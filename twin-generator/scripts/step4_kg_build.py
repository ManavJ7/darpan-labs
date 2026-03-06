"""
Step 4B: Build knowledge graph from twin profiles.

For each twin, sends all 353 Q&A pairs to Opus to extract behavioral traits,
then builds a networkx graph with Twin/Trait/Domain/Archetype nodes and edges.

Usage:
    python scripts/step4_kg_build.py
    python scripts/step4_kg_build.py --twins P01_T001 P01_T005   # specific twins only
    python scripts/step4_kg_build.py --resume                     # resume from last checkpoint
"""
import argparse
import asyncio
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import networkx as nx
from networkx.readwrite import json_graph

from config.settings import (
    OUTPUT_DIR,
    PROMPTS_DIR,
    LLM_REASONING_MODEL,
    LLM_MAX_TOKENS_KG_EXTRACT,
    LLM_TEMPERATURE_QUERY,
    KG_MAX_TRAITS_PER_TWIN,
)
from scripts.llm_utils import call_llm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

CHECKPOINT_PATH = OUTPUT_DIR / "step4_kg_checkpoint.json"
GRAPH_PATH = OUTPUT_DIR / "step4_knowledge_graph.json"


def load_profiles(profiles_dir: Path | None = None) -> dict[str, dict]:
    """Load step3 profiles indexed by twin_id."""
    profiles_path = (profiles_dir or OUTPUT_DIR) / "step3_complete_profiles.json"
    with open(profiles_path) as f:
        data = json.load(f)

    twins = {}
    for participant in data:
        for twin in participant["twins"]:
            twins[twin["twin_id"]] = twin
    return twins


def load_pruned_twins(pruned_dir: Path | None = None) -> dict[str, dict]:
    """Load step2 pruned twins for archetype data."""
    pruned_path = (pruned_dir or OUTPUT_DIR) / "step2_pruned_twins_20.json"
    with open(pruned_path) as f:
        data = json.load(f)

    twins = {}
    for participant in data:
        for twin in participant["twins"]:
            twins[twin["twin_id"]] = twin
    return twins


def format_qa_pairs(twin: dict) -> str:
    """Format all Q&A pairs for the trait extraction prompt, sorted by source quality."""
    # Sort: real first, then branch, then synthetic
    source_order = {"real": 0, "branch": 1, "synthetic": 2}
    sorted_pairs = sorted(twin["qa_pairs"], key=lambda qa: source_order.get(qa["source"], 2))

    lines = []
    for i, qa in enumerate(sorted_pairs, 1):
        source_tag = qa["source"].upper()
        lines.append(f"{i}. [{source_tag}] Q: {qa['question_text']}")
        lines.append(f"   A: {qa['answer_text']}")
        lines.append("")
    return "\n".join(lines)


async def extract_traits(twin_id: str, twin: dict, participant_id: str = "default") -> dict:
    """Call Opus to extract behavioral traits from a twin's Q&A pairs."""
    prompt_template = (PROMPTS_DIR / "step4_extract_traits.txt").read_text()
    qa_block = format_qa_pairs(twin)

    prompt = prompt_template.replace("{twin_id}", twin_id).replace("{qa_pairs_block}", qa_block)

    logger.info(f"Extracting traits for {twin_id} ({len(twin['qa_pairs'])} Q&A pairs)...")

    result = await call_llm(
        prompt=prompt,
        max_tokens=LLM_MAX_TOKENS_KG_EXTRACT,
        temperature=LLM_TEMPERATURE_QUERY,
        model=LLM_REASONING_MODEL,
        expect_json=True,
        participant_id=participant_id,
    )
    return result


