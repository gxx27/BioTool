"""Summaries for UniRule search responses."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXAMPLE_LIMIT = 2
SAMPLE_CONDITIONS = 2
SAMPLE_ANNOTATIONS = 2
SAMPLE_FEATURES = 2


def _safe_int(value: Any) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _first(values: Iterable[Any]) -> Optional[Any]:
    for item in values:
        if item:
            return item
    return None


def _trim_list(items: Optional[Iterable[Any]], limit: int) -> Optional[List[Any]]:
    if not items:
        return None
    trimmed: List[Any] = []
    for item in items:
        if item is None:
            continue
        trimmed.append(item)
        if len(trimmed) >= limit:
            break
    return trimmed or None


def _summarize_information(info: Any) -> Tuple[Dict[str, Any], Dict[str, Counter[str]]]:
    if not isinstance(info, dict):
        return {}, {"data_classes": Counter()}

    summary: Dict[str, Any] = {}
    data_class = info.get("dataClass")
    if isinstance(data_class, str) and data_class.strip():
        summary["dataClass"] = data_class.strip()

    version = info.get("version")
    if isinstance(version, str) and version.strip():
        summary["version"] = version.strip()

    old_rule = info.get("oldRuleNum")
    if isinstance(old_rule, str) and old_rule.strip():
        summary["legacyId"] = old_rule.strip()

    names = info.get("names")
    if isinstance(names, list):
        first_name = next((name for name in names if isinstance(name, str) and name.strip()), None)
        if first_name:
            summary["name"] = first_name.strip()

    uni_prot_ids = info.get("uniProtIds")
    if isinstance(uni_prot_ids, list) and uni_prot_ids:
        count = len([item for item in uni_prot_ids if isinstance(item, str) and item.strip()])
        if count:
            summary["uniprotIdCount"] = count

    accessions = info.get("uniProtAccessions")
    if isinstance(accessions, list) and accessions:
        first_acc = next((item for item in accessions if isinstance(item, str) and item.strip()), None)
        if first_acc:
            summary["representativeAccession"] = first_acc.strip()

    related = info.get("related")
    if isinstance(related, list) and related:
        first_related = next((item for item in related if isinstance(item, str) and item.strip()), None)
        if first_related:
            summary["relatedRule"] = first_related.strip()

    contributions = {"data_classes": Counter()}
    if isinstance(data_class, str) and data_class.strip():
        contributions["data_classes"].update([data_class.strip()])

    return summary, contributions


def _extract_condition_values(condition_values: Any) -> List[str]:
    results: List[str] = []
    if isinstance(condition_values, list):
        for value in condition_values:
            if isinstance(value, dict):
                val = value.get("value")
                if isinstance(val, str) and val.strip():
                    results.append(val.strip())
            elif isinstance(value, str) and value.strip():
                results.append(value.strip())
    return results


def _summarize_condition_sets(main_rule: Any) -> Tuple[Dict[str, Any], Counter[str], Counter[str]]:
    if not isinstance(main_rule, dict):
        return {}, Counter(), Counter()

    condition_sets = main_rule.get("conditionSets")
    if not isinstance(condition_sets, list):
        return {}, Counter(), Counter()

    condition_type_counter: Counter[str] = Counter()
    taxon_counter: Counter[str] = Counter()
    has_negative = False

    for cond_set in condition_sets:
        if not isinstance(cond_set, dict):
            continue
        conditions = cond_set.get("conditions")
        if not isinstance(conditions, list):
            continue
        for condition in conditions:
            if not isinstance(condition, dict):
                continue
            cond_type = condition.get("type")
            cond_type_str = cond_type.strip() if isinstance(cond_type, str) else None
            if cond_type_str:
                condition_type_counter[cond_type_str] += 1
            if condition.get("isNegative") is True:
                has_negative = True
            if cond_type_str == "taxon":
                taxon_counter.update(_extract_condition_values(condition.get("conditionValues")))

    top_types = [ctype for ctype, _ in condition_type_counter.most_common(SAMPLE_CONDITIONS)]
    top_taxa = [taxon for taxon, _ in taxon_counter.most_common(SAMPLE_CONDITIONS)]

    summary: Dict[str, Any] = {}
    if top_types:
        summary["conditionTypes"] = top_types
    if top_taxa:
        summary["representativeTaxa"] = top_taxa
    if has_negative:
        summary["hasNegativeConditions"] = True

    summary["conditionCount"] = sum(condition_type_counter.values())

    return summary, condition_type_counter, taxon_counter


def _summarize_protein_description(description: Dict[str, Any]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    if not isinstance(description, dict):
        return summary

    recommended = description.get("recommendedName", {})
    if isinstance(recommended, dict):
        full = recommended.get("fullName", {})
        if isinstance(full, dict):
            value = full.get("value")
            if isinstance(value, str) and value.strip():
                summary["recommended"] = value.strip()
        ec_numbers = recommended.get("ecNumbers")
        if isinstance(ec_numbers, list):
            numbers = _trim_list(
                (item.get("value") for item in ec_numbers if isinstance(item, dict)),
                3,
            )
            if numbers:
                summary["ec"] = numbers

    alt_names = description.get("alternativeNames")
    if isinstance(alt_names, list):
        entries: List[Dict[str, Any]] = []
        for alt in alt_names:
            if not isinstance(alt, dict):
                continue
            entry: Dict[str, Any] = {}
            full = alt.get("fullName")
            if isinstance(full, dict) and isinstance(full.get("value"), str):
                entry["name"] = full["value"].strip()
            short_names = alt.get("shortNames")
            if isinstance(short_names, list):
                trimmed = _trim_list(
                    (item.get("value") for item in short_names if isinstance(item, dict)),
                    2,
                )
                if trimmed:
                    entry["short"] = trimmed
            if entry:
                entries.append(entry)
            if len(entries) >= 2:
                break
        if entries:
            summary["alternatives"] = entries

    return summary


def _summarize_comment(comment: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(comment, dict):
        return {}

    summary: Dict[str, Any] = {}
    comment_type = comment.get("commentType")
    if isinstance(comment_type, str):
        summary["type"] = comment_type

    texts = comment.get("texts")
    if isinstance(texts, list):
        text_values = _trim_list(
            (item.get("value") for item in texts if isinstance(item, dict) and isinstance(item.get("value"), str)),
            1,
        )
        if text_values:
            summary["text"] = text_values[0]

    if isinstance(comment.get("reaction"), dict):
        reaction = comment["reaction"]
        reaction_name = reaction.get("name")
        if isinstance(reaction_name, str) and reaction_name.strip():
            summary["reaction"] = reaction_name.strip()
        ec_number = reaction.get("ecNumber")
        if isinstance(ec_number, str) and ec_number.strip():
            summary["ec"] = ec_number.strip()

    cofactors = comment.get("cofactors")
    if isinstance(cofactors, list):
        names = _trim_list(
            (
                item.get("name")
                for item in cofactors
                if isinstance(item, dict) and isinstance(item.get("name"), str)
            ),
            2,
        )
        if names:
            summary["cofactors"] = names

    subcellular = comment.get("subcellularLocations")
    if isinstance(subcellular, list):
        location = _trim_list(
            (
                loc.get("location", {}).get("value")
                for loc in subcellular
                if isinstance(loc, dict)
                and isinstance(loc.get("location"), dict)
                and isinstance(loc["location"].get("value"), str)
            ),
            1,
        )
        if location:
            summary["location"] = location[0]

    if not summary.get("text") and comment.get("note") and isinstance(comment["note"], dict):
        note_texts = comment["note"].get("texts")
        if isinstance(note_texts, list):
            note_value = _trim_list(
                (item.get("value") for item in note_texts if isinstance(item, dict) and isinstance(item.get("value"), str)),
                1,
            )
            if note_value:
                summary["note"] = note_value[0]

    return summary


def _summarize_annotations(main_rule: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Counter[str]]]:
    if not isinstance(main_rule, dict):
        return [], {
            "annotation_types": Counter(),
            "comment_types": Counter(),
            "keyword_names": Counter(),
            "gene_names": Counter(),
        }

    annotations = main_rule.get("annotations")
    if not isinstance(annotations, list):
        return [], {
            "annotation_types": Counter(),
            "comment_types": Counter(),
            "keyword_names": Counter(),
            "gene_names": Counter(),
        }

    entries: List[Dict[str, Any]] = []
    annotation_type_counter: Counter[str] = Counter()
    comment_type_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    gene_counter: Counter[str] = Counter()

    for annotation in annotations:
        if not isinstance(annotation, dict):
            continue
        ann_type = annotation.get("annotationType")
        ann_type_str = ann_type.strip() if isinstance(ann_type, str) else None
        if ann_type_str:
            annotation_type_counter[ann_type_str] += 1

        entry: Dict[str, Any] = {}
        if ann_type_str:
            entry["type"] = ann_type_str

        if annotation.get("proteinDescription") and len(entries) < SAMPLE_ANNOTATIONS:
            description = _summarize_protein_description(annotation["proteinDescription"])
            if description:
                entry["proteinDescription"] = description

        if annotation.get("comment") and len(entries) < SAMPLE_ANNOTATIONS:
            comment_summary = _summarize_comment(annotation["comment"])
            if comment_summary:
                entry["comment"] = comment_summary
                comment_type = comment_summary.get("type")
                if isinstance(comment_type, str):
                    comment_type_counter[comment_type] += 1

        if annotation.get("keyword") and len(entries) < SAMPLE_ANNOTATIONS:
            keyword = annotation["keyword"]
            if isinstance(keyword, dict):
                name = keyword.get("name")
                if isinstance(name, str) and name.strip():
                    keyword_counter[name.strip()] += 1
                    entry.setdefault("keywords", []).append(name.strip())

        if annotation.get("gene") and len(entries) < SAMPLE_ANNOTATIONS:
            gene = annotation["gene"]
            if isinstance(gene, dict):
                gene_name = gene.get("geneName")
                if isinstance(gene_name, dict):
                    value = gene_name.get("value")
                    if isinstance(value, str) and value.strip():
                        gene_counter[value.strip()] += 1
                        entry["gene"] = value.strip()

        if annotation.get("dbReference") and len(entries) < SAMPLE_ANNOTATIONS:
            db_ref = annotation["dbReference"]
            if isinstance(db_ref, dict):
                database = db_ref.get("database")
                identifier = db_ref.get("id")
                if isinstance(database, str) and database.strip():
                    entry.setdefault("dbRefs", []).append(database.strip())
                if isinstance(identifier, str) and identifier.strip():
                    entry.setdefault("dbIds", []).append(identifier.strip())

        if entry and len(entries) < SAMPLE_ANNOTATIONS:
            entries.append(entry)
        if len(entries) >= SAMPLE_ANNOTATIONS:
            break

    contributions = {
        "annotation_types": annotation_type_counter,
        "comment_types": comment_type_counter,
        "keyword_names": keyword_counter,
        "gene_names": gene_counter,
    }

    return entries, contributions


def _summarize_position_features(position_sets: Any) -> Tuple[Dict[str, Any], Counter[str]]:
    if not isinstance(position_sets, list):
        return {}, Counter()

    feature_samples: List[Dict[str, Any]] = []
    feature_type_counter: Counter[str] = Counter()

    for feature_set in position_sets:
        if not isinstance(feature_set, dict):
            continue
        features = feature_set.get("positionalFeatures")
        if not isinstance(features, list):
            continue
        for feature in features:
            if not isinstance(feature, dict):
                continue
            feature_type = feature.get("type")
            feature_type_str = feature_type.strip() if isinstance(feature_type, str) else None
            if feature_type_str:
                feature_type_counter[feature_type_str] += 1

            if len(feature_samples) >= SAMPLE_FEATURES:
                continue

            position = feature.get("position", {})
            start = position.get("start", {}) if isinstance(position, dict) else {}
            sample: Dict[str, Any] = {}
            if feature_type_str:
                sample["type"] = feature_type_str

            start_value = start.get("value") if isinstance(start, dict) else None
            if isinstance(start_value, (int, float)):
                sample["pos"] = start_value

            if feature.get("description") and isinstance(feature["description"], str):
                sample["description"] = feature["description"].strip()

            ligand = feature.get("ligand")
            if isinstance(ligand, dict):
                ligand_name = ligand.get("name")
                if isinstance(ligand_name, str) and ligand_name.strip():
                    sample["ligand"] = ligand_name.strip()

            if sample:
                feature_samples.append(sample)

    summary: Dict[str, Any] = {}
    if feature_samples:
        summary["samples"] = feature_samples[:SAMPLE_FEATURES]
    if feature_type_counter:
        summary["topTypes"] = [ftype for ftype, _ in feature_type_counter.most_common(3)]

    return summary, feature_type_counter


def _summarize_statistics(stats: Any) -> Tuple[Dict[str, Any], Dict[str, List[int]]]:
    if not isinstance(stats, dict):
        return {}, {"reviewed_counts": [], "unreviewed_counts": []}

    reviewed = _safe_int(stats.get("reviewedProteinCount"))
    unreviewed = _safe_int(stats.get("unreviewedProteinCount"))
    summary = {}
    if reviewed:
        summary["reviewedProteinCount"] = reviewed
    if unreviewed:
        summary["unreviewedProteinCount"] = unreviewed

    contributions = {
        "reviewed_counts": [reviewed] if reviewed else [],
        "unreviewed_counts": [unreviewed] if unreviewed else [],
    }

    return summary, contributions


def _summarize_result(result: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(result, dict):
        return {}, {
            "data_classes": Counter(),
            "condition_types": Counter(),
            "taxa": Counter(),
            "annotation_types": Counter(),
            "comment_types": Counter(),
            "keywords": Counter(),
            "gene_names": Counter(),
            "feature_types": Counter(),
            "reviewed_counts": [],
            "unreviewed_counts": [],
        }

    contributions = {
        "data_classes": Counter(),
        "condition_types": Counter(),
        "taxa": Counter(),
        "annotation_types": Counter(),
        "comment_types": Counter(),
        "keywords": Counter(),
        "gene_names": Counter(),
        "feature_types": Counter(),
        "reviewed_counts": [],
        "unreviewed_counts": [],
    }

    summary: Dict[str, Any] = {}

    uni_rule_id = result.get("uniRuleId")
    if isinstance(uni_rule_id, str) and uni_rule_id.strip():
        summary["uniRuleId"] = uni_rule_id.strip()

    info_summary, info_contrib = _summarize_information(result.get("information"))
    if info_summary:
        summary["information"] = info_summary
    contributions["data_classes"].update(info_contrib.get("data_classes", Counter()))

    condition_summary, condition_types, taxa = _summarize_condition_sets(result.get("mainRule"))
    annotation_summary, annotation_contrib = _summarize_annotations(result.get("mainRule"))
    if condition_summary:
        if annotation_summary:
            summary["mainRule"] = {
                "conditions": condition_summary,
                "annotations": annotation_summary,
            }
        else:
            summary["mainRule"] = {"conditions": condition_summary}
    elif annotation_summary:
        summary["mainRule"] = {"annotations": annotation_summary}

    contributions["condition_types"].update(condition_types)
    contributions["taxa"].update(taxa)
    contributions["annotation_types"].update(annotation_contrib.get("annotation_types", Counter()))
    contributions["comment_types"].update(annotation_contrib.get("comment_types", Counter()))
    contributions["keywords"].update(annotation_contrib.get("keyword_names", Counter()))
    contributions["gene_names"].update(annotation_contrib.get("gene_names", Counter()))

    feature_summary, feature_types = _summarize_position_features(result.get("positionFeatureSets"))
    if feature_summary:
        summary["positionFeatures"] = feature_summary
    contributions["feature_types"].update(feature_types)

    statistics_summary, stats_contrib = _summarize_statistics(result.get("statistics"))
    if statistics_summary:
        summary["statistics"] = statistics_summary
    contributions["reviewed_counts"].extend(stats_contrib.get("reviewed_counts", []))
    contributions["unreviewed_counts"].extend(stats_contrib.get("unreviewed_counts", []))

    created = result.get("createdDate")
    modified = result.get("modifiedDate")
    if isinstance(created, str) or isinstance(modified, str):
        summary["dates"] = {}
        if isinstance(created, str):
            summary["dates"]["created"] = created
        if isinstance(modified, str):
            summary["dates"]["modified"] = modified
        if not summary["dates"]:
            summary.pop("dates", None)

    return summary, contributions


def _aggregate_statistics(contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not contributions:
        return {}

    data_classes: Counter[str] = Counter()
    condition_types: Counter[str] = Counter()
    taxa: Counter[str] = Counter()
    annotation_types: Counter[str] = Counter()
    comment_types: Counter[str] = Counter()
    keywords: Counter[str] = Counter()
    gene_names: Counter[str] = Counter()
    feature_types: Counter[str] = Counter()
    reviewed_counts: List[int] = []
    unreviewed_counts: List[int] = []

    for entry in contributions:
        data_classes.update(entry.get("data_classes", Counter()))
        condition_types.update(entry.get("condition_types", Counter()))
        taxa.update(entry.get("taxa", Counter()))
        annotation_types.update(entry.get("annotation_types", Counter()))
        comment_types.update(entry.get("comment_types", Counter()))
        keywords.update(entry.get("keywords", Counter()))
        gene_names.update(entry.get("gene_names", Counter()))
        feature_types.update(entry.get("feature_types", Counter()))
        reviewed_counts.extend([count for count in entry.get("reviewed_counts", []) if count])
        unreviewed_counts.extend([count for count in entry.get("unreviewed_counts", []) if count])

    summary: Dict[str, Any] = {}

    if data_classes:
        summary["data_class_counts"] = dict(data_classes.most_common(3))
    if condition_types:
        summary["condition_types"] = dict(condition_types.most_common(3))
    if taxa:
        summary["top_taxa_conditions"] = dict(taxa.most_common(3))
    if annotation_types:
        summary["annotation_types"] = dict(annotation_types.most_common(3))
    if comment_types:
        summary["comment_types"] = dict(comment_types.most_common(3))
    if keywords:
        summary["keywords"] = dict(keywords.most_common(3))
    if gene_names:
        summary["gene_names"] = dict(gene_names.most_common(3))
    if feature_types:
        summary["feature_types"] = dict(feature_types.most_common(3))

    if reviewed_counts:
        summary["reviewed_proteins"] = {
            "average": round(sum(reviewed_counts) / len(reviewed_counts), 1),
            "min": min(reviewed_counts),
            "max": max(reviewed_counts),
        }
    if unreviewed_counts:
        summary["unreviewed_proteins"] = {
            "average": round(sum(unreviewed_counts) / len(unreviewed_counts), 1),
            "min": min(unreviewed_counts),
            "max": max(unreviewed_counts),
        }

    return summary


def postprocess_search_unirule(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense UniRule search responses into compact summaries and statistics."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "summaries": [], "statistics": {}}

    summaries: List[Dict[str, Any]] = []
    contributions: List[Dict[str, Any]] = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        summary, contrib = _summarize_result(item)
        if summary:
            summaries.append(summary)
            contributions.append(contrib)

    total_results = len(summaries)
    examples = summaries[:EXAMPLE_LIMIT]
    statistics = _aggregate_statistics(contributions)

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

def postprocess_stream_unirule(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniRule stream responses while preserving auxiliary fields."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {**{key: value for key, value in response.items() if key != "results"}, "total_results": 0, "examples": []}

    summaries: List[Dict[str, Any]] = []

    for item in raw_results:
        if not isinstance(item, dict):
            continue
        summary, _ = _summarize_result(item)
        if summary:
            summaries.append(summary)

    examples = summaries[: min(len(summaries), 5)]

    condensed: Dict[str, Any] = {key: value for key, value in response.items() if key != "results"}
    condensed["total_results"] = len(summaries)
    condensed["examples"] = examples

    return condensed