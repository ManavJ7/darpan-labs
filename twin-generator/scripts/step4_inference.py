"""
Step 4: Digital Twin Inference Engine.

Query digital twins using three inference modes:
  - vector:   ChromaDB semantic search -> top-K Q&A pairs -> Opus synthesis
  - kg:       Classify query domains -> traverse knowledge graph -> Opus synthesis
  - combined: Both vector + KG evidence -> merged Opus synthesis

Usage:
    # Single twin query
    python scripts/step4_inference.py \\
      --twin P01_T003 --mode vector \\
      --query "How would this person react to a premium body wash at ₹599?"

    # All twins
    python scripts/step4_inference.py \\
      --twin all --mode combined \\
      --query "Would you switch to a charcoal-based body wash?"

    # Interactive mode
    python scripts/step4_inference.py --interactive --mode combined
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
import networkx as nx

from config.settings import (
    VECTOR_TOP_K,
    LLM_QUERY_MODEL,
    LLM_MAX_TOKENS_QUERY,
    LLM_TEMPERATURE_QUERY,
    OUTPUT_DIR,
    PROMPTS_DIR,
)
from scripts.llm_utils import call_llm
from scripts.step4_vector_index import (
    get_client,
    get_collection,
    query_twin as vector_query_twin,
)
from scripts.step4_kg_build import load_graph

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data loading (cached at module level after first call)
# ---------------------------------------------------------------------------

_collection_cache: chromadb.Collection | None = None
_kg_cache: nx.DiGraph | None = None
_profiles_cache: dict[str, dict] | None = None
_pruned_cache: dict[str, dict] | None = None


def get_chroma_collection() -> chromadb.Collection:
    global _collection_cache
    if _collection_cache is None:
        client = get_client()
        _collection_cache = get_collection(client)
        count = _collection_cache.count()
        if count == 0:
            raise RuntimeError("ChromaDB collection is empty. Run step4_vector_index.py first.")
        logger.info(f"Loaded ChromaDB collection: {count} entries")
    return _collection_cache


def get_kg() -> nx.DiGraph:
    global _kg_cache
    if _kg_cache is None:
        path = OUTPUT_DIR / "step4_knowledge_graph.json"
        if not path.exists():
            raise FileNotFoundError(f"Knowledge graph not found at {path}. Run step4_kg_build.py first.")
        _kg_cache = load_graph(path)
        logger.info(f"Loaded KG: {_kg_cache.number_of_nodes()} nodes, {_kg_cache.number_of_edges()} edges")
    return _kg_cache


def get_profiles() -> dict[str, dict]:
    global _profiles_cache
    if _profiles_cache is None:
        with open(OUTPUT_DIR / "step3_complete_profiles.json") as f:
            data = json.load(f)
        _profiles_cache = {}
        for p in data:
            for t in p["twins"]:
                _profiles_cache[t["twin_id"]] = t
    return _profiles_cache


def get_pruned_twins() -> dict[str, dict]:
    global _pruned_cache
    if _pruned_cache is None:
        with open(OUTPUT_DIR / "step2_pruned_twins_20.json") as f:
            data = json.load(f)
        _pruned_cache = {}
        for p in data:
            for t in p["twins"]:
                _pruned_cache[t["twin_id"]] = t
    return _pruned_cache


def get_all_twin_ids() -> list[str]:
    return sorted(get_profiles().keys())


# ---------------------------------------------------------------------------
# Per-participant data loading (_for variants)
# ---------------------------------------------------------------------------

def get_chroma_collection_for(output_dir: Path) -> chromadb.Collection:
    """Load ChromaDB collection from a per-participant output directory."""
    chroma_dir = str(output_dir / "step4_chromadb")
    client = get_client(chroma_dir)
    collection = get_collection(client)
    count = collection.count()
    if count == 0:
        raise RuntimeError(f"ChromaDB collection at {chroma_dir} is empty.")
    return collection


def get_kg_for(output_dir: Path) -> nx.DiGraph:
    """Load knowledge graph from a per-participant output directory."""
    path = output_dir / "step4_knowledge_graph.json"
    if not path.exists():
        raise FileNotFoundError(f"Knowledge graph not found at {path}")
    return load_graph(path)


def get_profiles_for(output_dir: Path) -> dict[str, dict]:
    """Load profiles from a per-participant output directory."""
    with open(output_dir / "step3_complete_profiles.json") as f:
        data = json.load(f)
    result = {}
    for p in data:
        for t in p["twins"]:
            result[t["twin_id"]] = t
    return result


def get_pruned_twins_for(output_dir: Path) -> dict[str, dict]:
    """Load pruned twins from a per-participant output directory."""
    with open(output_dir / "step2_pruned_twins_20.json") as f:
        data = json.load(f)
    result = {}
    for p in data:
        for t in p["twins"]:
            result[t["twin_id"]] = t
    return result


# ---------------------------------------------------------------------------
# Twin summary builder (identity anchor for synthesis prompt)
# ---------------------------------------------------------------------------

def build_twin_summary(twin_id: str) -> str:
    """Build an identity anchor summary from profile + pruned + KG data."""
    profiles = get_profiles()
    pruned = get_pruned_twins()
    twin = profiles.get(twin_id, {})
    pruned_twin = pruned.get(twin_id, {})

    lines = [f"Twin ID: {twin_id}"]
    lines.append(f"Participant: {twin.get('participant_id', '?')}")
    lines.append(f"Coherence score: {twin.get('coherence_score', '?')}")
    lines.append(f"Profile basis: {twin.get('n_real', 59)} real interview answers + {twin.get('n_branch', 5)} branching answers + {twin.get('n_synthetic', 289)} synthetic answers")

    # Archetype positions from branch_answers
    lines.append("\nBehavioral Dimensions:")
    for ba in pruned_twin.get("branch_answers", []):
        lines.append(f"  - {ba['dimension_name']}: {ba['archetype_label']}")
        if ba.get("concept_test_prediction"):
            lines.append(f"    Concept test: {ba['concept_test_prediction'][:120]}")
        if ba.get("ad_test_prediction"):
            lines.append(f"    Ad test: {ba['ad_test_prediction'][:120]}")

    # If KG is available, add identity summary
    try:
        G = get_kg()
        if twin_id in G.nodes:
            identity = G.nodes[twin_id].get("identity_summary", "")
            if identity:
                lines.append(f"\nIdentity Summary: {identity}")
    except (FileNotFoundError, RuntimeError):
        pass  # KG not built yet

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mode 1: Vector retrieval (ChromaDB)
# ---------------------------------------------------------------------------

def retrieve_vector(query: str, twin_id: str, top_k: int = VECTOR_TOP_K) -> list[dict]:
    """Retrieve top-K Q&A pairs by semantic similarity for a specific twin."""
    collection = get_chroma_collection()
    results = vector_query_twin(collection, query, twin_id=twin_id, top_k=top_k)
    return results


def format_vector_evidence(results: list[dict]) -> str:
    """Format vector retrieval results as evidence block for the synthesis prompt."""
    lines = ["### Direct Evidence (Q&A pairs ranked by relevance)\n"]
    for i, r in enumerate(results, 1):
        score = r["score"]
        source = r["source"].upper()
        lines.append(f"{i}. [{source}, relevance={score:.2f}]")
        lines.append(f"   Q: {r['question_text']}")
        lines.append(f"   A: {r['answer_text']}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mode 2: Knowledge Graph retrieval
# ---------------------------------------------------------------------------

async def classify_query_domains(query: str, kg: nx.DiGraph | None = None, participant_id: str = "default") -> list[str]:
    """Use Opus to classify which behavioral domains a query relates to."""
    G = kg or get_kg()
    domains = sorted(set(
        d["label"] for _, d in G.nodes(data=True) if d.get("node_type") == "Domain"
    ))

    prompt = f"""Given this consumer behavior query, identify 1-3 most relevant behavioral domains.

