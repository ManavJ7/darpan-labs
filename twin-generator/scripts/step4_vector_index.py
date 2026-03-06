"""
Step 4A: Build ChromaDB vector index for all twin Q&A pairs.

Uses sentence-transformers (all-MiniLM-L6-v2) for free local embeddings.
Stores in a persistent ChromaDB collection with metadata filtering.

Usage:
    python scripts/step4_vector_index.py
    python scripts/step4_vector_index.py --rebuild   # Force rebuild from scratch
"""
import argparse
import json
import logging
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from config.settings import (
    CHROMA_PERSIST_DIR,
    CHROMA_COLLECTION_NAME,
    VECTOR_TOP_K,
    OUTPUT_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Source quality weights for retrieval ranking
SOURCE_WEIGHTS = {"real": 1.0, "branch": 0.9, "synthetic": 0.7}

# ChromaDB batch add limit
CHROMA_BATCH_SIZE = 5000

# Embedding model — runs locally, free, 384 dims
EMBEDDING_FUNCTION = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def load_profiles(profiles_path: Path | None = None) -> list[dict]:
    """Load step3 complete profiles and flatten to list of QA records."""
    profiles_path = profiles_path or (OUTPUT_DIR / "step3_complete_profiles.json")
    with open(profiles_path) as f:
        data = json.load(f)

    records = []
    for participant in data:
        for twin in participant["twins"]:
            for i, qa in enumerate(twin["qa_pairs"]):
                records.append({
                    "id": f"{twin['twin_id']}_q{i:03d}",
                    "twin_id": twin["twin_id"],
                    "participant_id": twin["participant_id"],
                    "question_text": qa["question_text"],
                    "answer_text": qa["answer_text"],
                    "source": qa["source"],
                    "module_id": qa.get("module_id", ""),
                    "weight": SOURCE_WEIGHTS.get(qa["source"], 0.7),
                    # Combined text for embedding — richer semantic representation
                    "document": f"{qa['question_text']} — {qa['answer_text']}",
                })
    return records


def get_client(chroma_dir: str | None = None) -> chromadb.ClientAPI:
    """Get persistent ChromaDB client."""
    return chromadb.PersistentClient(path=chroma_dir or CHROMA_PERSIST_DIR)


def get_collection(client: chromadb.ClientAPI, collection_name: str | None = None) -> chromadb.Collection:
    """Get or create the twin Q&A collection."""
    return client.get_or_create_collection(
        name=collection_name or CHROMA_COLLECTION_NAME,
        embedding_function=EMBEDDING_FUNCTION,
        metadata={"hnsw:space": "cosine"},
    )


def build_for_participant(participant_id: str, output_dir: Path, rebuild: bool = False):
    """Build ChromaDB index for a single participant from their output_dir."""
    profiles_path = output_dir / "step3_complete_profiles.json"
    chroma_dir = str(output_dir / "step4_chromadb")

    records = load_profiles(profiles_path)
    n_twins = len(set(r["twin_id"] for r in records))
    logger.info(f"[{participant_id}] Loaded {len(records)} Q&A pairs from {n_twins} twins")

    if rebuild and Path(chroma_dir).exists():
        shutil.rmtree(chroma_dir)

    client = get_client(chroma_dir)
    collection = get_collection(client)
    build_index(records, rebuild=False, client=client, collection=collection)
    logger.info(f"[{participant_id}] ChromaDB index built at {chroma_dir}")


def build_index(records: list[dict], rebuild: bool = False,
                client: chromadb.ClientAPI | None = None,
                collection: chromadb.Collection | None = None):
    """Build the ChromaDB index from Q&A records."""
    if rebuild and Path(CHROMA_PERSIST_DIR).exists():
        logger.info(f"Removing existing ChromaDB at {CHROMA_PERSIST_DIR}")
        shutil.rmtree(CHROMA_PERSIST_DIR)

    if client is None:
        client = get_client()
    if collection is None:
        collection = get_collection(client)

    # Check if already populated
    existing_count = collection.count()
    if existing_count >= len(records):
        logger.info(f"Collection already has {existing_count} entries (expected {len(records)}). Use --rebuild to force.")
        return collection

    if existing_count > 0:
        logger.info(f"Collection has {existing_count} entries, expected {len(records)}. Rebuilding...")
        client.delete_collection(CHROMA_COLLECTION_NAME)
        collection = get_collection(client)

    logger.info(f"Indexing {len(records)} Q&A pairs into ChromaDB...")

    # Add in batches (ChromaDB has per-call limits)
    def _sanitize_meta_value(v):
        """ChromaDB only accepts str, int, float, bool, or None for metadata."""
        if isinstance(v, (str, int, float, bool)) or v is None:
            return v
        return json.dumps(v)

    for batch_start in range(0, len(records), CHROMA_BATCH_SIZE):
        batch = records[batch_start:batch_start + CHROMA_BATCH_SIZE]
        collection.add(
            ids=[r["id"] for r in batch],
            documents=[r["document"] for r in batch],
            metadatas=[{
                "twin_id": r["twin_id"],
                "participant_id": r["participant_id"],
                "source": r["source"],
                "module_id": r["module_id"],
                "weight": r["weight"],
                "question_text": _sanitize_meta_value(r["question_text"]),
                "answer_text": _sanitize_meta_value(r["answer_text"]),
            } for r in batch],
        )
        logger.info(f"  Added {batch_start + len(batch)}/{len(records)}")

    logger.info(f"Index complete: {collection.count()} entries")
    return collection


def query_twin(
    collection: chromadb.Collection,
    query_text: str,
    twin_id: str | None = None,
    top_k: int = VECTOR_TOP_K,
) -> list[dict]:
    """
    Query ChromaDB for relevant Q&A pairs.

    Args:
        collection: ChromaDB collection
        query_text: The user's query
        twin_id: Filter to a specific twin (or None for all)
        top_k: Number of results

    Returns:
        List of result dicts with score, question_text, answer_text, source, weight
    """
    where_filter = {"twin_id": twin_id} if twin_id else None

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k,
        where=where_filter,
        include=["metadatas", "distances", "documents"],
    )

    output = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        # ChromaDB returns cosine distance; convert to similarity (1 - distance)
        distance = results["distances"][0][i]
        similarity = 1.0 - distance

        output.append({
            "id": results["ids"][0][i],
            "score": round(similarity, 4),
            "weighted_score": round(similarity * meta["weight"], 4),
            "twin_id": meta["twin_id"],
            "question_text": meta["question_text"],
            "answer_text": meta["answer_text"],
            "source": meta["source"],
            "weight": meta["weight"],
            "module_id": meta["module_id"],
        })

    # Re-sort by weighted score (source quality matters)
    output.sort(key=lambda x: x["weighted_score"], reverse=True)
    return output


