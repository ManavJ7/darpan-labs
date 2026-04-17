"""Service for generating AI-summarized qualitative insights from twin simulation responses."""

import asyncio
import hashlib
import json
import logging
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.client import LLMClient, get_llm_client
from app.models.study import Study, StepVersion
from app.models.twin import TwinSimulationRun
from app.schemas.qualitative_insights import (
    ConceptInsight,
    QualitativeInsightsResponse,
    ThemeItem,
)
from app.services.prompt_service import PromptService, get_prompt_service

logger = logging.getLogger(__name__)

# ─── Question classification patterns ──────────────────

_APPEALING_PATTERNS = [
    re.compile(r"most appealing", re.I),
    re.compile(r"like most", re.I),
    re.compile(r"appeals? to you", re.I),
    re.compile(r"positive aspects?", re.I),
]

_IMPROVE_PATTERNS = [
    re.compile(r"change|improve|different", re.I),
    re.compile(r"concerns?", re.I),
    re.compile(r"least appealing", re.I),
    re.compile(r"dislike", re.I),
]

# Stopwords for fallback extraction
_STOPWORDS = frozenset(
    "i me my we our you your he she it they them the a an and or but is are was were "
    "be been being have has had do does did will would shall should can could may might "
    "to of in for on at by from with about into through during before after above below "
    "between out off over under again further then once here there when where why how "
    "all each every both few more most other some such no nor not only own same so than "
    "too very just also back even still well much really".split()
)


def _classify_question(question_text: str) -> str | None:
    """Classify an open-text question as 'appealing' or 'improve'."""
    for pat in _APPEALING_PATTERNS:
        if pat.search(question_text):
            return "appealing"
    for pat in _IMPROVE_PATTERNS:
        if pat.search(question_text):
            return "improve"
    return None


def _extract_concept_index(section_id: str) -> int | None:
    """Extract concept index from section_id like 'S2_concept_1'."""
    m = re.search(r"concept[_-](\d+)", section_id, re.I)
    return int(m.group(1)) if m else None


def _compute_hash(texts: list[str]) -> str:
    """MD5 hash of sorted response texts for cache invalidation."""
    content = "\n".join(sorted(texts))
    return hashlib.md5(content.encode()).hexdigest()


def _fallback_themes(texts: list[str], n: int = 5) -> list[ThemeItem]:
    """Basic keyword frequency extraction when LLM is unavailable."""
    word_counts: Counter[str] = Counter()
    for text in texts:
        words = re.findall(r"\b[a-z]{4,}\b", text.lower())
        word_counts.update(w for w in words if w not in _STOPWORDS)

    total = len(texts)
    themes = []
    for word, count in word_counts.most_common(n):
        if count < 2:
            break
        themes.append(ThemeItem(
            theme_name=word.capitalize(),
            frequency=count,
            frequency_pct=round(count / total * 100, 1) if total else 0,
            sentiment="neutral",
            representative_quote=next(
                (t for t in texts if word in t.lower()), texts[0] if texts else ""
            ),
        ))
    return themes


