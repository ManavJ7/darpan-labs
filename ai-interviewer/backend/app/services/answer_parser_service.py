"""Answer satisfaction service using LLM judgment."""

import logging

from app.llm import LLMClient, get_llm_client
from app.schemas.llm_responses import AnswerSatisfactionResponse
from app.services.prompt_service import PromptService, get_prompt_service

logger = logging.getLogger(__name__)


class AnswerParserService:
    """Judge whether answers are satisfactory using a single LLM call."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_service: PromptService | None = None,
    ):
        self.llm_client = llm_client or get_llm_client()
        self.prompt_service = prompt_service or get_prompt_service()

    async def is_answer_satisfactory(
        self,
        question_text: str,
        answer_text: str,
        target_signal: str = "",
    ) -> tuple[bool, str | None]:
        """LLM judges if answer is satisfactory or needs follow-up.

        Returns (is_satisfactory, reason_if_not).
        Fallback: if LLM fails, treat answer as satisfactory (never block progress).
        """
        if not answer_text or not answer_text.strip():
            return False, "empty answer"

        try:
            prompt = self.prompt_service.get_answer_satisfaction_prompt(
                question_text=question_text,
                answer_text=answer_text,
                target_signal=target_signal,
            )
            response = await self.llm_client.generate(
                prompt=prompt,
                response_format=AnswerSatisfactionResponse,
                temperature=0.3,
                max_tokens=100,
                metadata={"prompt_name": "answer_satisfaction"},
            )
            return response.satisfactory, response.reason
        except Exception as e:
            logger.warning(f"Answer satisfaction LLM failed, treating as satisfactory: {e}")
            return True, None


# Singleton instance
_answer_parser_service: AnswerParserService | None = None


def get_answer_parser_service() -> AnswerParserService:
    """Get the singleton answer parser service instance."""
    global _answer_parser_service
    if _answer_parser_service is None:
        _answer_parser_service = AnswerParserService()
    return _answer_parser_service
