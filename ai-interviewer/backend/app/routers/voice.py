"""Voice interview WebSocket endpoint."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.voice_orchestrator import VoiceOrchestrator, get_voice_orchestrator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/voice", tags=["Voice"])


@router.websocket("/{session_id}")
async def voice_interview(websocket: WebSocket, session_id: str) -> None:
    """WebSocket endpoint for voice-based interviews.

    Protocol:
        Client → Server:
            Binary frames: complete PCM audio of one utterance (16kHz, mono, 16-bit)
            JSON: {"type": "control", "action": "start" | "stop" | "switch_to_text"}
            JSON: {"type": "text_answer", "text": "user typed answer"}

        Server → Client:
            {"type": "final_transcript", "text": "...", "language": "en", "confidence": 0.95}
            {"type": "processing"}
            {"type": "next_question", "question_id": "...", "question_text": "...", ...}
            {"type": "error", "message": "..."}
            {"type": "timeout_prompt", "message": "..."}
    """
    await websocket.accept()

    orchestrator = get_voice_orchestrator()

    try:
        await orchestrator.handle_voice_session(websocket, session_id)
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"Voice WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json({"type": "error", "message": "Internal server error"})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