def build_graph(
    all_traits: dict[str, dict],
    pruned_twins: dict[str, dict],
) -> nx.DiGraph:
    """Build a networkx directed graph from extracted traits."""
    G = nx.DiGraph()

    # Normalize: if twin_data is a list (just traits), wrap it
    for tid in list(all_traits.keys()):
        td = all_traits[tid]
        if isinstance(td, list):
            all_traits[tid] = {"twin_id": tid, "identity_summary": "", "traits": td}

    # Collect all unique domains
    all_domains = set()
    for twin_data in all_traits.values():
        for trait in twin_data.get("traits", []):
            all_domains.add(trait.get("domain", "Unknown"))

    # Add Domain nodes
    for domain in all_domains:
        G.add_node(f"domain:{domain}", node_type="Domain", label=domain)

    for twin_id, twin_data in all_traits.items():
        # Add Twin node with identity summary
        G.add_node(
            twin_id,
            node_type="Twin",
            label=twin_id,
            identity_summary=twin_data.get("identity_summary", ""),
        )

        # Add Archetype nodes and edges from pruned_twins
        pruned = pruned_twins.get(twin_id, {})
        for ba in pruned.get("branch_answers", []):
            arch_id = f"archetype:{ba['archetype_label']}"
            if not G.has_node(arch_id):
                G.add_node(
                    arch_id,
                    node_type="Archetype",
                    label=ba["archetype_label"],
                    dimension=ba["dimension_name"],
                )
            G.add_edge(
                twin_id,
                arch_id,
                edge_type="archetype_position",
                dimension=ba["dimension_name"],
                position=ba.get("position_on_dimension", ""),
            )

        # Add Trait nodes and edges
        traits = twin_data.get("traits", [])[:KG_MAX_TRAITS_PER_TWIN]
        trait_nodes = {}  # trait_name -> node_id

        for trait in traits:
            trait_name = trait["trait_name"]
            trait_node_id = f"trait:{twin_id}:{trait_name}"
            trait_nodes[trait_name] = trait_node_id

            G.add_node(
                trait_node_id,
                node_type="Trait",
                label=trait_name,
                twin_id=twin_id,
                description=trait.get("description", ""),
                confidence=trait.get("confidence", 0.5),
                evidence_quotes=trait.get("evidence_quotes", []),
                predictive_value=trait.get("predictive_value", ""),
            )

            # Twin -> has_trait -> Trait
            G.add_edge(
                twin_id,
                trait_node_id,
                edge_type="has_trait",
                confidence=trait.get("confidence", 0.5),
            )

            # Trait -> belongs_to -> Domain
            domain = trait.get("domain", "Unknown")
            domain_node = f"domain:{domain}"
            if G.has_node(domain_node):
                G.add_edge(trait_node_id, domain_node, edge_type="belongs_to")

        # Add intra-trait edges (supports/contradicts/causes)
        for conn in twin_data.get("trait_connections", []):
            from_name = conn.get("from_trait", "")
            to_name = conn.get("to_trait", "")
            from_node = trait_nodes.get(from_name)
            to_node = trait_nodes.get(to_name)
            if from_node and to_node:
                G.add_edge(
                    from_node,
                    to_node,
                    edge_type=conn.get("relationship", "supports"),
                    mechanism=conn.get("mechanism", ""),
                )

    return G


def save_graph(G: nx.DiGraph, path: Path):
    """Save graph as JSON using node-link format."""
    data = json_graph.node_link_data(G)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    size_mb = path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved knowledge graph to {path} ({size_mb:.1f} MB)")
    logger.info(f"  Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")


def load_graph(path: Path) -> nx.DiGraph:
    """Load graph from JSON."""
    with open(path) as f:
        data = json.load(f)
    return json_graph.node_link_graph(data, directed=True)


def load_checkpoint(checkpoint_path: Path | None = None) -> dict[str, dict]:
    """Load checkpoint of already-extracted traits."""
    path = checkpoint_path or CHECKPOINT_PATH
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_checkpoint(all_traits: dict[str, dict], checkpoint_path: Path | None = None):
    """Save extraction checkpoint."""
    path = checkpoint_path or CHECKPOINT_PATH
    with open(path, "w") as f:
        json.dump(all_traits, f, indent=2)


