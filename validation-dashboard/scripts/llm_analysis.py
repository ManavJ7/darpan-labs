"""Claude API theme extraction from open-ended responses."""

import json
import os
import hashlib
from pathlib import Path
from data_processing import CONCEPT_SHORT

CACHE_DIR = Path(__file__).parent / ".llm_cache"


def get_open_ended_responses(respondents: list) -> dict:
    """Collect open-ended responses per concept for appealing and change metrics."""
    results = {}
    for ci, name in enumerate(CONCEPT_SHORT):
        appealing = []
        change = []
        for r in respondents:
            app = r["concepts"][ci].get("appealing", "")
            chg = r["concepts"][ci].get("change", "")
            if app and len(app) > 3:
                appealing.append({"id": r["id"], "text": app})
            if chg and len(chg) > 3:
                change.append({"id": r["id"], "text": chg})
        results[name] = {"appealing": appealing, "change": change}
    return results


def extract_themes_with_claude(responses: dict, source_label: str) -> dict:
    """Use Claude API to extract themes from open-ended responses."""
    try:
        import anthropic
    except ImportError:
        print("  anthropic package not installed, using fallback theme extraction")
        return extract_themes_fallback(responses)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ANTHROPIC_API_KEY not set, using fallback theme extraction")
        return extract_themes_fallback(responses)

    client = anthropic.Anthropic()
    themes = {}

    for concept_name, data in responses.items():
        themes[concept_name] = {}

        for metric_type in ["appealing", "change"]:
            texts = data.get(metric_type, [])
            if not texts:
                themes[concept_name][metric_type] = []
                continue

            # Check cache
            cache_key = _cache_key(concept_name, metric_type, source_label, texts)
            cached = _load_cache(cache_key)
            if cached is not None:
                print(f"    Using cached themes for {concept_name} - {metric_type}")
                themes[concept_name][metric_type] = cached
                continue

            # Build prompt
            response_list = "\n".join([f"- [{t['id']}] {t['text']}" for t in texts])
            label = "most appealing aspects" if metric_type == "appealing" else "suggested changes/improvements"

            prompt = f"""Analyze these {source_label} responses about {label} for the "{concept_name}" concept.

Responses:
{response_list}

Extract the top themes (max 5). For each theme provide:
1. theme_name: Short descriptive name (2-4 words)
2. frequency: Number of responses mentioning this theme
3. sentiment: "positive", "negative", or "neutral"
4. representative_quote: One verbatim quote that best represents this theme

Return as JSON array:
[{{"theme_name": "...", "frequency": N, "sentiment": "...", "representative_quote": "..."}}]

Return ONLY the JSON array, no other text."""

            try:
                message = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                result_text = message.content[0].text.strip()
                # Parse JSON from response
                if result_text.startswith("```"):
                    result_text = result_text.split("```")[1]
                    if result_text.startswith("json"):
                        result_text = result_text[4:]
                parsed = json.loads(result_text)
                themes[concept_name][metric_type] = parsed
                _save_cache(cache_key, parsed)
                print(f"    Extracted {len(parsed)} themes for {concept_name} - {metric_type}")
            except Exception as e:
                print(f"    Error extracting themes for {concept_name} - {metric_type}: {e}")
                themes[concept_name][metric_type] = []

    return themes


def extract_themes_fallback(responses: dict) -> dict:
    """Simple keyword-based theme extraction when Claude API is unavailable."""
    themes = {}
    for concept_name, data in responses.items():
        themes[concept_name] = {}
        for metric_type in ["appealing", "change"]:
            texts = data.get(metric_type, [])
            if not texts:
                themes[concept_name][metric_type] = []
                continue

            # Simple word frequency analysis
            word_counts = {}
            for t in texts:
                words = t["text"].lower().split()
                seen_in_doc = set()
                for w in words:
                    w_clean = w.strip(".,!?;:'\"()[]")
                    if len(w_clean) > 3 and w_clean not in {"that", "this", "with", "have", "from", "would", "could", "should", "about", "very", "more", "like", "just", "also", "been", "some", "they", "them", "their", "what", "when", "which", "will", "good", "concept", "dove"}:
                        if w_clean not in seen_in_doc:
                            word_counts[w_clean] = word_counts.get(w_clean, 0) + 1
                            seen_in_doc.add(w_clean)

            sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            theme_list = []
            for word, count in sorted_words:
                if count >= 2:
                    # Find a representative quote containing this word
                    quote = next((t["text"] for t in texts if word in t["text"].lower()), texts[0]["text"])
                    theme_list.append({
                        "theme_name": word.title(),
                        "frequency": count,
                        "sentiment": "positive" if metric_type == "appealing" else "neutral",
                        "representative_quote": quote[:200],
                    })

            themes[concept_name][metric_type] = theme_list

    return themes


def _cache_key(concept: str, metric: str, source: str, texts: list) -> str:
    content = json.dumps({"concept": concept, "metric": metric, "source": source, "texts": [t["text"] for t in texts]}, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


def _load_cache(key: str):
    cache_file = CACHE_DIR / f"{key}.json"
    if cache_file.exists():
        with open(cache_file) as f:
            return json.load(f)
    return None


def _save_cache(key: str, data):
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / f"{key}.json"
    with open(cache_file, "w") as f:
        json.dump(data, f)
