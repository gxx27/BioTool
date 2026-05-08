"""Summaries for UniProtKB search responses."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

EXAMPLE_LIMIT = 2
MAX_NAMES = 2
MAX_LOCATIONS = 2
MAX_REACTIONS = 1
MAX_KEYWORDS = 2
MAX_FUNCTION_WORDS = 40
MAX_INTERACTIONS = 3
MAX_REFERENCES = 3
MAX_MAPPED_DATABASES = 3


def _safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _truncate_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]) + "…"


def _first_non_empty(strings: Iterable[Any]) -> Optional[str]:
    for item in strings:
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


def _extract_protein_name(description: Any) -> Dict[str, Any]:
    if not isinstance(description, dict):
        return {}

    summary: Dict[str, Any] = {}

    recommended = description.get("recommendedName")
    if isinstance(recommended, dict):
        full = recommended.get("fullName")
        if isinstance(full, dict):
            value = full.get("value")
            if isinstance(value, str) and value.strip():
                summary["recommendedName"] = value.strip()
        short_names = recommended.get("shortNames")
        if isinstance(short_names, list):
            first_short = _first_non_empty(item.get("value") for item in short_names if isinstance(item, dict))
            if first_short:
                summary["shortName"] = first_short

        ec_numbers = recommended.get("ecNumbers")
        if isinstance(ec_numbers, list):
            first_ec = _first_non_empty(item.get("value") for item in ec_numbers if isinstance(item, dict))
            if first_ec:
                summary["ecNumber"] = first_ec

    alternative = description.get("alternativeNames")
    if isinstance(alternative, list):
        alt_names = []
        for item in alternative:
            if not isinstance(item, dict):
                continue
            full = item.get("fullName")
            if isinstance(full, dict) and isinstance(full.get("value"), str):
                alt_names.append(full["value"].strip())
            if len(alt_names) >= MAX_NAMES:
                break
        if alt_names:
            summary["alternativeNames"] = alt_names

    return summary


def _extract_gene_names(genes: Any) -> List[str]:
    if not isinstance(genes, list):
        return []

    names: List[str] = []
    for gene in genes:
        if not isinstance(gene, dict):
            continue
        name = gene.get("geneName")
        if isinstance(name, dict):
            value = name.get("value")
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
        if len(names) >= MAX_NAMES:
            break
    return names


def _extract_locations(locations: Any) -> List[str]:
    if not isinstance(locations, list):
        return []

    results: List[str] = []
    for item in locations:
        if not isinstance(item, dict):
            continue
        location = item.get("location")
        if isinstance(location, dict):
            value = location.get("value")
            if isinstance(value, str) and value.strip():
                results.append(value.strip())
        if len(results) >= MAX_LOCATIONS:
            break
    return results


def _extract_comments(comments: Any) -> Dict[str, Any]:
    if not isinstance(comments, list):
        return {}

    summary: Dict[str, Any] = {}

    for comment in comments:
        if not isinstance(comment, dict):
            continue
        comment_type = comment.get("commentType")
        if not isinstance(comment_type, str):
            continue

        if comment_type == "FUNCTION" and "function" not in summary:
            texts = comment.get("texts")
            description = _first_non_empty(item.get("value") for item in texts if isinstance(item, dict))
            if isinstance(description, str) and description.strip():
                summary["function"] = _truncate_words(description.strip(), MAX_FUNCTION_WORDS)

        if comment_type == "SUBCELLULAR LOCATION" and "subcellularLocation" not in summary:
            locations = _extract_locations(comment.get("subcellularLocations"))
            if locations:
                summary["subcellularLocation"] = locations

        if comment_type == "CATALYTIC ACTIVITY" and "reactions" not in summary:
            reactions = []
            reaction = comment.get("reaction")
            if isinstance(reaction, dict):
                name = reaction.get("name")
                if isinstance(name, str) and name.strip():
                    reactions.append(_truncate_words(name.strip(), MAX_FUNCTION_WORDS))
            if reactions:
                summary["reactions"] = reactions[:MAX_REACTIONS]

    return summary


def _extract_features(features: Any) -> Dict[str, int]:
    if not isinstance(features, list):
        return {}

    counter: Counter[str] = Counter()
    for feature in features:
        if isinstance(feature, dict):
            feature_type = feature.get("type")
            if isinstance(feature_type, str) and feature_type.strip():
                counter[feature_type.strip()] += 1
    return dict(counter.most_common(3))


def _summarize_interactions(comments: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(comments, list):
        return None

    interactions_summary: List[Dict[str, Any]] = []
    total = 0

    for comment in comments:
        if not isinstance(comment, dict):
            continue
        if comment.get("commentType") != "INTERACTION":
            continue
        interactions = comment.get("interactions")
        if not isinstance(interactions, list):
            continue

        for interaction in interactions:
            if not isinstance(interaction, dict):
                continue
            partner = interaction.get("interactantTwo")
            if not isinstance(partner, dict):
                continue
            total += 1
            summary = {
                "accession": partner.get("uniProtKBAccession"),
                "gene": partner.get("geneName"),
                "experiments": interaction.get("numberOfExperiments"),
            }
            if len(interactions_summary) < MAX_INTERACTIONS:
                interactions_summary.append(summary)

    if total == 0:
        return None

    return {
        "count": total,
        "examples": interactions_summary,
    }


def _summarize_isoforms(comments: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(comments, list):
        return None

    for comment in comments:
        if not isinstance(comment, dict):
            continue
        if comment.get("commentType") != "ALTERNATIVE PRODUCTS":
            continue
        isoforms = comment.get("isoforms")
        if not isinstance(isoforms, list):
            continue
        total = len([iso for iso in isoforms if isinstance(iso, dict)])
        summaries = []
        for isoform in isoforms[:MAX_NAMES]:
            if not isinstance(isoform, dict):
                continue
            summaries.append({
                "name": isoform.get("name", {}).get("value") if isinstance(isoform.get("name"), dict) else None,
                "isoformIds": isoform.get("isoformIds"),
                "status": isoform.get("isoformSequenceStatus")
            })
        if total == 0:
            return None
        examples = [item for item in summaries if item]
        return {
            "total": total,
            "examples": examples,
        }

    return None


def _summarize_references(references: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(references, list):
        return None

    total = 0
    summaries: List[Dict[str, Any]] = []
    for reference in references:
        if not isinstance(reference, dict):
            continue
        total += 1
        citation = reference.get("citation")
        if not isinstance(citation, dict):
            continue
        summaries.append({
            "title": citation.get("title"),
            "journal": citation.get("journal"),
            "year": citation.get("publicationDate"),
            "type": citation.get("citationType"),
            "referenceNumber": reference.get("referenceNumber")
        })
        if len(summaries) >= MAX_REFERENCES:
            break
    if total == 0:
        return None
    return {
        "total": total,
        "examples": summaries,
    }


def _summarize_cross_references(cross_refs: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(cross_refs, list):
        return None

    total = 0
    db_counter: Counter[str] = Counter()
    summaries: List[Dict[str, Any]] = []
    for ref in cross_refs:
        if not isinstance(ref, dict):
            continue
        database = ref.get("database")
        identifier = ref.get("id")
        if database:
            db_counter[database] += 1
        if database and identifier and len(summaries) < MAX_MAPPED_DATABASES:
            summaries.append({
                "database": database,
                "id": identifier
            })
        total += 1
    if total == 0:
        return None
    return {
        "total": total,
        "topDatabases": dict(db_counter.most_common(MAX_MAPPED_DATABASES)),
        "examples": summaries,
    }


def _summarize_entry(entry: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if not isinstance(entry, dict):
        return {}, {
            "annotation_scores": [],
            "organisms": Counter(),
            "keywords": Counter(),
            "feature_types": Counter(),
        }

    primary_accession = entry.get("primaryAccession")
    if not isinstance(primary_accession, str) or not primary_accession.strip():
        return {}, {
            "annotation_scores": [],
            "organisms": Counter(),
            "keywords": Counter(),
            "feature_types": Counter(),
        }

    summary: Dict[str, Any] = {"accession": primary_accession.strip()}

    entry_type = entry.get("entryType")
    if isinstance(entry_type, str):
        summary["entryType"] = entry_type

    uniProt_id = entry.get("uniProtkbId")
    if isinstance(uniProt_id, str) and uniProt_id.strip():
        summary["uniprotId"] = uniProt_id.strip()

    protein_description = _extract_protein_name(entry.get("proteinDescription"))
    if protein_description:
        summary["protein"] = protein_description

    gene_names = _extract_gene_names(entry.get("genes"))
    if gene_names:
        summary["genes"] = gene_names

    organism = entry.get("organism")
    organism_name = None
    if isinstance(organism, dict):
        organism_name = organism.get("scientificName")
        if isinstance(organism_name, str) and organism_name.strip():
            summary["organism"] = organism_name.strip()

    protein_existence = entry.get("proteinExistence")
    if isinstance(protein_existence, str):
        summary["proteinExistence"] = protein_existence

    annotation_score = _safe_float(entry.get("annotationScore"))
    if annotation_score is not None:
        summary["annotationScore"] = annotation_score

    entry_audit = entry.get("entryAudit")
    if isinstance(entry_audit, dict):
        timeline: Dict[str, Any] = {}
        for key in ("firstPublicDate", "lastAnnotationUpdateDate", "lastSequenceUpdateDate"):
            value = entry_audit.get(key)
            if isinstance(value, str) and value.strip():
                timeline[key] = value.strip()
        if timeline:
            summary["dates"] = timeline

    comment_summary = _extract_comments(entry.get("comments"))
    if comment_summary:
        summary.update(comment_summary)

    interactions = _summarize_interactions(entry.get("comments"))
    if interactions:
        summary["interactions"] = interactions

    isoforms = _summarize_isoforms(entry.get("comments"))
    if isoforms:
        summary["isoforms"] = isoforms

    feature_counts = _extract_features(entry.get("features"))
    if feature_counts:
        summary["featureCounts"] = feature_counts

    keywords = entry.get("keywords")
    if isinstance(keywords, list):
        keyword_names = []
        for keyword in keywords:
            if not isinstance(keyword, dict):
                continue
            name = keyword.get("name")
            if isinstance(name, str) and name.strip():
                keyword_names.append(name.strip())
            if len(keyword_names) >= MAX_KEYWORDS:
                break
        if keyword_names:
            summary["keywords"] = keyword_names

    references = _summarize_references(entry.get("references"))
    if references:
        summary["references"] = references

    cross_refs = _summarize_cross_references(entry.get("uniProtKBCrossReferences"))
    if cross_refs:
        summary["crossReferences"] = cross_refs

    contributions = {
        "annotation_scores": [annotation_score] if annotation_score is not None else [],
        "organisms": Counter([organism_name.strip()]) if organism_name else Counter(),
        "keywords": Counter(summary.get("keywords", [])),
        "feature_types": Counter(feature_counts),
    }

    return summary, contributions


def _aggregate_statistics(contributions: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not contributions:
        return {}

    annotation_scores: List[float] = []
    organisms: Counter[str] = Counter()
    keywords: Counter[str] = Counter()
    features: Counter[str] = Counter()

    for contribution in contributions:
        annotation_scores.extend(contribution.get("annotation_scores", []))
        organisms.update(contribution.get("organisms", Counter()))
        keywords.update(contribution.get("keywords", Counter()))
        features.update(contribution.get("feature_types", Counter()))

    statistics: Dict[str, Any] = {}

    if annotation_scores:
        average_score = round(sum(annotation_scores) / len(annotation_scores), 2)
        if len(annotation_scores) == 1:
            statistics["annotationScore"] = average_score
        else:
            statistics["annotationScore"] = {
                "average": average_score,
                "min": round(min(annotation_scores), 2),
                "max": round(max(annotation_scores), 2),
            }

    if organisms:
        statistics["topOrganisms"] = dict(organisms.most_common(5))

    if keywords:
        statistics["topKeywords"] = dict(keywords.most_common(5))

    if features:
        statistics["featureTypes"] = dict(features.most_common(5))

    return statistics


def postprocess_search_uniprotkb(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniProtKB search results with concise examples and statistics."""

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

def postprocess_stream_uniprotkb(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniProtKB stream results with concise examples and statistics."""

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


def postprocess_get_uniprotkb_entry(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize a single UniProtKB entry fetched by accession."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    summary, contribution = _summarize_entry(response)
    if not summary:
        return {}

    statistics = _aggregate_statistics([contribution])

    result: Dict[str, Any] = {"summary": summary}
    if statistics:
        result["statistics"] = statistics

    key_components = {
        key: summary[key]
        for key in ("function", "subcellularLocation", "interactions", "isoforms")
        if summary.get(key)
    }
    if key_components:
        result["key_components"] = key_components

    return result