async def build_kg_for_participant(participant_id: str, output_dir: Path):
    """Build knowledge graph for a single participant from their output_dir."""
    checkpoint_path = output_dir / "step4_kg_checkpoint.json"
    graph_path = output_dir / "step4_knowledge_graph.json"

    profiles = load_profiles(output_dir)
    pruned_twins = load_pruned_twins(output_dir)
    twin_ids = sorted(profiles.keys())

    logger.info(f"[{participant_id}] Building KG for {len(twin_ids)} twins")

    all_traits = load_checkpoint(checkpoint_path)
    if all_traits:
        logger.info(f"[{participant_id}] Resumed from checkpoint: {len(all_traits)} twins done")

    for twin_id in twin_ids:
        if twin_id in all_traits:
            logger.info(f"[{participant_id}] Skipping {twin_id} (already in checkpoint)")
            continue

        if twin_id not in profiles:
            continue

        try:
            result = await extract_traits(twin_id, profiles[twin_id], participant_id=participant_id)
            all_traits[twin_id] = result
            save_checkpoint(all_traits, checkpoint_path)
        except Exception as e:
            logger.error(f"[{participant_id}] Failed to extract traits for {twin_id}: {e}")
            continue

    # Build graph
    G = build_graph(all_traits, pruned_twins)
    save_graph(G, graph_path)
    logger.info(f"[{participant_id}] KG complete: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")


async def main():
    parser = argparse.ArgumentParser(description="Build knowledge graph from twin profiles")
    parser.add_argument("--twins", nargs="*", help="Specific twin IDs to process (default: all)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    t0 = time.time()

    # Load data
    profiles = load_profiles()
    pruned_twins = load_pruned_twins()

    twin_ids = args.twins if args.twins else sorted(profiles.keys())
    logger.info(f"Processing {len(twin_ids)} twins: {twin_ids}")

    # Load or init checkpoint
    all_traits = load_checkpoint() if args.resume else {}
    if args.resume and all_traits:
        logger.info(f"Resumed from checkpoint: {len(all_traits)} twins already processed")

    # Extract traits for each twin
    for twin_id in twin_ids:
        if twin_id in all_traits:
            logger.info(f"Skipping {twin_id} (already in checkpoint)")
            continue

        if twin_id not in profiles:
            logger.warning(f"Twin {twin_id} not found in profiles, skipping")
            continue

        try:
            result = await extract_traits(twin_id, profiles[twin_id])
            all_traits[twin_id] = result
            n_traits = len(result.get("traits", []))
            n_connections = len(result.get("trait_connections", []))
            summary = result.get("identity_summary", "")[:100]
            logger.info(f"  {twin_id}: {n_traits} traits, {n_connections} connections")
            logger.info(f"  Identity: {summary}...")

            # Checkpoint after each twin
            save_checkpoint(all_traits)
        except Exception as e:
            logger.error(f"Failed to extract traits for {twin_id}: {e}")
            continue

    # Build graph
    logger.info("\nBuilding knowledge graph...")
    G = build_graph(all_traits, pruned_twins)
    save_graph(G, GRAPH_PATH)

    # Print summary
    elapsed = time.time() - t0
    logger.info(f"\nKnowledge graph built in {elapsed:.1f}s")

    # Stats by node type
    for ntype in ["Twin", "Trait", "Domain", "Archetype"]:
        count = sum(1 for _, d in G.nodes(data=True) if d.get("node_type") == ntype)
        logger.info(f"  {ntype} nodes: {count}")

    for etype in ["has_trait", "belongs_to", "archetype_position", "supports", "contradicts", "causes"]:
        count = sum(1 for _, _, d in G.edges(data=True) if d.get("edge_type") == etype)
        if count > 0:
            logger.info(f"  {etype} edges: {count}")


if __name__ == "__main__":
    asyncio.run(main())
