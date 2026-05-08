"""Summaries for UniParc search responses."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXAMPLE_LIMIT = 3
TAXON_LIMIT = 3
FEATURE_LIMIT = 4
CROSS_REF_SAMPLE_LIMIT = 5
DB_DISTRIBUTION_LIMIT = 5
ORGANISM_LIMIT = 5


def _safe_int(value: Any) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _extract_taxa(common_taxons: Any) -> List[str]:
    if not isinstance(common_taxons, list):
        return []

    taxa: List[str] = []
    for entry in common_taxons:
        if not isinstance(entry, dict):
            continue
        name = entry.get("commonTaxon")
        if isinstance(name, str) and name.strip():
            taxa.append(name.strip())
        if len(taxa) >= TAXON_LIMIT:
            break
    return taxa


def _first_valid(strings: Iterable[Any]) -> Optional[str]:
    for item in strings:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def _extract_feature_labels(features: Any) -> List[str]:
    if not isinstance(features, list):
        return []

    labels: List[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        interpro = feature.get("interproGroup")
        if isinstance(interpro, dict):
            group_id = interpro.get("id")
            name = interpro.get("name")
            if isinstance(group_id, str) and group_id.strip():
                labels.append(f"InterPro:{group_id.strip()}")
            elif isinstance(name, str) and name.strip():
                labels.append(name.strip())
        if len(labels) >= FEATURE_LIMIT:
            break

    if len(labels) < FEATURE_LIMIT:
        for feature in features:
            if not isinstance(feature, dict):
                continue
            database = feature.get("database")
            database_id = feature.get("databaseId")
            if isinstance(database, str) and isinstance(database_id, str):
                label = f"{database}:{database_id}"
                if label not in labels:
                    labels.append(label)
                if len(labels) >= FEATURE_LIMIT:
                    break

    return labels[:FEATURE_LIMIT]


def _summarize_feature_examples(features: Any) -> List[Dict[str, Any]]:
    if not isinstance(features, list):
        return []

    examples: List[Dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        entry: Dict[str, Any] = {}
        interpro = feature.get("interproGroup")
        if isinstance(interpro, dict):
            entry["label"] = interpro.get("name") or interpro.get("id")
        if "label" not in entry:
            database = feature.get("database")
            database_id = feature.get("databaseId")
            if isinstance(database, str) and isinstance(database_id, str):
                entry["label"] = f"{database}:{database_id}"
        locations = feature.get("locations")
        if isinstance(locations, list) and locations:
            loc = locations[0]
            if isinstance(loc, dict):
                start = loc.get("start")
                end = loc.get("end")
                if start is not None and end is not None:
                    entry["range"] = f"{start}-{end}"
        if entry:
            examples.append(entry)
        if len(examples) >= FEATURE_LIMIT:
            break
    return examples


def _summarize_cross_references(cross_refs: Any) -> Dict[str, Any]:
    if not isinstance(cross_refs, list):
        return {"total": 0, "active": 0, "inactive": 0, "top_databases": {}, "top_organisms": {}, "examples": []}

    total = 0
    active = 0
    db_counter: Counter[str] = Counter()
    organism_counter: Counter[str] = Counter()
    samples: List[Dict[str, Any]] = []

    for cross_ref in cross_refs:
        if not isinstance(cross_ref, dict):
            continue
        total += 1
        if cross_ref.get("active"):
            active += 1

        database = cross_ref.get("database")
        if isinstance(database, str) and database:
            db_counter[database] += 1

        organism = cross_ref.get("organism")
        if isinstance(organism, dict):
            org_name = organism.get("scientificName") or organism.get("commonName")
            if isinstance(org_name, str) and org_name.strip():
                organism_counter[org_name.strip()] += 1

        if len(samples) < CROSS_REF_SAMPLE_LIMIT:
            sample = {
                "database": database,
                "id": cross_ref.get("id"),
                "active": bool(cross_ref.get("active")),
            }
            if isinstance(organism, dict):
                sample_org = organism.get("scientificName") or organism.get("commonName")
                if sample_org:
                    sample["organism"] = sample_org
            if cross_ref.get("proteinName"):
                sample["protein"] = cross_ref.get("proteinName")
            elif cross_ref.get("geneName"):
                sample["gene"] = cross_ref.get("geneName")
            if cross_ref.get("lastUpdated"):
                sample["lastUpdated"] = cross_ref.get("lastUpdated")
            samples.append(sample)

    inactive = max(total - active, 0)

    return {
        "total": total,
        "active": active,
        "inactive": inactive,
        "top_databases": dict(db_counter.most_common(DB_DISTRIBUTION_LIMIT)),
        "top_organisms": dict(organism_counter.most_common(ORGANISM_LIMIT)),
        "examples": samples,
    }


def _summarize_sequence(sequence: Any) -> Dict[str, Any]:
    if not isinstance(sequence, dict):
        return {}

    summary: Dict[str, Any] = {}
    length = sequence.get("length")
    if isinstance(length, int):
        summary["length"] = length
    mol_weight = sequence.get("molWeight")
    if mol_weight is not None:
        summary["molecularWeight"] = mol_weight
    crc64 = sequence.get("crc64")
    if crc64:
        summary["crc64"] = crc64
    md5 = sequence.get("md5")
    if md5:
        summary["md5"] = md5

    sequence_value = sequence.get("value")
    if isinstance(sequence_value, str) and sequence_value:
        summary["preview"] = sequence_value[:20] + "…" if len(sequence_value) > 20 else sequence_value

    return summary


def _summarize_entry(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(entry, dict):
        return {}, {
            "lengths": [],
            "cross_refs": [],
            "taxa": Counter(),
            "feature_databases": Counter(),
        }

    uni_parc_id = entry.get("uniParcId")
    if not isinstance(uni_parc_id, str) or not uni_parc_id.strip():
        return {}, {
            "lengths": [],
            "cross_refs": [],
            "taxa": Counter(),
            "feature_databases": Counter(),
        }

    sequence = entry.get("sequence")
    sequence_length = _safe_int(sequence.get("length")) if isinstance(sequence, dict) else 0
    cross_refs = _safe_int(entry.get("crossReferenceCount"))

    summary: Dict[str, Any] = {"uniParcId": uni_parc_id.strip()}
    if sequence_length:
        summary["length"] = sequence_length
    if cross_refs:
        summary["crossReferences"] = cross_refs

    taxa = _extract_taxa(entry.get("commonTaxons"))
    if taxa:
        summary["taxa"] = taxa

    accession = None
    if isinstance(entry.get("uniProtKBAccessions"), list):
        accession = _first_valid(entry["uniProtKBAccessions"])
    if accession:
        summary["representativeAccession"] = accession

    feature_labels = _extract_feature_labels(entry.get("sequenceFeatures"))
    if feature_labels:
        summary["features"] = feature_labels

    contributions = {
        "lengths": [sequence_length] if sequence_length else [],
        "cross_refs": [cross_refs] if cross_refs else [],
        "taxa": Counter(taxa),
        "feature_databases": Counter(
            label.split(":", 1)[0] for label in feature_labels if ":" in label
        ),
    }

    return summary, contributions


def _aggregate_statistics(contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not contributions:
        return {}

    lengths: List[int] = []
    cross_refs: List[int] = []
    taxa_counter: Counter[str] = Counter()
    feature_db_counter: Counter[str] = Counter()

    for contribution in contributions:
        lengths.extend(contribution.get("lengths", []))
        cross_refs.extend(contribution.get("cross_refs", []))
        taxa_counter.update(contribution.get("taxa", Counter()))
        feature_db_counter.update(contribution.get("feature_databases", Counter()))

    stats: Dict[str, Any] = {}

    if lengths:
        stats["sequence_length"] = {
            "average": round(sum(lengths) / len(lengths), 1),
            "min": min(lengths),
            "max": max(lengths),
        }

    if cross_refs:
        stats["cross_references"] = {
            "average": round(sum(cross_refs) / len(cross_refs), 1),
            "min": min(cross_refs),
            "max": max(cross_refs),
        }

    if taxa_counter:
        stats["top_taxa"] = dict(taxa_counter.most_common(5))

    if feature_db_counter:
        stats["feature_sources"] = dict(feature_db_counter.most_common(5))

    return stats


def postprocess_search_uniparc(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense UniParc search response into concise summaries and statistics."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "summaries": [], "statistics": {}}

    summaries: List[Dict[str, Any]] = []
    contributions: List[Dict[str, Any]] = []

    for entry in raw_results:
        summary, contribution = _summarize_entry(entry)
        if summary:
            summaries.append(summary)
            contributions.append(contribution)

    total_results = len(summaries)
    examples = summaries[:EXAMPLE_LIMIT]
    statistics = _aggregate_statistics(contributions)

    condensed: Dict[str, Any] = {
        "total_results": total_results,
        "summaries": examples,
    }

    if statistics:
        condensed["statistics"] = statistics

    total_reported = response.get("totalResults") or response.get("total")
    if isinstance(total_reported, int):
        condensed["total_reported"] = total_reported

    facets = response.get("facets")
    if isinstance(facets, dict) and facets:
        condensed["facets"] = list(facets.keys())

    return condensed

def postprocess_stream_uniparc(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense UniParc stream response into concise summaries and statistics."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    raw_results = response.get("results")
    if not isinstance(raw_results, list):
        return {"total_results": 0, "examples": [], "statistics": {}}

    summaries: List[Dict[str, Any]] = []
    contributions: List[Dict[str, Any]] = []

    for entry in raw_results:
        summary, contribution = _summarize_entry(entry)
        if summary:
            summaries.append(summary)
            contributions.append(contribution)

    total_results = len(summaries)
    examples = summaries[: min(total_results, 5)]
    statistics = _aggregate_statistics(contributions)

    condensed: Dict[str, Any] = {
        key: value for key, value in response.items() if key != "results"
    }
    condensed["total_results"] = total_results
    condensed["examples"] = examples

    if statistics:
        condensed["statistics"] = statistics

    return condensed


def postprocess_get_uniparc_by_upi(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniParc entry details fetched by UPI into concise aggregates."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    uni_parc_id = response.get("uniParcId")
    if not isinstance(uni_parc_id, str) or not uni_parc_id.strip():
        raise ValueError("Response must contain a 'uniParcId'.")

    cross_reference_summary = _summarize_cross_references(response.get("uniParcCrossReferences"))
    sequence_summary = _summarize_sequence(response.get("sequence"))

    feature_labels = _extract_feature_labels(response.get("sequenceFeatures"))
    feature_examples = _summarize_feature_examples(response.get("sequenceFeatures"))

    entry_summary: Dict[str, Any] = {
        "uniParcId": uni_parc_id.strip(),
    }
    if sequence_summary.get("length"):
        entry_summary["sequenceLength"] = sequence_summary["length"]
    if cross_reference_summary.get("total"):
        entry_summary["crossReferences"] = cross_reference_summary["total"]

    timeline: Dict[str, Any] = {}
    oldest = response.get("oldestCrossRefCreated")
    latest = response.get("mostRecentCrossRefUpdated")
    if oldest:
        timeline["oldestCrossReference"] = oldest
    if latest:
        timeline["mostRecentCrossReference"] = latest

    result: Dict[str, Any] = {
        "summary": entry_summary,
        "cross_references": cross_reference_summary,
    }

    if sequence_summary:
        result["sequence"] = sequence_summary

    if feature_labels or feature_examples:
        features_section: Dict[str, Any] = {}
        if feature_labels:
            features_section["labels"] = feature_labels
        if feature_examples:
            features_section["examples"] = feature_examples
        result["features"] = features_section

    if timeline:
        result["history"] = timeline

    return result