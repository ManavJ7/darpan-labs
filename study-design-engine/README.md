# Study Design Engine

AI-assisted research study design microservice that converts a brand's unstructured research question into a fully specified, execution-ready research study through four sequential, AI-assisted, human-reviewed steps.

## Architecture

The engine follows a 4-step sequential pipeline with a state machine enforcing transitions:

```
init → Step 1 (Study Brief) → Step 2 (Concept Boards) → Step 3 (Research Design) → Step 4 (Questionnaire) → complete
```

Each step follows: **AI generates → Human reviews → Human edits → Human locks**.

## Quick Start

### With Docker

```bash
cd study-design-engine
docker-compose up
```

### Local Development

```bash
cd study-design-engine
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

### Database Setup

```bash
# Run migrations
alembic upgrade head

# Seed metric library
curl -X POST http://localhost:8001/api/v1/metrics/seed
```

## Running Tests

```bash
cd study-design-engine
python -m pytest tests/ -v --tb=short
```

## API Endpoints

### Core
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/api/v1/studies` | Create a new study |
| GET | `/api/v1/studies/{id}` | Get study by ID |
| GET | `/api/v1/studies` | List studies |

### Step 1 — Study Brief
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/studies/{id}/steps/1/generate` | Generate study brief |
| PATCH | `/api/v1/studies/{id}/steps/1` | Edit study brief |
| POST | `/api/v1/studies/{id}/steps/1/lock` | Lock study brief |

### Step 2 — Concept Boards
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/studies/{id}/steps/2/generate` | Generate concept templates |
| PATCH | `/api/v1/studies/{id}/concepts/{cid}` | Update concept |
| POST | `/api/v1/studies/{id}/concepts/{cid}/refine` | AI-refine concept |
| POST | `/api/v1/studies/{id}/concepts/{cid}/approve` | Approve concept |
| POST | `/api/v1/studies/{id}/concepts/comparability-check` | Run comparability audit |
| POST | `/api/v1/studies/{id}/concepts/{cid}/render` | Render concept image |
| POST | `/api/v1/studies/{id}/steps/2/lock` | Lock step 2 |

### Step 3 — Research Design
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/studies/{id}/steps/3/generate` | Generate research design |
| PATCH | `/api/v1/studies/{id}/steps/3` | Edit design (auto-recalculates) |
| POST | `/api/v1/studies/{id}/steps/3/lock` | Lock research design |

### Step 4 — Questionnaire
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/studies/{id}/steps/4/generate` | Generate questionnaire |
| POST | `/api/v1/studies/{id}/steps/4/sections/{sid}/feedback` | Submit section feedback |
| POST | `/api/v1/studies/{id}/steps/4/lock` | Lock questionnaire (completes study) |

### Support Services
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/metrics` | List metrics |
| POST | `/api/v1/metrics/seed` | Seed metric library |
| GET | `/api/v1/studies/{id}/audit-log` | Get audit trail |
| POST/GET | `/api/v1/studies/{id}/comments` | Manage review comments |
| GET | `/api/v1/studies/{id}/steps/{step}/versions` | Version history |
| GET | `/api/v1/studies/{id}/export` | Export complete study |

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL (async via SQLAlchemy + asyncpg)
- **LLM**: LiteLLM (supports OpenAI, Anthropic, etc.)
- **Port**: 8001 (standalone, does not conflict with main backend)
