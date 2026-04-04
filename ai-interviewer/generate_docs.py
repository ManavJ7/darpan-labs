"""
Generate comprehensive PDF documentation for the Darpan Labs AI Interviewer module.
"""

from fpdf import FPDF


class DocPDF(FPDF):
    """Custom PDF with header/footer for documentation."""

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, "Darpan Labs AI Interviewer - Technical Documentation", align="C")
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(30, 30, 30)
        self.ln(4)
        self.cell(0, 10, title)
        self.ln(6)
        self.set_draw_color(50, 150, 50)
        self.set_line_width(0.8)
        self.line(10, self.get_y(), 80, self.get_y())
        self.set_line_width(0.2)
        self.ln(6)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(50, 50, 50)
        self.ln(2)
        self.cell(0, 8, title)
        self.ln(8)

    def subsection_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(70, 70, 70)
        self.cell(0, 7, title)
        self.ln(7)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def code_text(self, text):
        self.set_font("Courier", "", 9)
        self.set_text_color(60, 60, 60)
        self.set_fill_color(245, 245, 245)
        self.multi_cell(0, 5, text, fill=True)
        self.ln(2)

    def bullet(self, text, indent=10):
        x = self.get_x()
        self.set_font("Helvetica", "", 10)
        self.set_text_color(40, 40, 40)
        self.set_x(x + indent)
        self.cell(5, 5.5, "-")
        self.multi_cell(0, 5.5, text)
        self.ln(1)

    def table_row(self, cols, widths, bold=False):
        style = "B" if bold else ""
        self.set_font("Helvetica", style, 9)
        h = 7
        for i, col in enumerate(cols):
            self.cell(widths[i], h, str(col)[:int(widths[i]/2.2)], border=1)
        self.ln(h)


