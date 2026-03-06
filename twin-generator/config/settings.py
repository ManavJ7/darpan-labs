"""
Twin Generator pipeline configuration.
All settings loaded from environment variables with sensible defaults.
"""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
PROMPTS_DIR = PROJECT_ROOT / "prompts"
TRAINING_DIR = PROJECT_ROOT / "training"

# Ensure output dirs exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)

# LLM
LLM_MODEL = os.getenv("LLM_DEFAULT_MODEL", "anthropic/claude-opus-4-6")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Multi-provider model configuration
LLM_REASONING_MODEL = os.getenv("LLM_REASONING_MODEL", "deepseek/deepseek-reasoner")  # Steps 2, 4B
LLM_GENERATION_MODEL = os.getenv("LLM_GENERATION_MODEL", "openai/gpt-5-mini")         # Steps 3, 5

# API key pool: comma-separated ANTHROPIC_API_KEYS, falls back to single key
_keys_env = os.getenv("ANTHROPIC_API_KEYS", "")
API_KEY_POOL: list[str] = [k.strip() for k in _keys_env.split(",") if k.strip()] if _keys_env else (
    [ANTHROPIC_API_KEY] if ANTHROPIC_API_KEY else []
)

# Per-provider API key pools
_deepseek_keys = os.getenv("DEEPSEEK_API_KEYS", os.getenv("DEEPSEEK_API_KEY", ""))
DEEPSEEK_KEY_POOL: list[str] = [k.strip() for k in _deepseek_keys.split(",") if k.strip()]

_openai_keys = os.getenv("OPENAI_API_KEYS", os.getenv("OPENAI_API_KEY", ""))
OPENAI_KEY_POOL: list[str] = [k.strip() for k in _openai_keys.split(",") if k.strip()]

MAX_PARALLEL_PARTICIPANTS = int(os.getenv("MAX_PARALLEL_PARTICIPANTS", str(max(len(API_KEY_POOL), len(DEEPSEEK_KEY_POOL), len(OPENAI_KEY_POOL), 1))))


def participant_output_dir(pid: str) -> Path:
    """Return per-participant output directory, creating it if needed."""
    d = OUTPUT_DIR / pid
    d.mkdir(parents=True, exist_ok=True)
    return d
LLM_MAX_TOKENS_BRANCHING = int(os.getenv("LLM_MAX_TOKENS_BRANCHING", "8000"))
LLM_MAX_TOKENS_PRUNING = int(os.getenv("LLM_MAX_TOKENS_PRUNING", "16000"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Pipeline parameters (locked per execution plan)
N_REAL_PARTICIPANTS = 20
Q_REAL_PER_PERSON = 59
Q_TOTAL_BANK = 350
Q_BRANCH = 5              # branching questions per person
V_BRANCH = 3              # answer variants per branching question
RAW_COMBOS = V_BRANCH ** Q_BRANCH  # 243
TARGET_TWINS_PER_PERSON = 100
N_TOTAL_TWINS = N_REAL_PARTICIPANTS * TARGET_TWINS_PER_PERSON  # 2000
Q_REMAINING_SYNTHETIC = Q_TOTAL_BANK - Q_REAL_PER_PERSON - Q_BRANCH  # 286

# Step 3: Profile Expansion
TARGET_TWINS_STEP3 = int(os.getenv("TARGET_TWINS_STEP3", "20"))  # prune from 100 → 20
STEP3_BATCH_SIZE = int(os.getenv("STEP3_BATCH_SIZE", "25"))       # questions per LLM call
LLM_MAX_TOKENS_STEP3 = int(os.getenv("LLM_MAX_TOKENS_STEP3", "8192"))  # 25 answers × ~150 tokens avg (some Qs echo options)
STEP3_PARALLEL_TWINS = int(os.getenv("STEP3_PARALLEL_TWINS", "5"))  # twins processed concurrently via asyncio.gather

# Step 4: Inference Layer
CHROMA_PERSIST_DIR = str(OUTPUT_DIR / "step4_chromadb")
CHROMA_COLLECTION_NAME = "twin_qa_pairs"
VECTOR_TOP_K = int(os.getenv("VECTOR_TOP_K", "15"))
KG_MAX_TRAITS_PER_TWIN = int(os.getenv("KG_MAX_TRAITS_PER_TWIN", "35"))
LLM_QUERY_MODEL = os.getenv("LLM_QUERY_MODEL", "deepseek/deepseek-reasoner")
LLM_MAX_TOKENS_QUERY = int(os.getenv("LLM_MAX_TOKENS_QUERY", "1024"))
LLM_TEMPERATURE_QUERY = float(os.getenv("LLM_TEMPERATURE_QUERY", "0.3"))
LLM_MAX_TOKENS_KG_EXTRACT = int(os.getenv("LLM_MAX_TOKENS_KG_EXTRACT", "16000"))

# Step 2D: Two-phase twin selection (eliminate → cluster)
CLUSTER_SURVIVOR_TARGET = int(os.getenv("CLUSTER_SURVIVOR_TARGET", "80"))  # Phase 1: keep top N by coherence
CLUSTER_EMBEDDING_MODEL = os.getenv("CLUSTER_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CLUSTER_RANDOM_SEED = int(os.getenv("CLUSTER_RANDOM_SEED", "42"))

# Step 5: Survey Simulation (Batched)
STEP5_MAX_BATCH_SIZE = int(os.getenv("STEP5_MAX_BATCH_SIZE", "8"))
LLM_MAX_TOKENS_BATCH_SURVEY = int(os.getenv("LLM_MAX_TOKENS_BATCH_SURVEY", "4096"))
STEP5_VECTOR_TOP_K_PER_QUERY = int(os.getenv("STEP5_VECTOR_TOP_K_PER_QUERY", "10"))
STEP5_SURVEY_SOURCE_WEIGHT = float(os.getenv("STEP5_SURVEY_SOURCE_WEIGHT", "0.95"))

# Concurrency
LLM_MAX_CONCURRENT = int(os.getenv("LLM_MAX_CONCURRENT", "5"))