class QualitativeInsightsService:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        prompt_service: PromptService | None = None,
    ):
        self.llm = llm_client or get_llm_client()
        self.prompts = prompt_service or get_prompt_service()

    async def get_or_generate_insights(
        self,
        study_id: str,
        db: AsyncSession,
        force_refresh: bool = False,
    ) -> QualitativeInsightsResponse:
        # Load study
        result = await db.execute(select(Study).where(Study.id == study_id))
        study = result.scalar_one_or_none()
        if not study:
            raise ValueError(f"Study {study_id} not found")

        # Load completed simulation runs
        sim_result = await db.execute(
            select(TwinSimulationRun).where(
                and_(
                    TwinSimulationRun.study_id == study_id,
                    TwinSimulationRun.status == "completed",
                )
            )
        )
        sim_runs = sim_result.scalars().all()
        if not sim_runs:
            return QualitativeInsightsResponse(
                study_id=str(study_id),
                insights=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
                cached=False,
            )

        # Load locked questionnaire for question mapping
        q_result = await db.execute(
            select(StepVersion).where(
                StepVersion.study_id == study_id,
                StepVersion.step == 4,
                StepVersion.status == "locked",
            ).order_by(StepVersion.version.desc()).limit(1)
        )
        q_version = q_result.scalar_one_or_none()

        # Build question_id → (concept_index, question_type, question_text) mapping
        q_map: dict[str, tuple[int, str, str]] = {}
        if q_version and q_version.content:
            for section in q_version.content.get("sections", []):
                cidx = _extract_concept_index(section.get("section_id", ""))
                if cidx is None:
                    continue
                for q in section.get("questions", []):
                    qtype_raw = q.get("question_type", "")
                    if qtype_raw not in ("open_text", "open_end", "open_ended", "text"):
                        continue
                    q_text_dict = q.get("question_text", {})
                    q_text = (
                        q_text_dict.get("en", "")
                        if isinstance(q_text_dict, dict)
                        else str(q_text_dict)
                    )
                    classification = _classify_question(q_text)
                    if classification:
                        q_map[q["question_id"]] = (cidx, classification, q_text)

        # Collect responses grouped by (concept_index, question_type)
        ResponseGroup = tuple[int, str]  # (concept_index, question_type)
        groups: dict[ResponseGroup, dict] = defaultdict(
            lambda: {"texts": [], "question_text": ""}
        )
        all_texts: list[str] = []

        for run in sim_runs:
            if not run.responses:
                continue
            for resp in run.responses:
                if resp.get("skipped"):
                    continue
                qid = resp.get("question_id")
                if qid not in q_map:
                    continue
                cidx, qtype, qtext = q_map[qid]
                answer = resp.get("structured_answer")
                if not answer or not isinstance(answer, str):
                    continue
                key: ResponseGroup = (cidx, qtype)
                groups[key]["texts"].append(answer)
                groups[key]["question_text"] = qtext
                all_texts.append(answer)

        if not all_texts:
            return QualitativeInsightsResponse(
                study_id=str(study_id),
                insights=[],
                generated_at=datetime.now(timezone.utc).isoformat(),
                cached=False,
            )

        # Check cache
        response_hash = _compute_hash(all_texts)
        metadata = study.study_metadata or {}
        cached_data = metadata.get("qualitative_insights")

        if not force_refresh and cached_data and cached_data.get("response_hash") == response_hash:
            return QualitativeInsightsResponse(
                study_id=str(study_id),
                insights=[ConceptInsight(**ci) for ci in cached_data["insights"]],
                generated_at=cached_data.get("generated_at", ""),
                cached=True,
            )

        # Get concept names
        concept_names = self._get_concept_names(sim_runs)

        # Generate insights via LLM (parallelize all calls)
        tasks = []
        task_keys: list[ResponseGroup] = []
        for (cidx, qtype), group_data in sorted(groups.items()):
            tasks.append(
                self._generate_single_insight(
                    concept_name=concept_names.get(cidx, f"Concept {cidx}"),
                    brand_name=study.brand_name or "",
                    category=study.category or "",
                    question_type=qtype,
                    question_text=group_data["question_text"],
                    texts=group_data["texts"],
                )
            )
            task_keys.append((cidx, qtype))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assemble insights
        insights: list[ConceptInsight] = []
        for (cidx, qtype), result in zip(task_keys, results):
            group_data = groups[(cidx, qtype)]
            texts = group_data["texts"]
            cname = concept_names.get(cidx, f"Concept {cidx}")

            if isinstance(result, Exception):
                logger.warning("LLM failed for concept %s/%s: %s", cname, qtype, result)
                # Fallback
                insights.append(ConceptInsight(
                    concept_index=cidx,
                    concept_name=cname,
                    question_type=qtype,
                    question_text=group_data["question_text"],
                    summary="AI analysis unavailable. Showing keyword-based themes.",
                    themes=_fallback_themes(texts),
                    representative_quotes=texts[:2],
                    response_count=len(texts),
                ))
            else:
                insights.append(ConceptInsight(
                    concept_index=cidx,
                    concept_name=cname,
                    question_type=qtype,
                    question_text=group_data["question_text"],
                    summary=result.get("summary", ""),
                    themes=[ThemeItem(**t) for t in result.get("themes", [])[:5]],
                    representative_quotes=result.get("representative_quotes", [])[:2],
                    response_count=len(texts),
                ))

        # Sort: by concept_index, then appealing before improve
        type_order = {"appealing": 0, "improve": 1}
        insights.sort(key=lambda i: (i.concept_index, type_order.get(i.question_type, 2)))

        generated_at = datetime.now(timezone.utc).isoformat()

        # Store in cache
        cache_payload = {
            "response_hash": response_hash,
            "insights": [ci.model_dump() for ci in insights],
            "generated_at": generated_at,
        }
        metadata["qualitative_insights"] = cache_payload
        study.study_metadata = metadata
        await db.commit()

        return QualitativeInsightsResponse(
            study_id=str(study_id),
            insights=insights,
            generated_at=generated_at,
            cached=False,
        )

    async def _generate_single_insight(
        self,
        concept_name: str,
        brand_name: str,
        category: str,
        question_type: str,
        question_text: str,
        texts: list[str],
    ) -> dict:
        """Generate insight for one (concept, question_type) pair via LLM."""
        responses_text = "\n".join(f"- {t}" for t in texts)

        prompt = self.prompts.format_prompt(
            "qualitative_insights",
            concept_name=concept_name,
            brand_name=brand_name,
            category=category,
            question_type="What respondents found most appealing" if question_type == "appealing" else "What respondents would change or improve",
            question_text=question_text,
            response_count=str(len(texts)),
            responses_text=responses_text,
        )

        return await self.llm.generate_json(prompt, max_tokens=2000)

    @staticmethod
    def _get_concept_names(sim_runs: list[TwinSimulationRun]) -> dict[int, str]:
        """Extract concept names from questionnaire_snapshot in simulation runs."""
        names: dict[int, str] = {}
        for run in sim_runs:
            snapshot = run.questionnaire_snapshot or {}
            for c in snapshot.get("concepts", []):
                idx = c.get("concept_index")
                pname = c.get("product_name", "")
                if idx is not None and pname and idx not in names:
                    names[idx] = pname
            if names:
                break
        return names
