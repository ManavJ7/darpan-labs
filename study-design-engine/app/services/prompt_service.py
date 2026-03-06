import os
from functools import lru_cache
from pathlib import Path


class PromptService:
    """Loads and formats prompt templates from the prompts/ directory."""

    def __init__(self, prompts_dir: str | None = None):
        self.prompts_dir = Path(prompts_dir) if prompts_dir else Path(__file__).parent.parent.parent / "prompts"
        self._cache: dict[str, str] = {}

    def load_template(self, template_name: str) -> str:
        """Load a prompt template file by name (without .txt extension)."""
        if template_name in self._cache:
            return self._cache[template_name]

        file_path = self.prompts_dir / f"{template_name}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt template not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        self._cache[template_name] = content
        return content

    def format_prompt(self, template_name: str, **kwargs: str) -> str:
        """Load a template and format it with the given keyword arguments."""
        template = self.load_template(template_name)
        return template.format(**kwargs)

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()


_prompt_service: PromptService | None = None


def get_prompt_service() -> PromptService:
    """Dependency function to get PromptService singleton."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
