"""Transcript correction service using LLM."""

import logging
import re

from app.llm import LLMClient, get_llm_client
from app.schemas.llm_responses import CorrectedTranscript
from app.services.prompt_service import PromptService, get_prompt_service

logger = logging.getLogger(__name__)


class TranscriptCorrectorService:
    """Correct ASR transcripts using LLM and heuristic fallback."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_service: PromptService | None = None,
    ):
        self.llm_client = llm_client or get_llm_client()
        self.prompt_service = prompt_service or get_prompt_service()

    async def correct_transcript(
        self,
        raw_transcript: str,
        confidence: float,
        recent_turns: list[dict] | None = None,
    ) -> CorrectedTranscript:
        """Correct an ASR transcript using LLM.

        Args:
            raw_transcript: Raw transcript from ASR.
            confidence: ASR confidence score (0-1).
            recent_turns: Recent conversation turns for context.

        Returns:
            CorrectedTranscript with corrections and language tags.
        """
        if not raw_transcript or not raw_transcript.strip():
            return CorrectedTranscript(
                corrected_transcript="",
                primary_language="EN",
                correction_applied=False,
            )

        # High-confidence transcripts with simple English likely need no correction
        if confidence > 0.95 and self._is_simple_english(raw_transcript):
            return CorrectedTranscript(
                corrected_transcript=raw_transcript,
                primary_language="EN",
                correction_applied=False,
            )

        recent_turns = recent_turns or []
        recent_context = self._format_recent_context(recent_turns)

        try:
            prompt = self.prompt_service.format_prompt(
                "transcript_correction",
                raw_transcript=raw_transcript,
                confidence_score=confidence,
                recent_context=recent_context,
            )

            result = await self.llm_client.generate_with_schema(
                prompt=prompt,
                response_schema=CorrectedTranscript,
                temperature=0.2,
            )
            return result

        except Exception as e:
            logger.warning(f"LLM transcript correction failed, using heuristic: {e}")
            return self._heuristic_fallback(raw_transcript)

    def _is_simple_english(self, text: str) -> bool:
        """Check if text is simple English (no Devanagari chars)."""
        hindi_chars = len(re.findall(r"[\u0900-\u097F]", text))
        return hindi_chars == 0

    def _heuristic_fallback(self, raw_transcript: str) -> CorrectedTranscript:
        """Fallback: return raw transcript with detected language."""
        language = self._detect_language(raw_transcript)
        return CorrectedTranscript(
            corrected_transcript=raw_transcript,
            primary_language=language,
            correction_applied=False,
        )

    def _detect_language(self, text: str) -> str:
        """Detect language using Devanagari character ratio.

        Same heuristic as answer_parser_service.py.
        """
        if not text:
            return "EN"

        hindi_chars = len(re.findall(r"[\u0900-\u097F]", text))
        total_chars = len(re.sub(r"\s", "", text))

        if total_chars == 0:
            return "EN"

        hindi_ratio = hindi_chars / total_chars

        if hindi_ratio > 0.5:
            return "HI"
        elif hindi_ratio > 0.1:
            return "HG"
        else:
            return "EN"

    def _format_recent_context(self, turns: list[dict], max_turns: int = 3) -> str:
        """Format recent turns for context."""
        if not turns:
            return "No previous turns."

        recent = turns[-max_turns:] if len(turns) > max_turns else turns
        lines = []
        for turn in recent:
            role = turn.get("role", "")
            content = turn.get("question") or turn.get("answer", "")
            lines.append(f"[{role}]: {content}")
        return "\n".join(lines)


# Singleton
_transcript_corrector: TranscriptCorrectorService | None = None


def get_transcript_corrector() -> TranscriptCorrectorService:
    """Get the singleton transcript corrector service instance."""
    global _transcript_corrector
    if _transcript_corrector is None:
        _transcript_corrector = TranscriptCorrectorService()
    return _transcript_corrector