def generate_doc():
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ========== TITLE PAGE ==========
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 15, "Darpan Labs", align="C")
    pdf.ln(15)
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(50, 150, 50)
    pdf.cell(0, 12, "AI Interviewer Module", align="C")
    pdf.ln(15)
    pdf.set_font("Helvetica", "", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 10, "Technical Documentation & Code Analysis", align="C")
    pdf.ln(30)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 8, "Version 0.1.0", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "April 2026", align="C")
    pdf.ln(8)
    pdf.cell(0, 8, "Auto-generated documentation", align="C")

    # ========== TABLE OF CONTENTS ==========
    pdf.add_page()
    pdf.chapter_title("Table of Contents")
    toc = [
        "1. Executive Summary",
        "2. Technology Stack",
        "3. Architecture Overview",
        "4. Directory Structure",
        "5. Backend - File-by-File Breakdown",
        "    5.1 Entry Point & Configuration",
        "    5.2 Database & Models",
        "    5.3 API Routers (Endpoints)",
        "    5.4 Services (Business Logic)",
        "    5.5 LLM Integration",
        "    5.6 Prompt Templates",
        "    5.7 Question Banks (Seed Data)",
        "    5.8 Schemas (Pydantic Models)",
        "6. Frontend - File-by-File Breakdown",
        "    6.1 Pages & Routing",
        "    6.2 Components",
        "    6.3 State Management (Stores)",
        "    6.4 API Client & Hooks",
        "    6.5 Types",
        "7. Feature Map & Connections",
        "8. Authentication Flow",
        "9. Interview Flow (Core Feature)",
        "10. Voice Interview System",
        "11. Admin Dashboard",
        "12. Database Schema",
        "13. DevOps & Deployment",
        "14. Code Quality Analysis",
        "15. Optimization Recommendations",
    ]
    for item in toc:
        if item.startswith("    "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_x(25)
        else:
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_x(15)
        pdf.set_text_color(40, 40, 40)
        pdf.cell(0, 6.5, item)
        pdf.ln(6.5)

    # ========== 1. EXECUTIVE SUMMARY ==========
    pdf.add_page()
    pdf.chapter_title("1. Executive Summary")
    pdf.body_text(
        "The Darpan Labs AI Interviewer is a full-stack web application designed for AI-powered consumer research interviews. "
        "It conducts structured yet adaptive interviews across 8 thematic modules, using LLM-driven question selection, "
        "follow-up probing, and answer satisfaction analysis to build rich consumer profiles."
    )
    pdf.body_text(
        "The platform supports both text-based and voice-based interviews, with real-time speech recognition via WebSockets. "
        "It features Google OAuth authentication, an admin dashboard for transcript review, and a modular architecture "
        "that cleanly separates concerns between API routing, business logic services, and data persistence."
    )
    pdf.ln(2)
    pdf.subsection_title("Key Capabilities")
    capabilities = [
        "8 interview modules (M1-M8) covering identity, preferences, purchase logic, lifestyle, sensory, body wash deep-dive, media influence, and concept testing",
        "Adaptive question selection using LLM to pick next question based on conversation context and signal coverage",
        "Answer satisfaction checking - LLM judges if answers are sufficient or need follow-up probes",
        "Real-time voice interviews with WebSocket-based ASR (OpenAI Whisper) and VAD (Voice Activity Detection)",
        "Google OAuth 2.0 authentication with JWT session management",
        "Admin dashboard for viewing user transcripts and module completion status",
        "123 pre-defined questions across all modules with structured metadata (signals, types, follow-ups)",
        "Module completion evaluation with coverage and confidence scoring via LLM",
    ]
    for c in capabilities:
        pdf.bullet(c)

    # ========== 2. TECHNOLOGY STACK ==========
    pdf.add_page()
    pdf.chapter_title("2. Technology Stack")

    pdf.subsection_title("Backend")
    backend_tech = [
        "Framework: FastAPI 0.109.0+ (Python async web framework)",
        "Database: PostgreSQL with asyncpg driver (async I/O)",
        "ORM: SQLAlchemy 2.0+ (async sessions)",
        "Migrations: Alembic for schema versioning",
        "Validation: Pydantic v2 for request/response schemas",
        "LLM: LiteLLM (abstraction over OpenAI, Anthropic, etc.)",
        "Auth: Google OAuth (google-auth library) + JWT (python-jose)",
        "Voice ASR: OpenAI Whisper API",
        "Task Queue: Celery + Redis (for async background tasks)",
        "Observability: Sentry (error tracking), Langfuse (LLM tracing)",
        "Testing: Pytest + pytest-asyncio",
    ]
    for t in backend_tech:
        pdf.bullet(t)

    pdf.ln(3)
    pdf.subsection_title("Frontend")
    frontend_tech = [
        "Framework: Next.js 14.1.0 (React, App Router)",
        "Language: TypeScript 5.3+",
        "Styling: Tailwind CSS 3.4.1",
        "State Management: Zustand 4.4.7 (lightweight stores)",
        "Auth UI: @react-oauth/google (Google Sign-In button)",
        "Voice: @ricky0123/vad-web (Voice Activity Detection in browser)",
        "Charts: Recharts 2.10 (admin dashboard)",
        "Animations: Framer Motion 10.18",
        "Notifications: Sonner (toast notifications)",
        "Icons: Lucide React",
    ]
    for t in frontend_tech:
        pdf.bullet(t)

    pdf.ln(3)
    pdf.subsection_title("DevOps")
    devops_tech = [
        "Containerization: Docker (separate Dockerfiles for frontend/backend)",
        "Orchestration: docker-compose.yml for local dev (PostgreSQL, Redis, backend, frontend)",
        "Production: Railway.app deployment",
        "Database Migrations: Alembic with auto-generated version scripts",
    ]
    for t in devops_tech:
        pdf.bullet(t)

    # ========== 3. ARCHITECTURE OVERVIEW ==========
    pdf.add_page()
    pdf.chapter_title("3. Architecture Overview")
    pdf.body_text(
        "The application follows a clean layered architecture with clear separation of concerns:"
    )
    pdf.ln(2)
    pdf.code_text(
        "  [Browser / Next.js Frontend]\n"
        "         |\n"
        "         | REST API + WebSocket\n"
        "         v\n"
        "  [FastAPI Backend]\n"
        "    |-- Routers (auth, interviews, voice, admin)\n"
        "    |-- Services (auth, interview, question_bank, prompt, etc.)\n"
        "    |-- LLM Client (LiteLLM wrapper)\n"
        "    |-- Models (SQLAlchemy ORM)\n"
        "         |\n"
        "         v\n"
        "  [PostgreSQL Database]\n"
        "  [Redis (Celery tasks)]\n"
        "  [External APIs: OpenAI, Google OAuth]"
    )
    pdf.ln(3)
    pdf.body_text(
        "Data Flow: User authenticates via Google OAuth -> Frontend stores JWT -> "
        "All API calls include Bearer token -> Backend validates JWT via dependency injection -> "
        "Services handle business logic -> LLM calls for adaptive question selection -> "
        "Responses stored in PostgreSQL."
    )
    pdf.ln(2)
    pdf.subsection_title("Key Design Patterns")
    patterns = [
        "Dependency Injection: FastAPI Depends() for auth, DB sessions, services",
        "Singleton Pattern: Question bank service, LLM client cached via lru_cache / module-level instances",
        "Repository Pattern: Services encapsulate all DB queries, routers never touch ORM directly",
        "Strategy Pattern: LiteLLM abstracts multiple LLM providers behind a single interface",
        "Observer Pattern: WebSocket voice pipeline streams events (transcript, next_question, error)",
    ]
    for p in patterns:
        pdf.bullet(p)

    # ========== 4. DIRECTORY STRUCTURE ==========
    pdf.add_page()
    pdf.chapter_title("4. Directory Structure")
    pdf.code_text(
        "ai-interviewer/\n"
        "|-- backend/\n"
        "|   |-- app/\n"
        "|   |   |-- main.py                 # FastAPI entry point\n"
        "|   |   |-- config.py               # Pydantic settings (env vars)\n"
        "|   |   |-- database.py             # Async SQLAlchemy engine/session\n"
        "|   |   |-- dependencies.py         # Auth dependency injection\n"
        "|   |   |-- models/\n"
        "|   |   |   |-- user.py             # User model\n"
        "|   |   |   |-- interview.py        # Session, Module, Turn models\n"
        "|   |   |   |-- consent.py          # Consent event model\n"
        "|   |   |-- routers/\n"
        "|   |   |   |-- auth.py             # Google OAuth + JWT endpoints\n"
        "|   |   |   |-- interviews.py       # Interview flow endpoints\n"
        "|   |   |   |-- voice.py            # WebSocket voice endpoint\n"
        "|   |   |   |-- admin.py            # Admin dashboard endpoints\n"
        "|   |   |-- schemas/                # Pydantic request/response models\n"
        "|   |   |-- services/\n"
        "|   |   |   |-- auth_service.py\n"
        "|   |   |   |-- interview_service.py\n"
        "|   |   |   |-- question_bank_service.py\n"
        "|   |   |   |-- module_state_service.py\n"
        "|   |   |   |-- answer_parser_service.py\n"
        "|   |   |   |-- prompt_service.py\n"
        "|   |   |   |-- voice_orchestrator.py\n"
        "|   |   |   |-- asr_service.py\n"
        "|   |   |   |-- transcript_corrector.py\n"
        "|   |   |-- llm/\n"
        "|   |       |-- client.py           # LiteLLM wrapper\n"
        "|   |-- prompts/                    # 7 LLM prompt templates\n"
        "|   |-- seed_data/question_banks/   # M1-M8 JSON question files\n"
        "|   |-- migrations/                 # Alembic DB migrations\n"
        "|   |-- tests/                      # Pytest test suite\n"
        "|   |-- requirements.txt\n"
        "|   |-- Dockerfile\n"
        "|-- frontend/\n"
        "|   |-- src/app/                    # Next.js pages (App Router)\n"
        "|   |-- src/components/             # React components\n"
        "|   |-- src/lib/                    # API clients\n"
        "|   |-- src/store/                  # Zustand stores\n"
        "|   |-- src/hooks/                  # Custom React hooks\n"
        "|   |-- src/types/                  # TypeScript type definitions\n"
        "|   |-- package.json\n"
        "|   |-- Dockerfile\n"
        "|-- docker-compose.yml\n"
        "|-- .env.example\n"
        "|-- README.md"
    )

    # ========== 5. BACKEND FILE-BY-FILE ==========
    pdf.add_page()
    pdf.chapter_title("5. Backend - File-by-File Breakdown")

    # 5.1
    pdf.section_title("5.1 Entry Point & Configuration")

    pdf.subsection_title("main.py - FastAPI Application Entry Point")
    pdf.body_text(
        "Creates the FastAPI app instance with lifespan handler for startup/shutdown. "
        "Configures CORS middleware, global exception handler, health check endpoint, and includes "
        "all API routers (auth, interviews, voice, admin) under the /api/v1 prefix."
    )
    pdf.bullet("Lifespan: Initializes database on startup, logs shutdown")
    pdf.bullet("CORS: Configured from environment (allow_origins, credentials, all methods/headers)")
    pdf.bullet("Exception handler: Returns detailed errors in dev, generic in production")
    pdf.bullet("Health endpoint: Returns app version, DB status, timestamp")

    pdf.ln(3)
    pdf.subsection_title("config.py - Application Settings")
    pdf.body_text(
        "Uses pydantic-settings to load all configuration from environment variables and .env files. "
        "Defines defaults for all settings. Includes a model_validator to auto-convert postgresql:// "
        "to postgresql+asyncpg:// for Railway compatibility."
    )
    pdf.bullet("40+ configuration parameters organized by concern")
    pdf.bullet("lru_cache on get_settings() for singleton behavior")
    pdf.bullet("Supports: database, Redis, LLM, auth, ASR, observability, storage settings")

    pdf.ln(3)
    pdf.subsection_title("database.py - Async Database Layer")
    pdf.body_text(
        "Sets up async SQLAlchemy engine and session factory using asyncpg driver. "
        "Provides get_session() async generator for dependency injection and init_db() "
        "for table creation on startup."
    )

    pdf.ln(3)
    pdf.subsection_title("dependencies.py - Auth Dependencies")
    pdf.body_text(
        "Defines FastAPI dependency functions for JWT authentication: "
        "get_current_user() extracts and validates the Bearer token, "
        "get_current_admin() additionally checks the is_admin flag."
    )

    # 5.2 Models
    pdf.add_page()
    pdf.section_title("5.2 Database Models")

    pdf.subsection_title("models/user.py - User Model")
    pdf.body_text(
        "SQLAlchemy model for the users table. Fields: id (UUID primary key), email (unique, indexed), "
        "display_name, auth_provider_id (Google OAuth sub), sex, age, profile_completed (boolean), "
        "is_admin (boolean), created_at, updated_at. Has relationships to consent_events and interview_sessions."
    )

    pdf.subsection_title("models/interview.py - Interview Models (3 tables)")
    pdf.body_text("InterviewSession: Represents a full interview session.")
    pdf.bullet("Fields: id, user_id (FK), status (active/completed/paused), input_mode, language_preference")
    pdf.bullet("JSONB fields: settings (sensitivity_settings, topic preferences)")
    pdf.bullet("Timestamps: started_at, ended_at, total_duration_sec")
    pdf.ln(2)
    pdf.body_text("InterviewModule: Tracks progress within a specific module (M1-M8).")
    pdf.bullet("Fields: id, session_id (FK), module_id, status, question_count")
    pdf.bullet("Scoring: coverage_score, confidence_score (floats)")
    pdf.bullet("JSONB: signals_captured (array), completion_eval (LLM evaluation)")
    pdf.ln(2)
    pdf.body_text("InterviewTurn: Individual Q&A turn within an interview.")
    pdf.bullet("Question fields: question_text, question_meta (JSONB)")
    pdf.bullet("Answer fields: answer_text, answer_raw_transcript, answer_language, answer_structured (JSONB)")
    pdf.bullet("Audio fields: audio_meta (JSONB with duration, VAD events, ASR confidence), audio_storage_ref")

    pdf.subsection_title("models/consent.py - Consent Event Model")
    pdf.body_text(
        "Tracks user consent for various purposes (interview, audio_storage, sensitive_topics, data_retention). "
        "Fields: consent_type, consent_version, accepted (boolean), consent_metadata (JSONB)."
    )

    # 5.3 Routers
    pdf.add_page()
    pdf.section_title("5.3 API Routers (Endpoints)")

    pdf.subsection_title("routers/auth.py - Authentication Endpoints")
    pdf.body_text("Prefix: /api/v1/auth")
    pdf.bullet("POST /google - Accepts Google OAuth credential, verifies token, creates/finds user, returns JWT")
    pdf.bullet("GET /me - Returns current authenticated user info (requires Bearer token)")
    pdf.bullet("PUT /profile - Updates user profile (display_name, sex, age), marks profile as completed")

    pdf.ln(3)
    pdf.subsection_title("routers/interviews.py - Interview Flow Endpoints")
    pdf.body_text("Prefix: /api/v1/interviews - Core interview functionality")
    pdf.bullet("POST /start - Start full interview (creates session, initializes M1-M4 modules, returns first question)")
    pdf.bullet("POST /start-module - Start a specific single module (for module selection screen)")
    pdf.bullet("POST /{session_id}/answer - Submit answer to current question (triggers satisfaction check)")
    pdf.bullet("POST /{session_id}/next-question - Get next question (adaptive LLM-driven selection)")
    pdf.bullet("POST /{session_id}/skip - Skip current question and get next")
    pdf.bullet("POST /{session_id}/pause - Pause interview session")
    pdf.bullet("POST /{session_id}/resume - Resume paused session")
    pdf.bullet("GET /{session_id}/status - Get full interview status (module progress, current question)")
    pdf.bullet("GET /user/{user_id}/modules - Get module completion status for module selection UI")
    pdf.bullet("POST /{session_id}/complete-module - Mark current module complete, return to selection")

    pdf.ln(3)
    pdf.subsection_title("routers/voice.py - Voice Interview WebSocket")
    pdf.body_text("WebSocket endpoint at /api/v1/voice/{session_id}")
    pdf.bullet("Accepts binary PCM audio frames (16kHz, mono, 16-bit)")
    pdf.bullet("Sends JSON messages: final_transcript, processing, next_question, error")
    pdf.bullet("Delegates to VoiceOrchestrator service for audio processing pipeline")

    pdf.ln(3)
    pdf.subsection_title("routers/admin.py - Admin Dashboard Endpoints")
    pdf.body_text("Prefix: /api/v1/admin - Requires admin authentication")
    pdf.bullet("GET /users - List all users with their module completion status")
    pdf.bullet("GET /users/{user_id}/transcript - Full Q&A transcript for a user")
    pdf.bullet("GET /users/{user_id}/transcript/download - Download transcript as JSON or CSV")

    # 5.4 Services
    pdf.add_page()
    pdf.section_title("5.4 Services (Business Logic)")

    pdf.subsection_title("services/auth_service.py")
    pdf.body_text(
        "Handles Google OAuth token verification and JWT management. "
        "Core methods: verify_google_token(credential) uses google.oauth2.id_token to validate "
        "the Google credential against the configured client ID. get_or_create_user() finds or "
        "creates users by email. create_access_token() generates JWT with 24-hour expiry."
    )

    pdf.ln(2)
    pdf.subsection_title("services/interview_service.py (CORE - largest service)")
    pdf.body_text(
        "The central orchestrator for the interview flow. This is the most complex service (~500+ lines). "
        "Key methods:"
    )
    pdf.bullet("start_interview(): Creates session, initializes modules (M1-M4 default), returns first question from M1")
    pdf.bullet("submit_answer(): Records the answer as an InterviewTurn, calls AnswerParserService to check satisfaction")
    pdf.bullet("get_next_question(): Adaptive question selection - uses LLM to decide next question based on conversation history, signal coverage, and module completion criteria. This is the most complex method (~300 lines)")
    pdf.bullet("skip_question(): Records skip, moves to next question")
    pdf.bullet("pause_interview() / resume_interview(): Session state management")
    pdf.bullet("complete_module_and_exit(): Marks module complete with LLM evaluation, returns to selection")

    pdf.ln(2)
    pdf.subsection_title("services/question_bank_service.py")
    pdf.body_text(
        "Loads and manages the 8 question bank JSON files from seed_data/. "
        "Implements in-memory caching. Methods: load_question_bank(), get_first_question(), "
        "get_next_static_question() (fallback when LLM unavailable), get_questions_for_signal(), "
        "get_module_completion_criteria(), get_concept_card() (for M8 concept tests)."
    )

    pdf.ln(2)
    pdf.subsection_title("services/module_state_service.py")
    pdf.body_text(
        "Manages InterviewModule records. Methods: initialize_modules() creates module records "
        "for a session, get_active_module() fetches the current active module, "
        "update_module_after_answer() increments question count and updates signals, "
        "complete_module() marks module complete and activates the next one."
    )

    pdf.ln(2)
    pdf.subsection_title("services/answer_parser_service.py")
    pdf.body_text(
        "Uses LLM to judge if an answer is satisfactory or needs a follow-up probe. "
        "Method: is_answer_satisfactory(question, answer, target_signal) returns (bool, reason). "
        "Falls back to treating answers as satisfactory if the LLM call fails."
    )

    pdf.ln(2)
    pdf.subsection_title("services/prompt_service.py")
    pdf.body_text(
        "Loads and formats prompt templates from the /prompts/ directory. "
        "Implements in-memory caching with hot-reload on file changes. "
        "Provides typed methods for each prompt: get_answer_parser_prompt(), "
        "get_interviewer_question_prompt(), get_module_completion_prompt(), get_followup_probe_prompt()."
    )

    pdf.ln(2)
    pdf.subsection_title("services/voice_orchestrator.py")
    pdf.body_text(
        "Manages WebSocket voice interview sessions. Handles PCM audio frame buffering, "
        "VAD (voice activity detection) triggers, delegates to ASR service for transcription, "
        "and coordinates with interview service for question flow."
    )

    pdf.ln(2)
    pdf.subsection_title("services/asr_service.py")
    pdf.body_text(
        "Transcribes audio using OpenAI Whisper API. Handles language detection "
        "(English, Hindi, Hinglish). Converts PCM audio to WAV format for API submission."
    )

    pdf.ln(2)
    pdf.subsection_title("services/transcript_corrector.py")
    pdf.body_text(
        "Post-processes ASR transcriptions using LLM to correct common speech recognition errors, "
        "especially for code-switched Hinglish text."
    )

    # 5.5 LLM
    pdf.add_page()
    pdf.section_title("5.5 LLM Integration")

    pdf.subsection_title("llm/client.py - LiteLLM Wrapper")
    pdf.body_text(
        "Thin wrapper around LiteLLM that provides: retry logic with configurable max_retries, "
        "JSON response validation and parsing, temperature/max_tokens/timeout configuration, "
        "and optional Langfuse logging integration for LLM call tracing."
    )
    pdf.bullet("Uses LiteLLM to support multiple providers (OpenAI, Anthropic, etc.) via a single interface")
    pdf.bullet("Default model: gpt-4-turbo-preview (configurable via LLM_MODEL env var)")
    pdf.bullet("Retry logic: Retries on API errors with exponential backoff")

    # 5.6 Prompts
    pdf.ln(4)
    pdf.section_title("5.6 Prompt Templates (7 files)")
    pdf.body_text("Located in backend/prompts/. Each is a text file with placeholders for dynamic content.")

    prompt_data = [
        ("interviewer_question.txt (7KB)", "Main prompt for adaptive question selection. Defines the Darpan persona as a 'warm, curious interviewer'. Includes module context, signal targets, completion criteria, question intent system (EXPLORE, DEEPEN, CONTRAST, CLARIFY, RESOLVE), and pacing strategy across 3 phases."),
        ("answer_satisfaction.txt (1.1KB)", "Judges if an answer is satisfactory. Input: question text, answer text, target signal. Output: JSON with satisfactory (bool) and reason."),
        ("answer_parser.txt (10.9KB)", "Extracts structured insights from answers - identifies signals captured, specificity level, confidence score, sentiment, contradictions, and open loops for follow-up."),
        ("followup_probe.txt (2KB)", "Generates follow-up questions when answers are vague or insufficient. Same output format as interviewer_question."),
        ("module_completion.txt (5.3KB)", "Evaluates whether a module can be completed. Calculates coverage and confidence scores. Returns detailed completion_eval JSON."),
        ("acknowledgment.txt (278B)", "Template for acknowledging user's previous answer before asking next question."),
        ("transcript_correction.txt (745B)", "Corrects ASR transcription errors in multilingual (English/Hindi) text."),
    ]
    for name, desc in prompt_data:
        pdf.subsection_title(name)
        pdf.body_text(desc)

    # 5.7 Question Banks
    pdf.add_page()
    pdf.section_title("5.7 Question Banks (Seed Data)")
    pdf.body_text(
        "8 JSON files in backend/seed_data/question_banks/ define all interview questions. "
        "Each file contains a ModuleQuestionBank with module metadata and an array of Question objects."
    )

    modules = [
        ("M1 - Core Identity & Context", "10 questions", "Demographics, psychographics (city, occupation, income, household, education)"),
        ("M2 - Preferences & Values", "8 questions", "Brand preferences, personal values, priorities, aspirations"),
        ("M3 - Purchase Decision Logic", "8 questions", "Purchase criteria, decision-making process, price sensitivity, brand loyalty"),
        ("M4 - Lifestyle & Grooming Routines", "8 questions", "Daily routines, grooming habits, product usage, lifestyle choices"),
        ("M5 - Sensory & Aesthetic Preferences", "8 questions", "Sensory preferences (scent, texture), aesthetic tastes, packaging appeal"),
        ("M6 - Body Wash Deep-Dive", "11 questions", "Category-specific deep dive: current usage, switching behavior, pain points"),
        ("M7 - Media & Influence", "6 questions", "Media consumption, influencer impact, ad recall, purchase triggers"),
        ("M8 - Concept Test", "64 questions", "Product concept evaluation with structured scoring (interest, uniqueness, purchase intent). Includes concept cards with images."),
    ]
    for name, count, desc in modules:
        pdf.subsection_title(f"{name} ({count})")
        pdf.body_text(desc)

    pdf.ln(3)
    pdf.subsection_title("Question Object Structure")
    pdf.code_text(
        "{\n"
        '  "question_id": "M1_q01",\n'
        '  "question_text": "Where do you currently live?",\n'
        '  "question_type": "open_text",  // or: numeric, single_select,\n'
        '                                 //     multi_select, scale, rank_order,\n'
        '                                 //     matrix_scale, matrix_premium\n'
        '  "target_signals": ["geography_climate"],\n'
        '  "follow_up_triggers": ["vague_location"],\n'
        '  "priority": 1,  // 1=must-ask, 2=important, 3=nice-to-have\n'
        '  "estimated_seconds": 30,\n'
        '  "intent": "EXPLORE",  // EXPLORE, DEEPEN, CONTRAST, CLARIFY, RESOLVE\n'
        '  "options": [...],  // for select types\n'
        '  "scale_min": 1, "scale_max": 5,  // for scale types\n'
        '  "is_followup": false,\n'
        '  "parent_question_id": null\n'
        "}"
    )

    # 5.8 Schemas
    pdf.add_page()
    pdf.section_title("5.8 Schemas (Pydantic Models)")
    pdf.body_text(
        "The schemas/ directory contains Pydantic v2 models for API request/response validation. "
        "These ensure type safety at the API boundary."
    )
    pdf.bullet("Auth schemas: GoogleAuthRequest, AuthResponse, UserResponse, ProfileUpdateRequest")
    pdf.bullet("Interview schemas: StartInterviewRequest, SubmitAnswerRequest, InterviewStatusResponse, QuestionResponse, ModuleStatusResponse")
    pdf.bullet("Admin schemas: UserListResponse, TranscriptResponse")
    pdf.bullet("Common schemas: HealthResponse, ErrorResponse")

    # ========== 6. FRONTEND ==========
    pdf.add_page()
    pdf.chapter_title("6. Frontend - File-by-File Breakdown")

    pdf.section_title("6.1 Pages & Routing (Next.js App Router)")
    pdf.body_text("The frontend uses Next.js 14 App Router for file-based routing.")

    pdf.subsection_title("app/page.tsx - Home Page")
    pdf.body_text("Landing page with Darpan Labs branding and a 'Get Started' CTA that links to /login.")

    pdf.subsection_title("app/login/page.tsx - Login Page")
    pdf.body_text(
        "Displays Google Sign-In button via @react-oauth/google GoogleLogin component. "
        "On successful credential, calls POST /auth/google and stores JWT in localStorage."
    )

    pdf.subsection_title("app/profile/page.tsx - Profile Setup")
    pdf.body_text(
        "First-time user onboarding: collects display name, sex, and age. "
        "Calls PUT /profile to complete the profile. Protected by auth guard."
    )

    pdf.subsection_title("app/create/page.tsx - Module Selection")
    pdf.body_text(
        "Shows all 8 interview modules as cards with completion status (completed, in-progress, not started). "
        "User can select which module to start next. Calls GET /interviews/user/{id}/modules."
    )

    pdf.subsection_title("app/interview/page.tsx - Interview Interface")
    pdf.body_text(
        "Main interview UI. Shows current question, text input area, voice recording controls, "
        "skip/pause buttons, and module progress indicator. Connects to interview store for state management."
    )

    pdf.subsection_title("app/admin/page.tsx - Admin Dashboard")
    pdf.body_text(
        "Shows list of all users with module completion status. "
        "Click on user to view their full Q&A transcript. Requires admin privileges."
    )

    pdf.subsection_title("app/layout.tsx - Root Layout")
    pdf.body_text(
        "Wraps the entire app with AuthProvider (Google OAuth), custom fonts (Inter, JetBrains Mono), "
        "Tailwind dark theme, and Sonner toast notification provider."
    )

    # 6.2 Components
    pdf.add_page()
    pdf.section_title("6.2 Components")

    pdf.subsection_title("components/auth/AuthProvider.tsx")
    pdf.body_text(
        "Wraps children with GoogleOAuthProvider using NEXT_PUBLIC_GOOGLE_CLIENT_ID. "
        "Initializes auth state on mount by checking localStorage for existing token."
    )

    pdf.subsection_title("components/auth/AuthGuard.tsx")
    pdf.body_text(
        "Route protection component. Checks if user is authenticated and profile is completed. "
        "Redirects to /login or /profile as appropriate."
    )

    pdf.subsection_title("components/interview/ (Interview UI Components)")
    pdf.body_text(
        "Multiple components for the interview experience: QuestionCard (displays question with type-specific UI), "
        "AnswerInput (text area or voice recording), ModuleProgress (progress bar), "
        "ModuleTransition (animation between modules), VoiceControls (record/stop/processing states)."
    )

    pdf.subsection_title("components/navigation/")
    pdf.body_text("Navigation bar with user menu, home link, and admin link (if admin).")

    # 6.3 Stores
    pdf.ln(4)
    pdf.section_title("6.3 State Management (Zustand Stores)")

    pdf.subsection_title("store/authStore.ts")
    pdf.body_text(
        "Manages authentication state: user object, JWT token, loading/initialized flags. "
        "Methods: loginWithGoogle(credential) -> POST /auth/google, updateProfile(data) -> PUT /profile, "
        "logout() clears localStorage, initialize() restores session from localStorage."
    )

    pdf.subsection_title("store/interviewStore.ts")
    pdf.body_text(
        "Manages interview session state: sessionId, status, currentModule, currentQuestion, modulePlan, "
        "currentAnswer, voice state (isRecording, finalTranscript, isProcessingVoice). "
        "Methods: startInterview(), submitAnswer(), getNextQuestion(), skipQuestion(), pauseInterview(), "
        "resumeInterview(), and voice-specific methods."
    )

    # 6.4 API & Hooks
    pdf.ln(4)
    pdf.section_title("6.4 API Client & Hooks")

    pdf.subsection_title("lib/api.ts - Base API Client")
    pdf.body_text(
        "Custom Fetch-based HTTP client. Auto-injects JWT Bearer token. "
        "Handles 401 responses by clearing token and redirecting to /login. "
        "Methods: get(), post(), put(), delete(). Singleton instance exported."
    )

    pdf.subsection_title("lib/interviewApi.ts - Interview API Functions")
    pdf.body_text("Typed API functions for all interview endpoints. Each function wraps api.post()/api.get() calls.")

    pdf.subsection_title("lib/adminApi.ts - Admin API Functions")
    pdf.body_text("Typed API functions for admin endpoints (user list, transcripts, downloads).")

    pdf.subsection_title("hooks/useVoice.ts - Voice Recording Hook")
    pdf.body_text(
        "Custom React hook for voice interviews. Manages WebSocket connection to /voice/{session_id}, "
        "captures microphone audio via MediaRecorder API, runs VAD (Voice Activity Detection) "
        "via @ricky0123/vad-web, sends binary PCM frames, and receives transcription results."
    )

    # 6.5 Types
    pdf.ln(4)
    pdf.section_title("6.5 Types")
    pdf.subsection_title("types/interview.ts")
    pdf.body_text(
        "TypeScript type definitions for the interview domain: InterviewSession, InterviewModule, "
        "InterviewTurn, Question, ModuleStatus, InterviewStatus, AnswerSubmission, etc."
    )

    # ========== 7. FEATURE MAP ==========
    pdf.add_page()
    pdf.chapter_title("7. Feature Map & Connections")
    pdf.body_text("How the major features connect across frontend and backend:")

    features = [
        ("Google OAuth Login",
         "Frontend: login/page.tsx -> AuthProvider -> authStore.loginWithGoogle()\n"
         "Backend: routers/auth.py POST /google -> auth_service.verify_google_token() -> auth_service.get_or_create_user() -> JWT"),
        ("Profile Setup",
         "Frontend: profile/page.tsx -> authStore.updateProfile()\n"
         "Backend: routers/auth.py PUT /profile -> DB user update"),
        ("Module Selection",
         "Frontend: create/page.tsx -> interviewApi.getUserModules()\n"
         "Backend: routers/interviews.py GET /user/{id}/modules -> module_state_service"),
        ("Start Interview",
         "Frontend: interviewStore.startInterview() -> interviewApi\n"
         "Backend: interviews.py POST /start -> interview_service.start_interview() -> module_state_service.initialize_modules() -> question_bank_service.get_first_question()"),
        ("Submit Answer",
         "Frontend: interviewStore.submitAnswer() -> interviewApi\n"
         "Backend: interviews.py POST /answer -> interview_service.submit_answer() -> answer_parser_service.is_answer_satisfactory() -> LLM call"),
        ("Get Next Question",
         "Frontend: interviewStore.getNextQuestion() -> interviewApi\n"
         "Backend: interviews.py POST /next-question -> interview_service.get_next_question() -> prompt_service + LLM call for adaptive selection"),
        ("Voice Interview",
         "Frontend: useVoice hook -> WebSocket -> binary PCM audio\n"
         "Backend: voice.py WebSocket -> voice_orchestrator -> asr_service (Whisper) -> transcript_corrector -> interview_service"),
        ("Admin Transcripts",
         "Frontend: admin/page.tsx -> adminApi\n"
         "Backend: admin.py GET /users, GET /transcript -> DB query joins"),
    ]
    for name, flow in features:
        pdf.subsection_title(name)
        pdf.code_text(flow)

    # ========== 8. AUTH FLOW ==========
    pdf.add_page()
    pdf.chapter_title("8. Authentication Flow")
    pdf.body_text("Detailed authentication flow from login to protected API calls:")
    pdf.ln(2)
    pdf.code_text(
        "1. User clicks 'Sign in with Google' on /login page\n"
        "2. @react-oauth/google shows Google consent popup\n"
        "3. Google returns credential (ID token) to frontend\n"
        "4. Frontend calls POST /api/v1/auth/google with {credential}\n"
        "5. Backend auth_service.verify_google_token():\n"
        "   - Uses google.oauth2.id_token.verify_oauth2_token()\n"
        "   - Validates against GOOGLE_CLIENT_ID\n"
        "   - Extracts: email, name, sub (provider ID)\n"
        "6. Backend auth_service.get_or_create_user():\n"
        "   - Looks up user by email\n"
        "   - Creates new user if not found\n"
        "7. Backend creates JWT (HS256, 24h expiry):\n"
        "   - Payload: {sub: user_id, email, exp}\n"
        "8. Returns: {access_token, user: {...}}\n"
        "9. Frontend stores token in localStorage (darpan_token)\n"
        "10. All subsequent API calls include:\n"
        "    Authorization: Bearer <token>\n"
        "11. Backend dependencies.py get_current_user():\n"
        "    - Extracts token from header\n"
        "    - Decodes JWT, validates expiry\n"
        "    - Returns user object for route handler"
    )

    # ========== 9. INTERVIEW FLOW ==========
    pdf.add_page()
    pdf.chapter_title("9. Interview Flow (Core Feature)")
    pdf.body_text("The interview is the central feature of the platform. Here is the complete flow:")
    pdf.ln(2)
    pdf.code_text(
        "1. USER STARTS INTERVIEW\n"
        "   - Selects module(s) on /create page\n"
        "   - POST /start or /start-module\n"
        "   - Backend creates InterviewSession + InterviewModule records\n"
        "   - Returns first question from question bank\n"
        "\n"
        "2. QUESTION-ANSWER LOOP\n"
        "   a) Frontend displays question (type-specific UI)\n"
        "   b) User types or speaks answer\n"
        "   c) POST /answer with {answer_text, question_id}\n"
        "   d) Backend records InterviewTurn\n"
        "   e) LLM checks answer satisfaction:\n"
        "      - Satisfactory -> move to next question\n"
        "      - Unsatisfactory -> generate follow-up probe\n"
        "   f) POST /next-question\n"
        "   g) Backend adaptive selection:\n"
        "      - Checks signal coverage for current module\n"
        "      - LLM selects best next question based on:\n"
        "        * Conversation history\n"
        "        * Uncovered signals\n"
        "        * Question priority\n"
        "        * Module completion criteria\n"
        "      - Falls back to static order if LLM fails\n"
        "   h) Returns next question to frontend\n"
        "\n"
        "3. MODULE COMPLETION\n"
        "   - After sufficient questions answered:\n"
        "   - LLM evaluates module completion:\n"
        "     * Coverage score (% of target signals captured)\n"
        "     * Confidence score (quality of captured signals)\n"
        "   - If criteria met: mark module complete\n"
        "   - Transition to next module or return to selection\n"
        "\n"
        "4. SESSION END\n"
        "   - All selected modules completed\n"
        "   - Session marked as completed\n"
        "   - User can start new modules from /create"
    )

    # ========== 10. VOICE ==========
    pdf.add_page()
    pdf.chapter_title("10. Voice Interview System")
    pdf.body_text("The voice system enables real-time spoken interviews via WebSocket:")
    pdf.ln(2)
    pdf.subsection_title("Frontend (useVoice.ts)")
    pdf.bullet("Opens WebSocket to ws://localhost:8000/api/v1/voice/{session_id}")
    pdf.bullet("Captures microphone audio via MediaRecorder (PCM 16kHz, mono, 16-bit)")
    pdf.bullet("Runs VAD (Voice Activity Detection) using @ricky0123/vad-web with ONNX model")
    pdf.bullet("Sends binary audio frames over WebSocket as they're captured")
    pdf.bullet("Receives JSON events: {type: 'final_transcript', text: '...'}, {type: 'next_question', ...}")

    pdf.ln(3)
    pdf.subsection_title("Backend Pipeline")
    pdf.bullet("voice.py: WebSocket endpoint, handles connection lifecycle")
    pdf.bullet("voice_orchestrator.py: Buffers audio frames, detects speech boundaries via VAD events")
    pdf.bullet("asr_service.py: Sends audio to OpenAI Whisper API, returns transcript + detected language")
    pdf.bullet("transcript_corrector.py: LLM post-processes transcript for accuracy (especially Hinglish)")
    pdf.bullet("interview_service.py: Records answer, gets next question, sends back via WebSocket")

    # ========== 11. ADMIN ==========
    pdf.ln(6)
    pdf.chapter_title("11. Admin Dashboard")
    pdf.body_text(
        "The admin dashboard at /admin provides oversight of all interview data. "
        "Access requires the is_admin flag on the user record."
    )
    pdf.bullet("User List: Shows all registered users with email, name, profile status, and module completion (M1-M8 checkmarks)")
    pdf.bullet("Transcript View: Click any user to see their full Q&A history across all modules")
    pdf.bullet("Transcript Download: Export as JSON or CSV for external analysis")
    pdf.bullet("Module Status: Visual indicators showing completed/in-progress/not-started for each module")

    # ========== 12. DATABASE SCHEMA ==========
    pdf.add_page()
    pdf.chapter_title("12. Database Schema")
    pdf.code_text(
        "users\n"
        "  |-- id (UUID PK)\n"
        "  |-- email (unique, indexed)\n"
        "  |-- display_name\n"
        "  |-- auth_provider_id (Google sub)\n"
        "  |-- sex, age\n"
        "  |-- profile_completed (bool)\n"
        "  |-- is_admin (bool)\n"
        "  |-- created_at, updated_at\n"
        "  |\n"
        "  |--< consent_events (FK: user_id)\n"
        "  |     |-- id (UUID PK)\n"
        "  |     |-- consent_type, consent_version\n"
        "  |     |-- accepted (bool)\n"
        "  |     |-- consent_metadata (JSONB)\n"
        "  |     |-- created_at\n"
        "  |\n"
        "  |--< interview_sessions (FK: user_id)\n"
        "        |-- id (UUID PK)\n"
        "        |-- status (active/completed/paused)\n"
        "        |-- input_mode, language_preference\n"
        "        |-- settings (JSONB)\n"
        "        |-- started_at, ended_at, total_duration_sec\n"
        "        |\n"
        "        |--< interview_modules (FK: session_id)\n"
        "        |     |-- id (UUID PK)\n"
        "        |     |-- module_id (M1-M8)\n"
        "        |     |-- status, question_count\n"
        "        |     |-- coverage_score, confidence_score\n"
        "        |     |-- signals_captured (JSONB)\n"
        "        |     |-- completion_eval (JSONB)\n"
        "        |\n"
        "        |--< interview_turns (FK: session_id)\n"
        "              |-- id (UUID PK)\n"
        "              |-- module_id, turn_index, role\n"
        "              |-- question_text, question_meta (JSONB)\n"
        "              |-- answer_text, answer_structured (JSONB)\n"
        "              |-- audio_meta (JSONB), audio_storage_ref\n"
        "              |-- created_at"
    )

    # ========== 13. DEVOPS ==========
    pdf.add_page()
    pdf.chapter_title("13. DevOps & Deployment")

    pdf.subsection_title("Docker Configuration")
    pdf.body_text(
        "docker-compose.yml defines 4 services: db (pgvector/pgvector:pg16), redis (redis:7-alpine), "
        "backend (FastAPI), frontend (Next.js). Health checks ensure proper startup ordering."
    )

    pdf.subsection_title("Backend Dockerfile")
    pdf.body_text(
        "Python base image, installs requirements.txt, copies app code, "
        "runs uvicorn on port 8000. Supports hot-reload via volume mount in dev."
    )

    pdf.subsection_title("Frontend Dockerfile")
    pdf.body_text(
        "Node base image, npm install, builds Next.js app, serves on port 3000. "
        "Build args for NEXT_PUBLIC_GOOGLE_CLIENT_ID (baked into client bundle at build time)."
    )

    pdf.subsection_title("Database Migrations (Alembic)")
    pdf.body_text(
        "Alembic configured in backend/alembic.ini with migration scripts in backend/migrations/versions/. "
        "2 migration files: initial schema (001_initial.py) and profile/admin fields addition."
    )

    pdf.subsection_title("Environment Variables")
    pdf.body_text("40+ environment variables across 8 categories:")
    pdf.bullet("Application: APP_NAME, DEBUG, ENVIRONMENT")
    pdf.bullet("Database: DATABASE_URL, DATABASE_ECHO")
    pdf.bullet("Redis: REDIS_URL")
    pdf.bullet("LLM: LLM_PROVIDER, LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS")
    pdf.bullet("API Keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPGRAM_API_KEY")
    pdf.bullet("Auth: AUTH_SECRET_KEY, GOOGLE_CLIENT_ID")
    pdf.bullet("Observability: SENTRY_DSN, LANGFUSE_*")
    pdf.bullet("Frontend: NEXT_PUBLIC_API_URL, NEXT_PUBLIC_GOOGLE_CLIENT_ID")

    # ========== 14. CODE QUALITY ==========
    pdf.add_page()
    pdf.chapter_title("14. Code Quality Analysis")

    pdf.section_title("Strengths")
    strengths = [
        "Clean layered architecture: routers (API) -> services (logic) -> models (data). No business logic in routers.",
        "Comprehensive async support: All DB operations, HTTP calls, and WebSocket handling use async/await.",
        "Strong type safety: Pydantic v2 schemas at API boundary, TypeScript on frontend, Python type hints throughout.",
        "Dependency injection: FastAPI Depends() pattern used consistently for auth, DB sessions, and services.",
        "Singleton pattern: Expensive services (question bank, LLM client) properly cached.",
        "Error handling: Custom exception handlers, try/catch at service boundaries, graceful fallbacks.",
        "Environment-based config: All secrets and settings loaded from environment, no hardcoded values.",
        "Comprehensive test suite: Unit tests for config, models, schemas, services, and end-to-end flows.",
        "Prompt engineering: Well-structured prompt templates with clear output format specifications.",
        "Database design: Proper use of JSONB for flexible schema, UUIDs for primary keys, proper FK relationships.",
    ]
    for s in strengths:
        pdf.bullet(s)

    pdf.add_page()
    pdf.section_title("Issues & Observations")
    issues = [
        "Next.js 14.1.0 has a known security vulnerability (CVE flagged by npm audit as critical). Should upgrade to latest 14.x patch.",
        "API keys in .env.example still have placeholder values ('your-openai-api-key'). The LLM-powered adaptive question flow won't work without real OpenAI keys.",
        "AUTH_SECRET_KEY default is 'your-secret-key-change-in-production' - insecure if accidentally used in production.",
        "The backend .env.example does not include GOOGLE_CLIENT_ID, though the config.py expects it. This could cause confusion.",
        "Frontend API client doesn't have request retry logic. A failed API call (e.g., network blip) requires manual retry.",
        "No rate limiting on API endpoints. The LLM-calling endpoints could be abused to run up API costs.",
        "WebSocket voice endpoint doesn't validate the JWT token from query params - only session_id is checked.",
        "Alembic migrations and SQLAlchemy create_all() both exist - potential for schema drift if both are used.",
    ]
    for s in issues:
        pdf.bullet(s)

    # ========== 15. OPTIMIZATION RECOMMENDATIONS ==========
    pdf.add_page()
    pdf.chapter_title("15. Optimization Recommendations")

    pdf.section_title("Code Duplication")

    pdf.subsection_title("1. interview_service.py get_next_question() - Method Too Large")
    pdf.body_text(
        "The get_next_question() method is ~300 lines and handles: checking module completion, "
        "LLM-based question selection, static fallback, module transitions, and error handling. "
        "RECOMMENDATION: Extract into smaller focused methods: _check_module_completion(), "
        "_select_question_via_llm(), _select_question_static_fallback(), _handle_module_transition(). "
        "This improves testability and readability."
    )

    pdf.subsection_title("2. Overlapping Start Endpoints")
    pdf.body_text(
        "POST /start and POST /start-module have overlapping module initialization logic. "
        "RECOMMENDATION: Extract a shared _initialize_session() helper and have both endpoints call it "
        "with different module lists."
    )

    pdf.subsection_title("3. Frontend API Client Duplication")
    pdf.body_text(
        "api.ts, interviewApi.ts, and adminApi.ts have similar patterns for error handling and response parsing. "
        "RECOMMENDATION: interviewApi and adminApi already use the base client well; the duplication is minor. "
        "Consider adding request retry logic to the base api.ts client for resilience."
    )

    pdf.subsection_title("4. Question Selection Logic")
    pdf.body_text(
        "Both get_next_static_question() in QuestionBankService and parts of get_next_question() in "
        "InterviewService iterate through questions to find the next unanswered one. "
        "RECOMMENDATION: Centralize 'answered question tracking' into a shared utility to avoid "
        "duplicating the already-answered check."
    )

    pdf.ln(4)
    pdf.section_title("Performance Optimizations")

    pdf.subsection_title("5. Database Query N+1 in Admin Endpoints")
    pdf.body_text(
        "The admin /users endpoint may load modules separately per user. "
        "RECOMMENDATION: Use SQLAlchemy joinedload/selectinload to eager-load module status in a single query."
    )

    pdf.subsection_title("6. LLM Call Latency")
    pdf.body_text(
        "Each answer submission triggers an LLM satisfaction check, and each next-question request triggers "
        "an LLM selection call. These are sequential. "
        "RECOMMENDATION: Consider combining the satisfaction check and next-question selection into a single "
        "LLM call to halve the latency. Alternatively, pipeline them with asyncio.gather() where possible."
    )

    pdf.subsection_title("7. Question Bank Caching")
    pdf.body_text(
        "Question banks are cached in-memory after first load, which is good. "
        "However, the cache has no invalidation mechanism. "
        "RECOMMENDATION: Add a simple TTL or file-modification-time check for development use, "
        "since the current in-memory cache requires a server restart to pick up question changes."
    )

    pdf.ln(4)
    pdf.section_title("Security Improvements")

    pdf.subsection_title("8. WebSocket Authentication")
    pdf.body_text(
        "The voice WebSocket endpoint should validate JWT tokens. Currently it only checks session_id. "
        "RECOMMENDATION: Accept token as a query parameter and validate it before upgrading to WebSocket."
    )

    pdf.subsection_title("9. Rate Limiting")
    pdf.body_text(
        "No rate limiting exists on any endpoint. LLM-calling endpoints are expensive. "
        "RECOMMENDATION: Add slowapi or a custom rate limiter middleware, especially on /answer and /next-question."
    )

    pdf.subsection_title("10. Upgrade Next.js")
    pdf.body_text(
        "Next.js 14.1.0 has known CVEs. "
        "RECOMMENDATION: Upgrade to the latest 14.x patch release to address the security vulnerability."
    )

    # ========== OUTPUT ==========
    output_path = "/Users/manavrsjain/Desktop/darpan-labs-V2-reorganized/ai-interviewer/AI_Interviewer_Documentation.pdf"
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    return output_path


if __name__ == "__main__":
    generate_doc()
