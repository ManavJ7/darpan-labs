"""
Step 2D: Two-Phase Twin Selection (Eliminate → Cluster)

Phase 1 — Greedy Elimination:
  Sort all twins by coherence score descending. Keep the top N (CLUSTER_SURVIVOR_TARGET)
  and eliminate the rest. These bottom twins have the most internally contradictory
  branch-answer combinations, so they're dropped before any diversity analysis.

Phase 2 — K-Medoids Clustering:
  Embed each survivor's 5 branch answers via sentence-transformers, compute pairwise
  cosine distances, and run k-medoids PAM (k=20) to select the most behaviorally
  disjoint set as cluster medoids.

Input:
  - data/output/step2_pruned_twins.json  — 100 twins per participant

Output:
  - data/output/step2_pruned_twins_20.json      — updated with participant's 20 medoids
  - data/output/step2d_embeddings_{PID}.npz      — cached embeddings for survivors
  - data/output/step2d_cluster_report_{PID}.json — full diagnostics
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics import silhouette_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import (
    OUTPUT_DIR,
    TARGET_TWINS_STEP3,
    CLUSTER_SURVIVOR_TARGET,
    CLUSTER_EMBEDDING_MODEL,
    CLUSTER_RANDOM_SEED,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("step2d_cluster")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_participant_twins(participant_id: str) -> list[dict]:
    """Load a participant's 100 twins from step2_pruned_twins.json."""
    path = OUTPUT_DIR / "step2_pruned_twins.json"
    if not path.exists():
        raise FileNotFoundError(f"Pruned twins not found at {path}")
    with open(path) as f:
        data = json.load(f)
    for entry in data:
        if entry["participant_id"] == participant_id:
            logger.info(f"Loaded {len(entry['twins'])} twins for {participant_id}")
            return entry["twins"]
    raise ValueError(f"Participant {participant_id} not found in {path}")


def load_existing_pruned_20() -> list[dict]:
    """Load existing step2_pruned_twins_20.json (may have other participants)."""
    path = OUTPUT_DIR / "step2_pruned_twins_20.json"
    if not path.exists():
        return []
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Phase 1: Greedy coherence elimination
# ---------------------------------------------------------------------------

def eliminate_by_coherence(twins: list[dict], survivor_target: int) -> tuple[list[dict], list[dict]]:
    """
    Sort twins by coherence descending and keep the top `survivor_target`.
    Returns (survivors, eliminated) so both can be logged/reported.
    """
    ranked = sorted(twins, key=lambda t: t["coherence_score"], reverse=True)

    if len(ranked) <= survivor_target:
        return ranked, []

    survivors = ranked[:survivor_target]
    eliminated = ranked[survivor_target:]

    cutoff_score = survivors[-1]["coherence_score"]
    elim_worst = eliminated[-1]["coherence_score"]
    elim_best = eliminated[0]["coherence_score"]

    logger.info(
        f"PHASE 1 — Greedy elimination: {len(twins)} → {len(survivors)} survivors"
    )
    logger.info(
        f"  Survivor coherence range:   {survivors[-1]['coherence_score']:.2f} – "
        f"{survivors[0]['coherence_score']:.2f}"
    )
    logger.info(
        f"  Eliminated {len(eliminated)} twins with coherence "
        f"{elim_worst:.2f} – {elim_best:.2f} (cutoff: {cutoff_score:.2f})"
    )

    return survivors, eliminated


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

def embed_twins(
    twins: list[dict], model: SentenceTransformer
) -> np.ndarray:
    """
    Build embedding matrix for twins.
    Each twin → 5 sub-vectors (one per branch answer), L2-normalized and concatenated.
    Returns shape (n_twins, 5 * embed_dim).
    """
    embed_dim = model.get_sentence_embedding_dimension()
    n_dims = len(twins[0]["branch_answers"])

    # Build all embedding inputs at once for batched encoding
    all_texts = []
    for twin in twins:
        for ba in twin["branch_answers"]:
            all_texts.append(f"{ba['dimension_name']}: {ba['answer_text']}")

    logger.info(f"Encoding {len(all_texts)} texts ({len(twins)} twins x {n_dims} dims)...")
    all_embeddings = model.encode(all_texts, show_progress_bar=True, normalize_embeddings=True)

    # Reshape: (n_twins * n_dims, embed_dim) → (n_twins, n_dims * embed_dim)
    matrix = all_embeddings.reshape(len(twins), n_dims * embed_dim)

    # L2-normalize the full concatenated vector (sub-vectors are already unit-norm
    # but the concatenated 1920-dim vector has norm sqrt(5), not 1)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    matrix = matrix / norms

    logger.info(f"Embedding matrix shape: {matrix.shape}")
    return matrix


