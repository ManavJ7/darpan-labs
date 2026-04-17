FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (cached unless requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY prompts/ ./prompts/
COPY seed_data/ ./seed_data/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/
COPY alembic.ini ./

EXPOSE 8001

# Railway sets $PORT dynamically. On every boot:
# 1. Run DB migrations (alembic)
# 2. Seed / refresh the shared-login user (idempotent; reads $SHARED_LOGIN_USERNAME
#    and $SHARED_LOGIN_PASSWORD; skipped if password is empty)
# 3. Start the API
CMD alembic upgrade head && \
    ( [ -n "$SHARED_LOGIN_PASSWORD" ] && python scripts/seed_shared_user.py \
        --username "${SHARED_LOGIN_USERNAME:-darpantry}" \
        --password "$SHARED_LOGIN_PASSWORD" || echo "[seed] SHARED_LOGIN_PASSWORD not set, skipping shared-user seed" ) && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}
