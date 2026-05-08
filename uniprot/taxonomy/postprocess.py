"""Summaries for UniProt taxonomy search responses."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


EXAMPLE_LIMIT = 3


def _safe_int(value: Any) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _extract_name(entry: Dict[str, Any], *keys: str) -> Optional[str]:
    for key in keys:
        value = entry.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _summarize_lineage(lineage: Any, depth: int = 5) -> List[str]:
    if not isinstance(lineage, list):
        return []

    names: List[str] = []
    for node in lineage:
        if not isinstance(node, dict):
            continue
        name = _extract_name(node, "commonName", "scientificName")
        if name:
            names.append(name)

    return names[-depth:]


def _summarize_statistics(statistics: Any) -> Dict[str, int]:
    if not isinstance(statistics, dict):
        return {}

    summary: Dict[str, int] = {}
    for key, value in statistics.items():
        value_int = _safe_int(value)
        if value_int:
            summary[key] = value_int
    return summary


def _summarize_taxon(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(entry, dict):
        return {}, {}

    summary: Dict[str, Any] = {}
    statistics: Dict[str, Any] = {
        "rank": None,
        "hidden": None,
        "has_common_name": False,
        "lineage_depth": 0,
    }

    scientific_name = entry.get("scientificName")
    if isinstance(scientific_name, str):
        summary["scientificName"] = scientific_name

    common_name = entry.get("commonName")
    if isinstance(common_name, str) and common_name.strip():
        summary["commonName"] = common_name.strip()
        statistics["has_common_name"] = True

    rank = entry.get("rank")
    if isinstance(rank, str):
        summary["rank"] = rank
        statistics["rank"] = rank

    taxon_id = entry.get("taxonId")
    if isinstance(taxon_id, int):
        summary["taxonId"] = taxon_id

    mnemonic = entry.get("mnemonic")
    if isinstance(mnemonic, str) and mnemonic.strip():
        summary["mnemonic"] = mnemonic.strip()

    hidden = entry.get("hidden")
    if isinstance(hidden, bool):
        statistics["hidden"] = hidden
        if hidden:
            summary["hidden"] = hidden

    active = entry.get("active")
    if isinstance(active, bool) and not active:
        summary["active"] = active

    parent = entry.get("parent")
    if isinstance(parent, dict):
        parent_name = _extract_name(parent, "commonName", "scientificName")
        parent_id = parent.get("taxonId")
        if parent_name or isinstance(parent_id, int):
            summary["parent"] = {
                "name": parent_name,
                "taxonId": parent_id if isinstance(parent_id, int) else None,
            }

    other_names = entry.get("otherNames")
    if isinstance(other_names, list) and other_names:
        names = [name for name in other_names if isinstance(name, str)]
        if names:
            summary["otherNames"] = names[:5]

    strains = entry.get("strains")
    if isinstance(strains, list) and strains:
        formatted: List[Dict[str, Any]] = []
        for strain in strains:
            if not isinstance(strain, dict):
                continue
            name = strain.get("name")
            if isinstance(name, str) and name.strip():
                item: Dict[str, Any] = {"name": name.strip()}
                syns = strain.get("synonyms")
                if isinstance(syns, list) and syns:
                    filtered = [s for s in syns if isinstance(s, str) and s.strip()]
                    if filtered:
                        item["synonyms"] = filtered[:2]
                formatted.append(item)
        if formatted:
            summary["strains"] = formatted[:5]

    links = entry.get("links")
    if isinstance(links, list):
        urls = [url for url in links if isinstance(url, str) and url.strip()]
        if urls:
            summary["links"] = urls[:5]

    lineage = _summarize_lineage(entry.get("lineage"))
    if lineage:
        summary["lineage"] = lineage
        statistics["lineage_depth"] = len(lineage)

    stats = _summarize_statistics(entry.get("statistics"))
    if stats:
        summary["statistics"] = stats

    return summary, statistics


def _aggregate_statistics(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not items:
        return {}

    rank_counter: Counter[str] = Counter()
    hidden_counter: Counter[bool] = Counter()
    common_name_count = 0
    lineage_depths: List[int] = []
    protein_counts: List[int] = []

    for stats in items:
        rank = stats.get("rank")
        if isinstance(rank, str):
            rank_counter[rank] += 1

        hidden = stats.get("hidden")
        if isinstance(hidden, bool):
            hidden_counter[hidden] += 1

        if stats.get("has_common_name"):
            common_name_count += 1

        depth = stats.get("lineage_depth")
        if isinstance(depth, int) and depth > 0:
            lineage_depths.append(depth)

    summary: Dict[str, Any] = {}

    if rank_counter:
        summary["rank_distribution"] = dict(rank_counter.most_common(5))

    total_items = len(items)
    if total_items:
        summary["common_name_ratio"] = round(common_name_count / total_items, 2)

    if hidden_counter:
        summary["hidden_flags"] = {str(key): count for key, count in hidden_counter.items()}

    if lineage_depths:
        summary["lineage_depth"] = {
            "average": round(sum(lineage_depths) / len(lineage_depths), 1),
            "min": min(lineage_depths),
            "max": max(lineage_depths),
        }

    return summary


def postprocess_search_taxonomy(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize taxonomy search results with representative examples and statistics."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "summaries": [], "statistics": {}}

    summaries: List[Dict[str, Any]] = []
    stat_records: List[Dict[str, Any]] = []

    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        summary, stats = _summarize_taxon(entry)
        if summary:
            summaries.append(summary)
            stat_records.append(stats)

    total_results = len(summaries)
    examples = summaries[:EXAMPLE_LIMIT]
    aggregates = _aggregate_statistics(stat_records)

    summary: Dict[str, Any] = {
        "total_results": total_results,
        "summaries": examples,
    }

    if aggregates:
        summary["statistics"] = aggregates

    total_reported = response.get("totalResults") or response.get("total")
    if isinstance(total_reported, int):
        summary["total_reported"] = total_reported

    facets = response.get("facets")
    if isinstance(facets, dict) and facets:
        summary["facets"] = list(facets.keys())

    return summary

def postprocess_stream_taxonomy(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize taxonomy stream results with representative examples."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "summaries": []}

    summaries: List[Dict[str, Any]] = []

    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        summary, _ = _summarize_taxon(entry)
        if summary:
            summaries.append(summary)

    total_results = len(summaries)
    examples = summaries[:10]

    summary: Dict[str, Any] = {key: value for key, value in response.items() if key != "results"}
    summary["total_results"] = total_results
    summary["examples"] = examples

    return summary