# ---------------------------------------------------------------------------
# K-medoids PAM
# ---------------------------------------------------------------------------

def cosine_distance_matrix(X: np.ndarray) -> np.ndarray:
    """Compute pairwise cosine distance matrix. X should be L2-normalized rows."""
    sim = X @ X.T
    np.clip(sim, -1.0, 1.0, out=sim)
    return 1.0 - sim


def kmedoids_pam(dist: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray, float]:
    """
    K-medoids PAM algorithm (BUILD + SWAP). Deterministic.

    Args:
        dist: (n, n) distance matrix
        k: number of medoids

    Returns:
        medoid_indices: array of k medoid indices
        labels: cluster assignment for each point
        total_cost: sum of distances to nearest medoid
    """
    n = dist.shape[0]

    # --- BUILD phase: greedy initialization ---
    total_dists = dist.sum(axis=1)
    medoids = [int(np.argmin(total_dists))]
    cost = dist[medoids[0]].copy()

    for _ in range(1, k):
        gains = np.zeros(n)
        for c in range(n):
            if c in medoids:
                continue
            improvement = np.maximum(0, cost - dist[c])
            gains[c] = improvement.sum()
        best = int(np.argmax(gains))
        medoids.append(best)
        cost = np.minimum(cost, dist[best])

    medoids = np.array(medoids, dtype=int)
    logger.info(f"  BUILD phase: {k} initial medoids selected")

    # --- SWAP phase: iteratively improve ---
    max_iter = 100
    for iteration in range(max_iter):
        labels = np.argmin(dist[medoids], axis=0)
        total_cost = sum(dist[medoids[labels[j]], j] for j in range(n))

        best_swap = None
        best_cost = total_cost

        for mi in range(k):
            for candidate in range(n):
                if candidate in medoids:
                    continue
                trial = medoids.copy()
                trial[mi] = candidate
                trial_labels = np.argmin(dist[trial], axis=0)
                trial_cost = sum(dist[trial[trial_labels[j]], j] for j in range(n))
                if trial_cost < best_cost:
                    best_cost = trial_cost
                    best_swap = (mi, candidate)

        if best_swap is None:
            logger.info(f"  SWAP phase converged after {iteration} iterations (cost={total_cost:.4f})")
            break

        mi_idx, new_medoid = best_swap
        old_medoid = medoids[mi_idx]
        medoids[mi_idx] = new_medoid
        logger.info(
            f"  SWAP iter {iteration}: medoid {old_medoid} → {new_medoid} "
            f"(cost {total_cost:.4f} → {best_cost:.4f})"
        )
    else:
        logger.warning(f"  SWAP phase hit max iterations ({max_iter})")

    labels = np.argmin(dist[medoids], axis=0)
    total_cost = float(sum(dist[medoids[labels[j]], j] for j in range(n)))

    return medoids, labels, total_cost


# ---------------------------------------------------------------------------
# Greedy baseline (for comparison in report)
# ---------------------------------------------------------------------------

