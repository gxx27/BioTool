"""Summarize UniProt ARBA search responses for compact storage."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple


_MAX_EXAMPLES = 3
_MAX_SAMPLE_CONDITIONS = 5
_MAX_SAMPLE_ANNOTATIONS = 5


def _safe_int(value: Any) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _extract_scope(scope: Any) -> Optional[str]:
    if isinstance(scope, str) and scope.strip():
        return scope.strip()

    if isinstance(scope, dict):
        for key in ("scientificName", "commonName", "value", "label", "name"):
            value = scope.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    if isinstance(scope, list):
        for entry in scope:
            extracted = _extract_scope(entry)
            if extracted:
                return extracted

    return None


def _simplify_information(info: Any) -> Tuple[Dict[str, Any], Optional[str]]:
    if not isinstance(info, dict):
        return {}, None

    simplified: Dict[str, Any] = {}
    scope_value: Optional[str] = None

    for key, value in info.items():
        if value is None:
            continue
        if key == "taxonomicScope":
            scope_value = _extract_scope(value)
            if scope_value:
                simplified["taxonomic_scope"] = scope_value
            continue
        if isinstance(value, (str, int, float, bool)):
            simplified[key] = value
        elif isinstance(value, dict):
            candidate = _extract_scope(value)
            if candidate:
                simplified[key] = candidate
        elif isinstance(value, list):
            if not value:
                continue
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                simplified[key] = value[:5]

    return simplified, scope_value


def _summarize_condition_sets(
    main_rule: Dict[str, Any],
) -> Tuple[Dict[str, Any], Counter[str], Counter[str], int]:
    condition_sets = main_rule.get("conditionSets")
    if not isinstance(condition_sets, list):
        return {}, Counter(), Counter(), 0

    condition_sets = [cs for cs in condition_sets if isinstance(cs, dict)]
    if not condition_sets:
        return {}, Counter(), Counter(), 0

    set_count = len(condition_sets)
    condition_count = 0
    type_counter: Counter[str] = Counter()
    taxon_counter: Counter[str] = Counter()
    samples: List[Dict[str, Any]] = []

    for cond_set in condition_sets:
        conditions = cond_set.get("conditions")
        if not isinstance(conditions, list):
            continue
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            condition_type = condition.get("type")
            if isinstance(condition_type, str):
                type_counter[condition_type] += 1
            values = condition.get("conditionValues") or []
            extracted_values: List[str] = []
            if isinstance(values, list):
                for item in values:
                    if isinstance(item, dict):
                        val = item.get("value")
                        if isinstance(val, str) and val.strip():
                            extracted_values.append(val.strip())
                    elif isinstance(item, str):
                        extracted_values.append(item)

            if condition_type == "taxon":
                for val in extracted_values:
                    taxon_counter[val] += 1

            condition_count += 1

            if len(samples) < _MAX_SAMPLE_CONDITIONS:
                entry: Dict[str, Any] = {
                    "type": condition_type,
                    "values": extracted_values[:3],
                }
                if condition.get("isNegative"):
                    entry["negative"] = True
                samples.append(entry)

    summary: Dict[str, Any] = {
        "set_count": set_count,
        "condition_count": condition_count,
    }

    if type_counter:
        summary["top_types"] = dict(type_counter.most_common(5))
    if samples:
        summary["sample_conditions"] = samples

    return summary, type_counter, taxon_counter, condition_count


def _summarize_annotations(
    main_rule: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Counter[str], Counter[str], int]:
    annotations = main_rule.get("annotations")
    if not isinstance(annotations, list):
        return [], Counter(), Counter(), 0

    sanitized: List[Dict[str, Any]] = []
    type_counter: Counter[str] = Counter()
    database_counter: Counter[str] = Counter()

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        ann_type = annotation.get("annotationType")
        if isinstance(ann_type, str):
            type_counter[ann_type] += 1

        db_reference = annotation.get("dbReference")
        database: Optional[str] = None
        identifier: Optional[str] = None
        properties: List[Dict[str, Any]] = []

        if isinstance(db_reference, dict):
            database = db_reference.get("database") if isinstance(db_reference.get("database"), str) else None
            identifier = db_reference.get("id") if isinstance(db_reference.get("id"), str) else None
            props = db_reference.get("properties")
            if isinstance(props, list):
                for prop in props:
                    if isinstance(prop, dict):
                        key = prop.get("key")
                        value = prop.get("value")
                        if isinstance(key, str) and isinstance(value, str):
                            properties.append({"key": key, "value": value})

        if database:
            database_counter[database] += 1

        entry: Dict[str, Any] = {}
        if ann_type:
            entry["type"] = ann_type
        if database:
            entry["database"] = database
        if identifier:
            entry["id"] = identifier
        if properties:
            entry["properties"] = properties[:3]

        if entry:
            sanitized.append(entry)

        if len(sanitized) >= _MAX_SAMPLE_ANNOTATIONS:
            break

    return sanitized, type_counter, database_counter, len(annotations)


def _summarize_main_rule(
    main_rule: Any,
) -> Tuple[Dict[str, Any], Counter[str], Counter[str], Counter[str], Counter[str], int, int]:
    if not isinstance(main_rule, dict):
        return {}, Counter(), Counter(), Counter(), Counter(), 0, 0

    conditions_summary, condition_type_counter, taxon_counter, condition_count = _summarize_condition_sets(main_rule)
    annotations_summary, annotation_type_counter, annotation_db_counter, annotation_count = _summarize_annotations(main_rule)

    summary: Dict[str, Any] = {}

    if conditions_summary:
        summary["conditions"] = conditions_summary
    if annotations_summary:
        summary["annotations"] = annotations_summary

    return (
        summary,
        condition_type_counter,
        taxon_counter,
        annotation_type_counter,
        annotation_db_counter,
        condition_count,
        annotation_count,
    )


def _summarize_result(result: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(result, dict):
        return {}, {
            "condition_types": Counter(),
            "taxa": Counter(),
            "annotation_types": Counter(),
            "annotation_databases": Counter(),
            "condition_count": 0,
            "annotation_count": 0,
            "taxonomic_scope": None,
        }

    summary: Dict[str, Any] = {}

    uni_rule_id = result.get("uniRuleId")
    if isinstance(uni_rule_id, str):
        summary["uniRuleId"] = uni_rule_id

    info_summary, scope_value = _simplify_information(result.get("information"))
    if info_summary:
        summary["information"] = info_summary

    main_rule_summary, condition_type_counter, taxon_counter, annotation_type_counter, annotation_db_counter, condition_count, annotation_count = _summarize_main_rule(result.get("mainRule"))
    if main_rule_summary:
        summary["mainRule"] = main_rule_summary

    statistics = result.get("statistics")
    if isinstance(statistics, dict):
        numeric_statistics: Dict[str, Any] = {}
        for key, value in statistics.items():
            if isinstance(value, (int, float)):
                numeric_statistics[key] = value
            else:
                numeric = _safe_float(value)
                if numeric is not None:
                    numeric_statistics[key] = numeric
        if numeric_statistics:
            summary["statistics"] = numeric_statistics

    annotation_covered = result.get("annotationCovered") or result.get("annotation_covered")
    if isinstance(annotation_covered, dict):
        covered_summary: Dict[str, Any] = {}
        for key, value in annotation_covered.items():
            if isinstance(value, (int, float)):
                covered_summary[key] = value
        if covered_summary:
            summary["annotationCovered"] = covered_summary

    contributions = {
        "condition_types": condition_type_counter,
        "taxa": taxon_counter,
        "annotation_types": annotation_type_counter,
        "annotation_databases": annotation_db_counter,
        "condition_count": condition_count,
        "annotation_count": annotation_count,
        "taxonomic_scope": scope_value,
    }

    return summary, contributions


def _summarize_results_list(
    raw_results: Any,
    sample_limit: int = _MAX_EXAMPLES,
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
    if not isinstance(raw_results, list):
        return [], 0, {}

    summarized: List[Dict[str, Any]] = []
    condition_type_counter: Counter[str] = Counter()
    taxon_counter: Counter[str] = Counter()
    annotation_type_counter: Counter[str] = Counter()
    annotation_db_counter: Counter[str] = Counter()
    condition_counts: List[int] = []
    annotation_counts: List[int] = []
    scope_counter: Counter[str] = Counter()

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        condensed, contributions = _summarize_result(item)
        if not condensed:
            continue
        summarized.append(condensed)

        condition_type_counter.update(contributions["condition_types"])
        taxon_counter.update(contributions["taxa"])
        annotation_type_counter.update(contributions["annotation_types"])
        annotation_db_counter.update(contributions["annotation_databases"])
        if contributions["condition_count"]:
            condition_counts.append(contributions["condition_count"])
        if contributions["annotation_count"]:
            annotation_counts.append(contributions["annotation_count"])
        if isinstance(contributions["taxonomic_scope"], str):
            scope_counter[contributions["taxonomic_scope"]] += 1

    total_items = len(summarized)
    sampled = summarized[:sample_limit] if sample_limit > 0 else summarized

    summary_stats: Dict[str, Any] = {}

    if condition_type_counter:
        summary_stats["condition_type_counts"] = dict(condition_type_counter.most_common(5))
    if taxon_counter:
        summary_stats["taxon_condition_counts"] = dict(taxon_counter.most_common(5))
    if annotation_type_counter:
        summary_stats["annotation_type_counts"] = dict(annotation_type_counter.most_common(5))
    if annotation_db_counter:
        summary_stats["annotation_database_counts"] = dict(annotation_db_counter.most_common(5))
    if scope_counter:
        summary_stats["taxonomic_scope_counts"] = dict(scope_counter.most_common(5))

    if condition_counts:
        summary_stats["conditions_per_rule"] = {
            "average": round(sum(condition_counts) / len(condition_counts), 1),
            "min": min(condition_counts),
            "max": max(condition_counts),
        }

    if annotation_counts:
        summary_stats["annotations_per_rule"] = {
            "average": round(sum(annotation_counts) / len(annotation_counts), 1),
            "min": min(annotation_counts),
            "max": max(annotation_counts),
        }

    return sampled, total_items, summary_stats


def postprocess_search_arba(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense ARBA search responses into compact, informative summaries."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    examples, total_results, statistics = _summarize_results_list(response.get("results"))

    summary: Dict[str, Any] = {
        "total_results": total_results,
        "summaries": examples,
    }

    if statistics:
        summary["statistics"] = statistics

    total_reported = response.get("totalResults") or response.get("total")
    if isinstance(total_reported, int):
        summary["total_reported"] = total_reported

    facets = response.get("facets")
    if isinstance(facets, dict) and facets:
        summary["facets"] = list(facets.keys())

    return summary


def postprocess_stream_arba(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense ARBA stream responses while retaining auxiliary payload keys."""
    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    examples, total_results, statistics = _summarize_results_list(response.get("results"))

    summary: Dict[str, Any] = {key: value for key, value in response.items() if key != "results"}
    summary["total_results"] = total_results
    summary["summaries"] = examples
    if statistics:
        summary["statistics"] = statistics

    return summary

