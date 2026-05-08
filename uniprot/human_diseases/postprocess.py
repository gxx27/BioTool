"""Summaries for UniProt human disease stream responses."""

from __future__ import annotations

from typing import Any, Dict, List

EXAMPLE_LIMIT = 5


def _summarize_definition(definition: str, max_words: int = 30) -> str:
    words = definition.split()
    if len(words) <= max_words:
        return definition
    return " ".join(words[:max_words]) + "…"


def _summarize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(entry, dict):
        return {}

    identifier = entry.get("id")
    definition = entry.get("definition")

    if not isinstance(identifier, str) or not isinstance(definition, str):
        return {}

    summary: Dict[str, Any] = {
        "id": identifier,
        "summary": _summarize_definition(definition),
    }

    return summary


def _collect_statistics(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    stats: Dict[str, int] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        definition = entry.get("definition")
        if not isinstance(definition, str):
            continue
        for keyword in ("dominant", "recessive", "epilepsy", "encephalopathy", "developmental", "neurologic"):
            if keyword in definition.lower():
                stats[keyword] = stats.get(keyword, 0) + 1
    return stats


def postprocess_stream_human_diseases(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense stream human diseases response to concise summaries."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "examples": [], "statistics": {}}

    summarized_entries: List[Dict[str, Any]] = []
    for entry in raw_results:
        summary = _summarize_entry(entry)
        if summary:
            summarized_entries.append(summary)

    total_results = len(summarized_entries)
    examples = summarized_entries[:EXAMPLE_LIMIT]
    statistics = _collect_statistics(raw_results)

    summary: Dict[str, Any] = {
        "total_results": total_results,
        "examples": examples,
    }

    if statistics:
        summary["statistics"] = statistics

    return summary

