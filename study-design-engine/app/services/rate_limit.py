"""Redis-backed fixed-window rate limiter.

Used by the password-login endpoint to block brute-force attacks. Keyed by
client IP so a single attacker can't get infinite attempts. Fail-open: if
Redis is unreachable we log and allow the request (preferable to locking
users out of their own site when the cache is flapping).
"""
import logging
from typing import Optional

import redis.asyncio as redis
from fastapi import HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def _get_redis() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as exc:
            logger.warning("Could not init Redis for rate limiting: %s", exc)
            return None
    return _redis_client


def _client_ip(request: Request) -> str:
    """Extract client IP honoring reverse-proxy headers (Railway sets these)."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def enforce_rate_limit(
    request: Request,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> None:
    """Raise 429 if the caller has exceeded `limit` hits in `window_seconds`.

    Fixed-window counter: INCR a key and set an EXPIRE if it's new. Simpler
    than a sliding window and fine for login — the worst case is 2× burst at
    window boundaries, which at 5 attempts per 15 min is still unexploitable.
    """
    r = _get_redis()
    if r is None:
        return  # fail-open, already logged

    ip = _client_ip(request)
    key = f"ratelimit:{bucket}:{ip}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window_seconds)
    except Exception as exc:
        logger.warning("Rate-limit Redis op failed, allowing request: %s", exc)
        return

    if count > limit:
        raise HTTPException(
            status_code=429,
            detail=f"Too many attempts. Try again in {window_seconds // 60} minutes.",
        )