def main():
    parser = argparse.ArgumentParser(description="Build ChromaDB vector index for twin Q&A pairs")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild from scratch")
    args = parser.parse_args()

    t0 = time.time()

    # Load profiles
    records = load_profiles()
    n_twins = len(set(r["twin_id"] for r in records))
    logger.info(f"Loaded {len(records)} Q&A pairs from {n_twins} twins")
    for src in ["real", "branch", "synthetic"]:
        count = sum(1 for r in records if r["source"] == src)
        logger.info(f"  {src}: {count} (weight={SOURCE_WEIGHTS[src]})")

    # Build index
    collection = build_index(records, rebuild=args.rebuild)

    elapsed = time.time() - t0
    logger.info(f"\nVector index built in {elapsed:.1f}s")

    # Sanity check
    logger.info("\n--- Sanity Check ---")
    test_queries = [
        "What body wash brand do you use?",
        "How much do you spend on body wash per month?",
        "Would you try a new Korean body wash brand?",
    ]

    first_twin = records[0]["twin_id"]
    for query in test_queries:
        results = query_twin(collection, query, twin_id=first_twin, top_k=3)
        logger.info(f"\nQuery: '{query}' (twin {first_twin})")
        for i, r in enumerate(results):
            logger.info(f"  {i+1}. [score={r['score']:.3f}, {r['source']}] Q: {r['question_text'][:70]}...")
            logger.info(f"     A: {r['answer_text'][:90]}...")


if __name__ == "__main__":
    main()
