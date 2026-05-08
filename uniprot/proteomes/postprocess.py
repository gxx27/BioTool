from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


def _safe_int(value: Any) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _lineage_trail(taxon_lineage: Any, depth: int = 4) -> Dict[str, Optional[str]]:
    if not isinstance(taxon_lineage, list):
        return {"organism": None, "lineage_path": None}

    names: List[str] = []
    for entry in taxon_lineage:
        if not isinstance(entry, dict):
            continue
        name = entry.get("commonName") or entry.get("scientificName")
        if isinstance(name, str) and name.strip():
            names.append(name.strip())

    if not names:
        return {"organism": None, "lineage_path": None}

    trimmed = names[-depth:]
    return {
        "organism": trimmed[-1] if trimmed else None,
        "lineage_path": " > ".join(trimmed) if len(trimmed) > 1 else trimmed[0],
    }


def _summarize_components(components: Any, *, top_n: int = 3) -> Dict[str, Any]:
    if not isinstance(components, list):
        return {}

    cleaned: List[Dict[str, Any]] = [comp for comp in components if isinstance(comp, dict)]
    if not cleaned:
        return {}

    total_proteins = sum(_safe_int(comp.get("proteinCount")) for comp in cleaned)
    sources = {
        str((comp.get("genomeAnnotation") or {}).get("source"))
        for comp in cleaned
        if (comp.get("genomeAnnotation") or {}).get("source")
    }

    cross_ref_total = 0
    top_components: List[Dict[str, Any]] = []
    for comp in cleaned:
        cross_refs = comp.get("proteomeCrossReferences") or []
        if isinstance(cross_refs, list):
            cross_ref_total += len(cross_refs)
        entry = {
            "name": comp.get("name"),
            "proteins": _safe_int(comp.get("proteinCount")),
        }
        if comp.get("description"):
            entry["description"] = str(comp.get("description"))[:120]
        top_components.append(entry)

    top_components.sort(key=lambda item: item.get("proteins", 0), reverse=True)

    summary: Dict[str, Any] = {
        "component_count": len(cleaned),
        "total_proteins": total_proteins,
        "top_components": top_components[:top_n],
    }

    if sources:
        summary["annotation_sources"] = sorted(sources)

    unplaced = next(
        (
            comp for comp in top_components
            if isinstance(comp.get("name"), str) and comp["name"].lower() == "unplaced"
        ),
        None,
    )
    if unplaced:
        summary["unplaced_proteins"] = unplaced.get("proteins")

    if cross_ref_total:
        summary["cross_references"] = cross_ref_total

    return summary


def _summarize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}

    summary: Dict[str, Any] = {}

    if result.get("id"):
        summary["id"] = result["id"]
    if result.get("proteomeType"):
        summary["type"] = result["proteomeType"]

    lineage_info = _lineage_trail(result.get("taxonLineage"))
    if lineage_info["organism"]:
        summary["organism"] = lineage_info["organism"]
    if lineage_info["lineage_path"]:
        summary["lineage"] = lineage_info["lineage_path"]

    component_summary = _summarize_components(result.get("components"))
    if component_summary:
        summary["components"] = component_summary

    if result.get("statistics") and isinstance(result["statistics"], dict):
        key_stats = {key: result["statistics"].get(key) for key in ("BuscoC", "BuscoS", "BuscoD") if result["statistics"].get(key) is not None}
        if key_stats:
            summary["statistics"] = key_stats

    return summary


def _summarize_results_list(
    raw_results: Any,
    sample_limit: int = 3,
) -> Tuple[List[Dict[str, Any]], int, int, Dict[str, Any]]:
    if not isinstance(raw_results, list):
        return [], 0, 0, {}

    summarized_results: List[Dict[str, Any]] = []
    type_counter: Counter[str] = Counter()
    protein_totals: List[int] = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        condensed = _summarize_result(item)
        if not condensed:
            continue

        summarized_results.append(condensed)

        if isinstance(condensed.get("type"), str):
            type_counter[condensed["type"]] += 1

        components = condensed.get("components")
        if isinstance(components, dict):
            total = components.get("total_proteins")
            if isinstance(total, int):
                protein_totals.append(total)

    sampled_results = summarized_results[:sample_limit] if sample_limit > 0 else summarized_results

    stats: Dict[str, Any] = {}
    if type_counter:
        stats["type_counts"] = dict(type_counter.most_common())

    if protein_totals:
        avg = round(sum(protein_totals) / len(protein_totals), 1)
        stats["proteins_per_proteome"] = {
            "average": avg,
            "min": min(protein_totals),
            "max": max(protein_totals),
        }

    total_items = len(raw_results)
    valid_items = len(summarized_results)
    skipped = total_items - valid_items

    return sampled_results, valid_items, skipped, stats


def postprocess_search_proteomes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Compress search results to compact summaries suitable for training data."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    summarized_results, valid_items, skipped_invalid, stats = _summarize_results_list(
        response.get("results")
    )

    summary: Dict[str, Any] = {
        "result_count": len(summarized_results),
        "results": summarized_results,
        "total_results": valid_items,
    }

    if stats:
        summary["summary_stats"] = stats

    if isinstance(response.get("facets"), dict) and response["facets"]:
        summary["facets"] = list(response["facets"].keys())

    total_results = response.get("totalResults") or response.get("total")
    if isinstance(total_results, int):
        summary["total_reported"] = total_results

    if skipped_invalid:
        summary["skipped_entries"] = skipped_invalid

    return summary

def postprocess_stream_proteomes(response: Dict[str, Any]) -> Dict[str, Any]:
    """Compress stream results while preserving auxiliary response keys."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    summarized_results, valid_items, _, _ = _summarize_results_list(response.get("results"))

    summary: Dict[str, Any] = {
        key: value for key, value in response.items() if key != "results"
    }
    summary["total"] = valid_items
    summary["results"] = summarized_results

    return summary