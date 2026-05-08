from collections import Counter
from typing import Any, Dict, List


def postprocess_stream_literature_citations(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniProt literature citation stream results into concise aggregates."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary containing a 'results' list.")

    results = response.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Response['results'] must be a list of citation entries.")

    entries = [entry for entry in results if isinstance(entry, dict)]
    total_entries = len(entries)

    if total_entries == 0:
        return {
            "counts": {"total_citations": 0},
            "citation_types": [],
            "journal_distribution": [],
            "year_distribution": [],
            "mapping_stats": {},
            "examples": []
        }

    citation_type_counter = Counter()
    journal_counter = Counter()
    year_counter = Counter()

    total_reviewed = 0
    total_unreviewed = 0
    total_computational = 0
    total_community = 0

    examples: List[Dict[str, Any]] = []
    sample_size = 3

    for entry in entries:
        citation = entry.get("citation") or {}
        statistics = entry.get("statistics") or {}

        if isinstance(statistics, dict):
            reviewed = statistics.get("reviewedProteinCount")
            unreviewed = statistics.get("unreviewedProteinCount")
            computational = statistics.get("computationallyMappedProteinCount")
            community = statistics.get("communityMappedProteinCount")
            if isinstance(reviewed, int):
                total_reviewed += reviewed
            if isinstance(unreviewed, int):
                total_unreviewed += unreviewed
            if isinstance(computational, int):
                total_computational += computational
            if isinstance(community, int):
                total_community += community

        if isinstance(citation, dict):
            citation_type = citation.get("citationType")
            if citation_type:
                citation_type_counter[citation_type] += 1

            journal = citation.get("journal")
            if journal:
                journal_counter[journal] += 1

            publication_date = citation.get("publicationDate")
            year = _extract_year(publication_date)
            if year:
                year_counter[year] += 1

            if len(examples) < sample_size:
                examples.append(_build_citation_sample(citation, statistics))

    citation_types = [
        {"type": ctype, "count": count}
        for ctype, count in citation_type_counter.most_common()
    ]

    journal_distribution = [
        {"journal": journal, "count": count}
        for journal, count in journal_counter.most_common(10)
    ]

    year_distribution = [
        {"year": year, "count": count}
        for year, count in sorted(year_counter.items(), reverse=True)[:10]
    ]

    summary = {
        "counts": {
            "total_citations": total_entries,
            "unique_citation_types": len(citation_type_counter),
            "unique_journals": len(journal_counter)
        },
        "citation_types": citation_types,
        "journal_distribution": journal_distribution,
        "year_distribution": year_distribution,
        "mapping_stats": {
            "reviewed_proteins": total_reviewed,
            "unreviewed_proteins": total_unreviewed,
            "computationally_mapped": total_computational,
            "community_mapped": total_community
        },
        "examples": examples
    }

    return summary


def _extract_year(publication_date: Any) -> str:
    if isinstance(publication_date, int):
        return str(publication_date)
    if isinstance(publication_date, str):
        stripped = publication_date.strip()
        if len(stripped) >= 4 and stripped[:4].isdigit():
            return stripped[:4]
    return ""


def _build_citation_sample(citation: Dict[str, Any], statistics: Dict[str, Any], author_limit: int = 5) -> Dict[str, Any]:
    authors = citation.get("authors")
    if isinstance(authors, list):
        trimmed_authors = authors[:author_limit]
        if len(authors) > author_limit:
            trimmed_authors.append("...")
    else:
        trimmed_authors = None

    cross_refs = []
    citation_refs = citation.get("citationCrossReferences")
    if isinstance(citation_refs, list):
        for ref in citation_refs[:author_limit]:
            if isinstance(ref, dict):
                cross_refs.append({
                    "database": ref.get("database"),
                    "id": ref.get("id")
                })

    return {
        "id": citation.get("id"),
        "title": citation.get("title"),
        "journal": citation.get("journal"),
        "year": _extract_year(citation.get("publicationDate")),
        "type": citation.get("citationType"),
        "authors": trimmed_authors,
        "cross_references": cross_refs,
        "statistics": {
            "reviewed": statistics.get("reviewedProteinCount") if isinstance(statistics, dict) else None,
            "unreviewed": statistics.get("unreviewedProteinCount") if isinstance(statistics, dict) else None,
            "computationally_mapped": statistics.get("computationallyMappedProteinCount") if isinstance(statistics, dict) else None,
            "community_mapped": statistics.get("communityMappedProteinCount") if isinstance(statistics, dict) else None
        }
    }