def greedy_baseline_select(twins: list[dict], target: int) -> list[int]:
    """
    Reproduce the old greedy coherence+Hamming selection (Step 3's original method).
    Returns indices into the input list.
    """
    n_branch = len(twins[0]["branch_answers"])
    ranked = sorted(range(len(twins)), key=lambda i: twins[i]["coherence_score"], reverse=True)

    selected = [ranked[0]]
    remaining = list(ranked[1:])

    while len(selected) < target and remaining:
        best_idx_in_remaining = 0
        best_score = -1.0

        for ri, idx in enumerate(remaining):
            choices_cand = twins[idx]["choices"]
            min_diff = min(
                sum(1 for k in choices_cand if choices_cand.get(k) != twins[s]["choices"].get(k))
                for s in selected
            )
            combined = twins[idx]["coherence_score"] * 0.6 + (min_diff / n_branch) * 0.4
            if combined > best_score:
                best_score = combined
                best_idx_in_remaining = ri

        selected.append(remaining.pop(best_idx_in_remaining))

    return selected


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run(participant_id: str):
    start_time = time.time()

    # 1. Load twins
    twins = load_participant_twins(participant_id)
    n_input = len(twins)

    # ===== PHASE 1: Greedy coherence elimination =====
    survivors, eliminated = eliminate_by_coherence(twins, CLUSTER_SURVIVOR_TARGET)
    n_survivors = len(survivors)
    n_eliminated = len(eliminated)

    # Safety: need at least k twins to cluster
    if n_survivors < TARGET_TWINS_STEP3:
        logger.warning(
            f"Only {n_survivors} survivors, need {TARGET_TWINS_STEP3}. "
            f"Using all {n_input} twins."
        )
        survivors = sorted(twins, key=lambda t: t["coherence_score"], reverse=True)
        n_survivors = len(survivors)
        n_eliminated = 0

    # ===== PHASE 2: K-medoids clustering on survivors =====
    logger.info(f"\nPHASE 2 — K-medoids clustering: {n_survivors} → {TARGET_TWINS_STEP3}")

    # Embed
    logger.info(f"Loading embedding model: {CLUSTER_EMBEDDING_MODEL}")
    model = SentenceTransformer(CLUSTER_EMBEDDING_MODEL)
    embeddings = embed_twins(survivors, model)

    # Save embeddings
    emb_path = OUTPUT_DIR / f"step2d_embeddings_{participant_id}.npz"
    np.savez_compressed(
        emb_path,
        embeddings=embeddings,
        twin_ids=np.array([t["twin_id"] for t in survivors]),
    )
    logger.info(f"Saved embeddings to {emb_path}")

    # Cosine distance matrix
    dist = cosine_distance_matrix(embeddings)
    logger.info(f"Distance matrix: {dist.shape}, range [{dist.min():.4f}, {dist.max():.4f}]")

    # K-medoids
    k = TARGET_TWINS_STEP3
    medoids, labels, total_cost = kmedoids_pam(dist, k)

    # Select medoid twins
    selected_twins = [survivors[i] for i in medoids]

    # Re-number twin IDs
    for idx, twin in enumerate(selected_twins, 1):
        twin["twin_id"] = f"{participant_id}_T{idx:03d}"

    coherence_scores = [t["coherence_score"] for t in selected_twins]
    logger.info(f"Selected {len(selected_twins)} medoid twins")
    logger.info(
        f"  Coherence range: {min(coherence_scores):.2f} – {max(coherence_scores):.2f} "
        f"(mean {np.mean(coherence_scores):.2f})"
    )

    # Silhouette score
    n_unique_labels = len(set(labels))
    if n_unique_labels >= 2:
        sil_score = float(silhouette_score(dist, labels, metric="precomputed"))
    else:
        logger.warning("Only 1 unique label — silhouette score undefined, setting to 0.0")
        sil_score = 0.0
    logger.info(f"Silhouette score: {sil_score:.4f}")

    # Cluster sizes
    cluster_sizes = [int(np.sum(labels == c)) for c in range(k)]

    # Greedy baseline comparison (run on same survivors for apples-to-apples)
    greedy_indices = greedy_baseline_select(survivors, k)
    greedy_twin_ids = {survivors[i]["twin_id"] for i in greedy_indices}
    medoid_orig_ids = {survivors[i]["twin_id"] for i in medoids}
    overlap = len(greedy_twin_ids & medoid_orig_ids)

    # ===== Save outputs =====

    # Append to step2_pruned_twins_20.json
    existing_data = load_existing_pruned_20()
    existing_data = [p for p in existing_data if p["participant_id"] != participant_id]
    existing_data.append({
        "participant_id": participant_id,
        "n_original": n_input,
        "n_survivors": n_survivors,
        "n_selected": len(selected_twins),
        "selection_method": "eliminate_then_kmedoids",
        "twins": selected_twins,
    })
    existing_data.sort(key=lambda p: p["participant_id"])

    output_path = OUTPUT_DIR / "step2_pruned_twins_20.json"
    with open(output_path, "w") as f:
        json.dump(existing_data, f, indent=2)
    logger.info(f"Saved updated pruned-20 to {output_path}")
    for p in existing_data:
        logger.info(f"  {p['participant_id']}: {len(p['twins'])} twins")

    # Cluster report
    elapsed = time.time() - start_time

    eliminated_scores = [t["coherence_score"] for t in eliminated] if eliminated else []
    survivor_scores = [t["coherence_score"] for t in survivors]

    report = {
        "participant_id": participant_id,
        "selection_method": "eliminate_then_kmedoids",
        "embedding_model": CLUSTER_EMBEDDING_MODEL,
        "phase1_elimination": {
            "n_input": n_input,
            "survivor_target": CLUSTER_SURVIVOR_TARGET,
            "n_survivors": n_survivors,
            "n_eliminated": n_eliminated,
            "coherence_cutoff": float(survivors[-1]["coherence_score"]) if survivors else None,
            "eliminated_coherence_range": {
                "min": float(min(eliminated_scores)) if eliminated_scores else None,
                "max": float(max(eliminated_scores)) if eliminated_scores else None,
            },
            "survivor_coherence_range": {
                "min": float(min(survivor_scores)),
                "max": float(max(survivor_scores)),
                "mean": float(np.mean(survivor_scores)),
            },
        },
        "phase2_clustering": {
            "n_input": n_survivors,
            "k": k,
            "n_selected": len(selected_twins),
            "total_cost": total_cost,
            "silhouette_score": sil_score,
            "cluster_sizes": cluster_sizes,
            "cluster_size_stats": {
                "min": int(np.min(cluster_sizes)),
                "max": int(np.max(cluster_sizes)),
                "mean": float(np.mean(cluster_sizes)),
                "std": float(np.std(cluster_sizes)),
            },
            "selected_coherence_scores": {
                "min": float(min(coherence_scores)),
                "max": float(max(coherence_scores)),
                "mean": float(np.mean(coherence_scores)),
            },
        },
        "greedy_comparison": {
            "overlap_with_greedy": overlap,
            "out_of": k,
            "pct_overlap": round(100 * overlap / k, 1),
        },
        "selected_twin_ids": [t["twin_id"] for t in selected_twins],
        "elapsed_seconds": round(elapsed, 1),
    }

    report_path = OUTPUT_DIR / f"step2d_cluster_report_{participant_id}.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info(f"Saved cluster report to {report_path}")

    # Summary
    print(f"\n{'=' * 70}")
    print(f"STEP 2D: ELIMINATE → CLUSTER — {participant_id}")
    print(f"{'=' * 70}")
    print(f"  Phase 1 (eliminate contradictory):")
    print(f"    Input:           {n_input} twins")
    print(f"    Eliminated:      {n_eliminated} (lowest coherence)")
    print(f"    Survivors:       {n_survivors}")
    if eliminated_scores:
        print(f"    Cutoff:          {survivors[-1]['coherence_score']:.2f}")
    print(f"  Phase 2 (k-medoids clustering):")
    print(f"    Input:           {n_survivors} survivors")
    print(f"    Selected:        {len(selected_twins)} medoids")
    print(f"    Silhouette:      {sil_score:.4f}")
    print(f"    Total cost:      {total_cost:.4f}")
    print(f"    Cluster sizes:   {cluster_sizes}")
    print(f"    Coherence:       {min(coherence_scores):.2f} – {max(coherence_scores):.2f}")
    print(f"  Greedy overlap:    {overlap}/{k} ({100 * overlap / k:.0f}%)")
    print(f"  Elapsed:           {elapsed:.1f}s")
    print(f"\nOutputs:")
    print(f"  - {output_path}")
    print(f"  - {emb_path}")
    print(f"  - {report_path}")
    print(f"{'=' * 70}")

    return selected_twins


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Two-phase twin selection: eliminate contradictory profiles, then cluster"
    )
    parser.add_argument(
        "--participant", required=True,
        help="Participant ID (e.g. P02)",
    )
    args = parser.parse_args()
    run(args.participant)