Domains: {json.dumps(domains)}

Query: "{query}"

Return a JSON list of domain names, e.g. ["Purchase Decision Mechanics", "Risk & Novelty Orientation"].
Only return the JSON list, nothing else."""

    result = await call_llm(
        prompt=prompt,
        max_tokens=256,
        temperature=0.1,
        model=LLM_QUERY_MODEL,
        expect_json=True,
        participant_id=participant_id,
    )

    if isinstance(result, list):
        return result
    return domains[:2]  # fallback


def retrieve_kg(twin_id: str, relevant_domains: list[str], kg: nx.DiGraph | None = None) -> dict:
    """
    Traverse knowledge graph to collect traits and reasoning chain for a twin.
    """
    G = kg or get_kg()

    if twin_id not in G:
        return {"traits": [], "archetypes": [], "connections": [], "identity_summary": ""}

    # Identity summary
    identity_summary = G.nodes[twin_id].get("identity_summary", "")

    # Collect traits for this twin in relevant domains
    traits = []
    for _, trait_node, edge_data in G.out_edges(twin_id, data=True):
        if edge_data.get("edge_type") != "has_trait":
            continue
        node_data = G.nodes[trait_node]

        # Check if trait belongs to a relevant domain
        trait_domains = [
            G.nodes[succ].get("label", "")
            for succ in G.successors(trait_node)
            if G.nodes[succ].get("node_type") == "Domain"
        ]
        domain_match = any(d in relevant_domains for d in trait_domains) if relevant_domains else True
        if domain_match:
            traits.append({
                "trait_name": node_data.get("label", ""),
                "description": node_data.get("description", ""),
                "confidence": node_data.get("confidence", 0.5),
                "domains": trait_domains,
                "evidence_quotes": node_data.get("evidence_quotes", []),
                "predictive_value": node_data.get("predictive_value", ""),
            })

    # Sort by confidence
    traits.sort(key=lambda t: t["confidence"], reverse=True)

    # Collect archetype positions
    archetypes = []
    for _, arch_node, edge_data in G.out_edges(twin_id, data=True):
        if edge_data.get("edge_type") != "archetype_position":
            continue
        node_data = G.nodes[arch_node]
        archetypes.append({
            "archetype": node_data.get("label", ""),
            "dimension": edge_data.get("dimension", ""),
            "position": edge_data.get("position", ""),
        })

    # Collect trait connections (supports/contradicts/causes)
    connections = []
    trait_node_ids = {f"trait:{twin_id}:{t['trait_name']}" for t in traits}
    for trait_node_id in trait_node_ids:
        if trait_node_id not in G:
            continue
        for _, target, edge_data in G.out_edges(trait_node_id, data=True):
            if edge_data.get("edge_type") in ("supports", "contradicts", "causes"):
                target_label = G.nodes[target].get("label", "")
                connections.append({
                    "from": G.nodes[trait_node_id].get("label", ""),
                    "to": target_label,
                    "relationship": edge_data["edge_type"],
                    "mechanism": edge_data.get("mechanism", ""),
                })

    return {
        "traits": traits,
        "archetypes": archetypes,
        "connections": connections,
        "identity_summary": identity_summary,
    }


def format_kg_evidence(kg_data: dict) -> str:
    """Format KG retrieval results as evidence block."""
    lines = ["### Behavioral Profile (from Knowledge Graph)\n"]

    if kg_data.get("identity_summary"):
        lines.append(f"**Core Identity:** {kg_data['identity_summary']}")
        lines.append("")

    if kg_data["archetypes"]:
        lines.append("**Behavioral Dimensions:**")
        for a in kg_data["archetypes"]:
            lines.append(f"- {a['dimension']}: {a['archetype']} ({a['position']})")
        lines.append("")

    if kg_data["traits"]:
        lines.append("**Relevant Traits:**")
        for t in kg_data["traits"]:
            conf = t["confidence"]
            lines.append(f"- **{t['trait_name']}** (confidence={conf:.2f}): {t['description']}")
            if t.get("predictive_value"):
                lines.append(f"  Prediction: {t['predictive_value']}")
            for eq in t.get("evidence_quotes", [])[:2]:
                lines.append(f"  Evidence: \"{eq[:120]}\"")
        lines.append("")

    if kg_data["connections"]:
        lines.append("**Trait Interactions:**")
        for c in kg_data["connections"]:
            lines.append(f"- {c['from']} --[{c['relationship']}]--> {c['to']}: {c['mechanism']}")
        lines.append("")

    if not kg_data["traits"]:
        lines.append("No relevant traits found in the knowledge graph for this query domain.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Synthesis (shared by all modes)
# ---------------------------------------------------------------------------

async def synthesize(twin_id: str, evidence_block: str, query: str, participant_id: str = "default") -> str:
    """Call Opus to synthesize a final answer from evidence."""
    prompt_template = (PROMPTS_DIR / "step4_query.txt").read_text()
    twin_summary = build_twin_summary(twin_id)

    prompt = (
        prompt_template
        .replace("{twin_summary}", twin_summary)
        .replace("{evidence_block}", evidence_block)
        .replace("{user_query}", query)
    )

    answer = await call_llm(
        prompt=prompt,
        max_tokens=LLM_MAX_TOKENS_QUERY,
        temperature=LLM_TEMPERATURE_QUERY,
        model=LLM_QUERY_MODEL,
        expect_json=False,
        participant_id=participant_id,
    )
    return answer.strip()


# ---------------------------------------------------------------------------
# Query entry points per mode
# ---------------------------------------------------------------------------

async def query_vector(twin_id: str, query: str) -> dict:
    """Mode 1: Vector DB inference via ChromaDB."""
    t0 = time.time()
    results = retrieve_vector(query, twin_id)
    evidence = format_vector_evidence(results)
    answer = await synthesize(twin_id, evidence, query)
    elapsed = time.time() - t0
    return {
        "twin_id": twin_id,
        "mode": "vector",
        "query": query,
        "answer": answer,
        "n_evidence": len(results),
        "elapsed_s": round(elapsed, 2),
    }


async def query_kg(twin_id: str, query: str) -> dict:
    """Mode 2: Knowledge Graph inference."""
    t0 = time.time()
    domains = await classify_query_domains(query)
    kg_data = retrieve_kg(twin_id, domains)
    evidence = format_kg_evidence(kg_data)
    answer = await synthesize(twin_id, evidence, query)
    elapsed = time.time() - t0
    return {
        "twin_id": twin_id,
        "mode": "kg",
        "query": query,
        "answer": answer,
        "relevant_domains": domains,
        "n_traits": len(kg_data["traits"]),
        "elapsed_s": round(elapsed, 2),
    }


async def query_combined(twin_id: str, query: str) -> dict:
    """Mode 3: Combined vector + KG inference (parallel retrieval)."""
    t0 = time.time()

    # Vector retrieval is sync (ChromaDB), domain classification is async
    vector_results = retrieve_vector(query, twin_id)
    domains = await classify_query_domains(query)

    # KG retrieval (sync, fast graph traversal)
    kg_data = retrieve_kg(twin_id, domains)

    # Merge evidence
    vector_evidence = format_vector_evidence(vector_results)
    kg_evidence = format_kg_evidence(kg_data)
    combined_evidence = f"{vector_evidence}\n---\n\n{kg_evidence}"

    answer = await synthesize(twin_id, combined_evidence, query)
    elapsed = time.time() - t0
    return {
        "twin_id": twin_id,
        "mode": "combined",
        "query": query,
        "answer": answer,
        "n_vector_evidence": len(vector_results),
        "n_traits": len(kg_data["traits"]),
        "relevant_domains": domains,
        "elapsed_s": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

QUERY_FUNCTIONS = {
    "vector": query_vector,
    "kg": query_kg,
    "combined": query_combined,
}


async def query_twin_inference(twin_id: str, query: str, mode: str) -> dict:
    """Query a single twin in the specified mode."""
    fn = QUERY_FUNCTIONS.get(mode)
    if not fn:
        raise ValueError(f"Unknown mode: {mode}. Choose from: {list(QUERY_FUNCTIONS.keys())}")
    return await fn(twin_id, query)


async def query_all_twins(query: str, mode: str) -> list[dict]:
    """Query all twins and return aggregated results."""
    twin_ids = get_all_twin_ids()
    logger.info(f"Querying {len(twin_ids)} twins in '{mode}' mode...")

    results = []
    for twin_id in twin_ids:
        result = await query_twin_inference(twin_id, query, mode)
        results.append(result)
        logger.info(f"  {twin_id}: {result['answer'][:80]}...")

    return results


def print_result(result: dict):
    """Pretty-print a query result."""
    print(f"\n{'='*70}")
    print(f"Twin: {result['twin_id']}  |  Mode: {result['mode']}  |  Time: {result['elapsed_s']}s")
    print(f"{'='*70}")
    print(f"Q: {result['query']}")
    print(f"\nA: {result['answer']}")
    if "relevant_domains" in result:
        print(f"\nDomains: {result['relevant_domains']}")
    if "n_evidence" in result:
        print(f"Vector evidence: {result['n_evidence']} Q&A pairs")
    if "n_vector_evidence" in result:
        print(f"Vector evidence: {result['n_vector_evidence']} Q&A pairs")
    if "n_traits" in result:
        print(f"KG traits: {result['n_traits']}")
    print()


async def interactive_mode(mode: str):
    """Interactive REPL for querying twins."""
    twin_ids = get_all_twin_ids()
    print(f"\nDigital Twin Inference Engine — Interactive Mode ({mode})")
    print(f"Available twins: {', '.join(twin_ids)}")
    print(f"Commands: 'quit' to exit, 'mode <m>' to switch mode, 'twin <id>' to set default twin")
    print(f"{'='*70}\n")

    current_twin = twin_ids[0] if twin_ids else None
    current_mode = mode

    while True:
        try:
            user_input = input(f"[{current_twin}|{current_mode}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower().startswith("mode "):
            new_mode = user_input.split(None, 1)[1].strip()
            if new_mode in QUERY_FUNCTIONS:
                current_mode = new_mode
                print(f"Switched to {current_mode} mode")
            else:
                print(f"Unknown mode. Available: {list(QUERY_FUNCTIONS.keys())}")
            continue
        if user_input.lower().startswith("twin "):
            new_twin = user_input.split(None, 1)[1].strip()
            if new_twin == "all":
                current_twin = "all"
                print("Will query all twins")
            elif new_twin in get_all_twin_ids():
                current_twin = new_twin
                print(f"Switched to twin {current_twin}")
            else:
                print(f"Unknown twin. Available: {', '.join(get_all_twin_ids())}")
            continue

        # Treat input as a query
        if current_twin == "all":
            results = await query_all_twins(user_input, current_mode)
            for r in results:
                print_result(r)
        else:
            result = await query_twin_inference(current_twin, user_input, current_mode)
            print_result(result)


async def main():
    parser = argparse.ArgumentParser(description="Digital Twin Inference Engine")
    parser.add_argument("--twin", default=None, help="Twin ID to query (e.g. P01_T003) or 'all'")
    parser.add_argument("--mode", choices=["vector", "kg", "combined"], default="combined",
                        help="Inference mode (default: combined)")
    parser.add_argument("--query", default=None, help="Query string")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--output", default=None, help="Save results to JSON file")
    args = parser.parse_args()

    if args.interactive:
        await interactive_mode(args.mode)
        return

    if not args.query:
        parser.error("--query is required (or use --interactive)")
    if not args.twin:
        parser.error("--twin is required (or use --interactive)")

    if args.twin == "all":
        results = await query_all_twins(args.query, args.mode)
        for r in results:
            print_result(r)
    else:
        result = await query_twin_inference(args.twin, args.query, args.mode)
        print_result(result)
        results = [result]

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {args.output}")


if __name__ == "__main__":
    asyncio.run(main())
