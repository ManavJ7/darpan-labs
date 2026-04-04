"""Voice interview orchestrator — coordinates ASR, transcript correction, and interview pipeline."""

import asyncio
import json
import logging
from uuid import UUID

import openai
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import async_session_factory
from app.models.interview import InterviewSession, InterviewTurn
from app.schemas.interview import InterviewAnswerRequest
from app.services.asr_service import (
    ASRService,
    ASRResult,
    get_asr_service,
    pcm_to_wav,
    MIN_AUDIO_BYTES,
)
from app.services.interview_service import InterviewService, get_interview_service
from app.services.transcript_corrector import (
    TranscriptCorrectorService,
    get_transcript_corrector,
)

logger = logging.getLogger(__name__)

# Timeout constants
PAUSE_OFFER_TIMEOUT_S = 20


class VoiceOrchestrator:
    """Coordinates the full voice turn cycle."""

    def __init__(
        self,
        asr_service: ASRService | None = None,
        transcript_corrector: TranscriptCorrectorService | None = None,
        interview_service: InterviewService | None = None,
    ):
        self.asr = asr_service or get_asr_service()
        self.corrector = transcript_corrector or get_transcript_corrector()
        self.interview = interview_service or get_interview_service()

    async def handle_voice_session(
        self,
        websocket: WebSocket,
        session_id: str,
    ) -> None:
        """Main voice session loop.

        Receives complete audio segments (from frontend VAD) as binary frames,
        transcribes via Whisper, corrects, and submits through the interview pipeline.

        Args:
            websocket: The active WebSocket connection.
            session_id: Interview session ID.
        """
        interview_session_id = UUID(session_id)

        # Validate session
        if not await self._validate_session(interview_session_id):
            await self._send_error(websocket, "Invalid or inactive interview session")
            return

        is_processing = False
        silence_task: asyncio.Task | None = None

        try:
            logger.info(f"Voice session started for {session_id}")

            # Start silence monitor
            silence_task = asyncio.create_task(self._silence_monitor(websocket))

            # Main loop: receive messages from frontend
            while True:
                try:
                    message = await websocket.receive()
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected for session {session_id}")
                    break

                if message.get("type") == "websocket.disconnect":
                    break

                # Binary frame: complete audio segment from VAD
                if "bytes" in message and message["bytes"]:
                    audio_pcm = message["bytes"]

                    # Skip very short audio (< 0.5s)
                    if len(audio_pcm) < MIN_AUDIO_BYTES:
                        logger.debug(
                            f"Skipping short audio segment: {len(audio_pcm)} bytes"
                        )
                        continue

                    if is_processing:
                        logger.debug("Ignoring audio while processing")
                        continue

                    is_processing = True

                    # Reset silence monitor
                    if silence_task and not silence_task.done():
                        silence_task.cancel()

                    try:
                        await websocket.send_json({"type": "processing"})

                        # Convert PCM to WAV and transcribe
                        wav_bytes = pcm_to_wav(audio_pcm)
                        asr_result = await self.asr.transcribe(wav_bytes)

                        if not asr_result.transcript.strip():
                            logger.debug("Empty transcript, skipping")
                            continue

                        # Send transcript back so the user can review/edit
                        # before explicitly submitting.
                        await websocket.send_json({
                            "type": "final_transcript",
                            "text": asr_result.transcript,
                            "language": asr_result.language,
                            "confidence": asr_result.confidence,
                        })
                    except openai.APIConnectionError:
                        logger.error(
                            f"Whisper API connection failed for {session_id} after retries",
                            exc_info=True,
                        )
                        await self._send_error(
                            websocket,
                            "Voice transcription is temporarily unavailable. "
                            "Please try again or switch to typing.",
                        )
                    except Exception as e:
                        logger.error(
                            f"Error processing audio for {session_id}: {e}",
                            exc_info=True,
                        )
                        await self._send_error(
                            websocket, f"Processing error: {e}"
                        )
                    finally:
                        is_processing = False
                        # Restart silence monitor
                        silence_task = asyncio.create_task(
                            self._silence_monitor(websocket)
                        )

                # JSON control messages
                elif "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue

                    msg_type = data.get("type", "")

                    if msg_type == "control":
                        action = data.get("action", "")
                        if action in ("switch_to_text", "stop"):
                            logger.info(
                                f"Voice session {action} for {session_id}"
                            )
                            break

                    elif msg_type == "text_answer":
                        text_answer = data.get("text", "").strip()
                        if text_answer and not is_processing:
                            is_processing = True

                            # Reset silence monitor
                            if silence_task and not silence_task.done():
                                silence_task.cancel()

                            try:
                                await websocket.send_json({"type": "processing"})
                                await self._submit_and_respond(
                                    websocket=websocket,
                                    interview_session_id=interview_session_id,
                                    answer_text=text_answer,
                                    raw_transcript=None,
                                    confidence=1.0,
                                    language="EN",
                                    language_tags=[],
                                )
                            except Exception as e:
                                logger.error(
                                    f"Error processing text answer: {e}"
                                )
                                await self._send_error(websocket, str(e))
                            finally:
                                is_processing = False
                                silence_task = asyncio.create_task(
                                    self._silence_monitor(websocket)
                                )

        except Exception as e:
            logger.error(f"Voice session error for {session_id}: {e}")
            await self._send_error(websocket, "Voice session error")
        finally:
            if silence_task and not silence_task.done():
                silence_task.cancel()
            logger.info(f"Voice session ended for {session_id}")

    async def _process_final_transcript(
        self,
        websocket: WebSocket,
        interview_session_id: UUID,
        transcript: str,
        confidence: float,
    ) -> None:
        """Correct transcript, submit answer, and send next question.

        Note: the raw Whisper transcript is already sent to the client
        before this method is called, so the user sees it instantly.
        """
        # Get recent turns for correction context
        recent_turns = await self._get_recent_turns(interview_session_id)

        # Run transcript correction
        corrected = await self.corrector.correct_transcript(
            raw_transcript=transcript,
            confidence=confidence,
            recent_turns=recent_turns,
        )

        # Submit through interview pipeline (corrected text)
        await self._submit_and_respond(
            websocket=websocket,
            interview_session_id=interview_session_id,
            answer_text=corrected.corrected_transcript,
            raw_transcript=transcript,
            confidence=confidence,
            language=corrected.primary_language,
            language_tags=corrected.language_tags,
        )

    async def _submit_and_respond(
        self,
        websocket: WebSocket,
        interview_session_id: UUID,
        answer_text: str,
        raw_transcript: str | None,
        confidence: float,
        language: str,
        language_tags: list[dict],
    ) -> None:
        """Submit answer through interview pipeline and send next question."""
        audio_meta = None
        if raw_transcript is not None:
            audio_meta = {
                "asr_confidence": confidence,
                "raw_transcript": raw_transcript,
                "language_tags": language_tags,
            }

        async with async_session_factory() as db_session:
            try:
                # Get question_id from last interviewer turn
                result = await db_session.execute(
                    select(InterviewTurn)
                    .where(
                        InterviewTurn.session_id == interview_session_id,
                        InterviewTurn.role == "interviewer",
                    )
                    .order_by(InterviewTurn.turn_index.desc())
                    .limit(1)
                )
                last_turn = result.scalar_one_or_none()
                question_id = ""
                if last_turn and last_turn.question_meta:
                    question_id = last_turn.question_meta.get("question_id", "")

                # Submit answer
                request = InterviewAnswerRequest(
                    answer_text=answer_text,
                    question_id=question_id,
                    input_mode="voice" if raw_transcript else "text",
                    audio_meta=audio_meta,
                )

                await self.interview.submit_answer(
                    db_session, interview_session_id, request
                )

                # Get next question
                next_response = await self.interview.get_next_question(
                    db_session, interview_session_id
                )

                await db_session.commit()

                # Build response
                status = next_response.status
                progress = (
                    next_response.module_progress.model_dump()
                    if next_response.module_progress
                    else {}
                )

                msg = {
                    "type": "next_question",
                    "status": status,
                    "question_id": next_response.question_id,
                    "question_text": next_response.question_text,
                    "question_type": next_response.question_type,
                    "module_progress": progress,
                }
                if next_response.module_summary:
                    msg["module_summary"] = next_response.module_summary
                # Rich UI fields for structured question types
                if next_response.options:
                    msg["options"] = [o.model_dump() for o in next_response.options]
                if next_response.max_selections is not None:
                    msg["max_selections"] = next_response.max_selections
                if next_response.scale_min is not None:
                    msg["scale_min"] = next_response.scale_min
                if next_response.scale_max is not None:
                    msg["scale_max"] = next_response.scale_max
                if next_response.scale_labels:
                    msg["scale_labels"] = next_response.scale_labels
                if next_response.matrix_items:
                    msg["matrix_items"] = next_response.matrix_items
                if next_response.matrix_options:
                    msg["matrix_options"] = [o.model_dump() for o in next_response.matrix_options]
                if next_response.placeholder:
                    msg["placeholder"] = next_response.placeholder
                if next_response.concept_card:
                    msg["concept_card"] = next_response.concept_card.model_dump()

                await websocket.send_json(msg)
                logger.info(
                    f"Sent next_question (status={status}) for session {interview_session_id}"
                )

            except Exception:
                await db_session.rollback()
                raise

    async def _validate_session(self, interview_session_id: UUID) -> bool:
        """Validate that the interview session exists and is active."""
        async with async_session_factory() as db_session:
            try:
                result = await db_session.execute(
                    select(InterviewSession).where(
                        InterviewSession.id == interview_session_id,
                        InterviewSession.status.in_(["active", "paused"]),
                    )
                )
                return result.scalar_one_or_none() is not None
            except Exception as e:
                logger.error(f"Error validating session {interview_session_id}: {e}")
                return False

    async def _get_recent_turns(self, interview_session_id: UUID) -> list[dict]:
        """Get recent conversation turns for context."""
        async with async_session_factory() as db_session:
            try:
                result = await db_session.execute(
                    select(InterviewTurn)
                    .where(InterviewTurn.session_id == interview_session_id)
                    .order_by(InterviewTurn.turn_index.desc())
                    .limit(6)
                )
                turns = result.scalars().all()
                return [
                    {
                        "role": t.role,
                        "question": t.question_text if t.role == "interviewer" else None,
                        "answer": t.answer_text if t.role == "user" else None,
                    }
                    for t in reversed(turns)
                ]
            except Exception as e:
                logger.error(f"Error getting recent turns: {e}")
                return []

    async def _silence_monitor(self, websocket: WebSocket) -> None:
        """Monitor for silence and send timeout prompts."""
        try:
            await asyncio.sleep(PAUSE_OFFER_TIMEOUT_S)
            await websocket.send_json({
                "type": "timeout_prompt",
                "message": "Would you like to pause and come back later? You can also switch to typing.",
            })
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _send_error(self, websocket: WebSocket, message: str) -> None:
        """Send error message to client."""
        try:
            await websocket.send_json({"type": "error", "message": message})
        except Exception:
            pass


# Singleton
_voice_orchestrator: VoiceOrchestrator | None = None


def get_voice_orchestrator() -> VoiceOrchestrator:
    """Get the singleton voice orchestrator instance."""
    global _voice_orchestrator
    if _voice_orchestrator is None:
        _voice_orchestrator = VoiceOrchestrator()
    return _voice_orchestrator
