from collections import Counter
from typing import Any, Dict, List


def postprocess_stream_subcellular_locations(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize subcellular location stream results into concise aggregates."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary containing a 'results' list.")

    results = response.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Response['results'] must be a list of subcellular location entries.")

    entries = [entry for entry in results if isinstance(entry, dict)]
    total_entries = len(entries)

    if total_entries == 0:
        return {
            "counts": {"total_locations": 0},
            "category_distribution": [],
            "statistics_totals": {},
            "go_terms": [],
            "examples": []
        }

    category_counter = Counter()
    keyword_counter = Counter()
    go_counter = Counter()

    total_reviewed = 0
    total_unreviewed = 0
    has_synonyms = 0
    has_is_a = 0
    has_part_of = 0

    examples: List[Dict[str, Any]] = []
    sample_size = 3

    for entry in entries:
        category = entry.get("category")
        if category:
            category_counter[category] += 1

        keyword = entry.get("keyword")
        if isinstance(keyword, dict):
            keyword_name = keyword.get("name")
            if keyword_name:
                keyword_counter[keyword_name] += 1

        statistics = entry.get("statistics")
        if isinstance(statistics, dict):
            reviewed = statistics.get("reviewedProteinCount")
            unreviewed = statistics.get("unreviewedProteinCount")
            if isinstance(reviewed, int):
                total_reviewed += reviewed
            if isinstance(unreviewed, int):
                total_unreviewed += unreviewed

        gene_ontologies = entry.get("geneOntologies")
        if isinstance(gene_ontologies, list):
            for go in gene_ontologies:
                if isinstance(go, dict):
                    go_name = go.get("name")
                    if go_name:
                        go_counter[go_name] += 1

        synonyms = entry.get("synonyms")
        if isinstance(synonyms, list) and synonyms:
            has_synonyms += 1

        is_a = entry.get("isA")
        if isinstance(is_a, list) and is_a:
            has_is_a += 1

        part_of = entry.get("partOf")
        if isinstance(part_of, list) and part_of:
            has_part_of += 1

        if len(examples) < sample_size:
            examples.append(_build_location_sample(entry))

    category_distribution = [
        {"category": category, "count": count}
        for category, count in category_counter.most_common()
    ]

    keyword_distribution = [
        {"keyword": name, "count": count}
        for name, count in keyword_counter.most_common(10)
    ]

    go_terms = [
        {"name": name, "count": count}
        for name, count in go_counter.most_common(10)
    ]

    summary = {
        "counts": {
            "total_locations": total_entries,
            "with_synonyms": has_synonyms,
            "with_is_a": has_is_a,
            "with_part_of": has_part_of
        },
        "category_distribution": category_distribution,
        "keyword_distribution": keyword_distribution,
        "statistics_totals": {
            "reviewed_proteins": total_reviewed,
            "unreviewed_proteins": total_unreviewed
        },
        "go_terms": go_terms,
        "examples": examples
    }

    return summary


def _build_location_sample(entry: Dict[str, Any], syn_limit: int = 3, relation_limit: int = 2) -> Dict[str, Any]:
    keywords = entry.get("keyword") if isinstance(entry.get("keyword"), dict) else {}
    statistics = entry.get("statistics") if isinstance(entry.get("statistics"), dict) else {}

    synonyms = entry.get("synonyms")
    if isinstance(synonyms, list):
        synonyms = synonyms[:syn_limit]
    else:
        synonyms = None

    def _relation_sample(key: str) -> List[Dict[str, Any]]:
        relations = entry.get(key)
        if not isinstance(relations, list):
            return []
        sample = []
        for rel in relations[:relation_limit]:
            if isinstance(rel, dict):
                sample.append({
                    "id": rel.get("id"),
                    "name": rel.get("name"),
                    "category": rel.get("category")
                })
        return sample

    go_terms = []
    go_list = entry.get("geneOntologies")
    if isinstance(go_list, list):
        for go in go_list[:syn_limit]:
            if isinstance(go, dict):
                go_terms.append({
                    "id": go.get("goId"),
                    "name": go.get("name")
                })

    return {
        "id": entry.get("id"),
        "name": entry.get("name"),
        "category": entry.get("category"),
        "reviewed": statistics.get("reviewedProteinCount"),
        "unreviewed": statistics.get("unreviewedProteinCount"),
        "keyword": {
            "id": keywords.get("id"),
            "name": keywords.get("name")
        } if keywords else None,
        "synonyms": synonyms,
        "gene_ontologies": go_terms,
        "is_a": _relation_sample("isA"),
        "part_of": _relation_sample("partOf")
    }

