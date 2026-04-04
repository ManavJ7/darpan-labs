# AI Interviewer

AI-powered interview platform for consumer research. Conducts structured voice/text interviews across 8 modular question banks (M1-M8) to build deep consumer understanding and generate digital twin profiles.

## What It Does

1. **User signs in** via Google OAuth
2. **Selects modules** to complete from the module dashboard
3. **AI interviewer** asks questions from the selected module's question bank
4. **User responds** via text or voice (voice is transcribed via OpenAI Whisper and corrected by LLM)
5. **Answer parser** evaluates response satisfaction and extracts key insights
6. **Follow-up probes** are generated if the answer needs deeper exploration
7. **Module completes** when all questions are satisfactorily answered
8. **Admin dashboard** allows viewing transcripts and tracking progress

## Interview Modules

| Module | Name | Description |
|--------|------|-------------|
| M1 | Core Identity & Context | Demographics, background, self-perception |
| M2 | Preferences & Values | Personal values, brand preferences |
| M3 | Purchase Decision Logic | How they evaluate and buy products |
| M4 | Lifestyle & Grooming | Daily routines, grooming habits |
| M5 | Sensory & Aesthetic | Sensory preferences, aesthetic tastes |
| M6 | Body Wash Deep Dive | Category-specific deep exploration |
| M7 | Media & Influence | Media consumption, influencer impact |
| M8 | Concept Test | Evaluate product concepts with structured scoring |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Pydantic v2, SQLAlchemy (async), LiteLLM |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS, Zustand, Framer Motion |
| **Database** | PostgreSQL (asyncpg) + pgvector |
| **LLM** | LiteLLM (OpenAI, Anthropic, etc.) |
| **Voice/ASR** | OpenAI Whisper API |
| **Auth** | Google OAuth + JWT |
| **Deployment** | Railway / Docker Compose |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL (or use Docker)

### Option 1: Docker Compose (recommended)

```bash
cd ai-interviewer
cp .env.example .env
# Edit .env with your API keys

docker-compose up -d
# Backend auto-creates tables on startup
```

### Option 2: Run Locally

```bash
# Start database with Docker
docker-compose up db redis -d

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # or create backend/.env
uvicorn app.main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

### Verify

- Backend Health: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:3000

## Project Structure

```
ai-interviewer/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # Async SQLAlchemy engine
│   │   ├── dependencies.py      # Auth dependencies
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── routers/             # API route handlers
│   │   ├── services/            # Business logic
│   │   └── llm/                 # LiteLLM abstraction
│   ├── prompts/                 # LLM prompt templates
│   ├── seed_data/               # JSON question banks (M1-M8)
│   ├── migrations/              # Alembic DB migrations
│   ├── tests/                   # Pytest test suite
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages (login, interview, admin)
│   │   ├── components/          # React components
│   │   ├── lib/                 # API client
│   │   ├── store/               # Zustand state
│   │   ├── hooks/               # Custom hooks (useVoice)
│   │   └── types/               # TypeScript types
│   ├── public/                  # VAD models, WASM files
│   ├── package.json
│   ├── Dockerfile
│   └── next.config.js
├── docker-compose.yml           # Full stack: DB + Redis + Backend + Frontend
├── .env.example
└── .gitignore
```

## API Endpoints

### Auth (`/api/v1/auth`)
- `POST /google` — Google OAuth login
- `GET /me` — Current user profile
- `PUT /profile` — Update user demographics

### Interviews (`/api/v1/interviews`)
- `POST /start` — Start full interview
- `POST /start-module` — Start single module
- `POST /{session_id}/answer` — Submit answer
- `POST /{session_id}/skip` — Skip question
- `POST /{session_id}/pause` — Pause session
- `POST /{session_id}/complete-module` — Complete module
- `GET /user/{user_id}/modules` — Module completion status

### Voice (`/api/v1/voice`)
- `WebSocket /{session_id}` — Real-time voice interview

### Admin (`/api/v1/admin`)
- `GET /users` — List all users
- `GET /users/{user_id}/transcript` — Full transcript export
- `GET /users/{user_id}/transcript/download` — Download (JSON/CSV)

## Environment Variables

See `.env.example` for the full list. Key variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `OPENAI_API_KEY` | OpenAI API key (LLM + Whisper) | Yes |
| `AUTH_SECRET_KEY` | JWT signing secret | Yes |
| `NEXT_PUBLIC_GOOGLE_CLIENT_ID` | Google OAuth client ID | Yes |
| `NEXT_PUBLIC_API_URL` | Backend URL for frontend | Yes |

## License

Confidential - Darpan Labs
