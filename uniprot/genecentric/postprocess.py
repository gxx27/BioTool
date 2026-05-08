from collections import Counter
from typing import Any, Dict, List

def postprocess_search_genecentric(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize GeneCentric response into compact aggregates and samples."""
    return postprocess_stream_genecentric(response)


def postprocess_stream_genecentric(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize GeneCentric stream results into compact aggregates and samples."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary containing a 'results' list.")

    results = response.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Response['results'] must be a list of GeneCentric entries.")

    entries = [entry for entry in results if isinstance(entry, dict)]
    total_entries = len(entries)

    if total_entries == 0:
        return {
            "counts": {"total_genes": 0},
            "organism_distribution": [],
            "sequence_stats": {},
            "examples": []
        }

    organism_counter = Counter()
    sequence_lengths: List[int] = []
    related_counts: List[int] = []

    examples: List[Dict[str, Any]] = []
    sample_size = 3

    for entry in entries:
        canonical = entry.get("canonicalProtein") or {}
        canonical_seq = canonical.get("sequence") if isinstance(canonical, dict) else {}
        seq_length = canonical_seq.get("length") if isinstance(canonical_seq, dict) else None
        if isinstance(seq_length, int):
            sequence_lengths.append(seq_length)

        related = entry.get("relatedProteins") or []
        if isinstance(related, list):
            related_counts.append(len(related))
            for protein in related[:3]:
                organism = protein.get("organism")
                if isinstance(organism, dict):
                    organism_name = organism.get("scientificName")
                    if organism_name:
                        organism_counter[organism_name] += 1

        if len(examples) < sample_size:
            examples.append({
                "canonical_id": canonical.get("id"),
                "sequence_length": seq_length,
                "related_count": len(related),
                "related_sample": _extract_related_sample(related)
            })

    organism_distribution = [
        {"organism": name, "count": count}
        for name, count in organism_counter.most_common(10)
    ]

    sequence_stats = _compute_numeric_stats(sequence_lengths, labels={
        "total": "total_sequence_length",
        "average": "avg_sequence_length",
        "minimum": "min_sequence_length",
        "maximum": "max_sequence_length"
    })

    related_stats = _compute_numeric_stats(related_counts, labels={
        "total": "total_related_proteins",
        "average": "avg_related_per_gene",
        "minimum": "min_related",
        "maximum": "max_related"
    })

    summary = {
        "counts": {
            "total_genes": total_entries,
            "genes_with_related": sum(1 for count in related_counts if count > 0)
        },
        "organism_distribution": organism_distribution,
        "sequence_stats": sequence_stats,
        "related_stats": related_stats,
        "examples": examples
    }

    return summary


def _extract_related_sample(related: Any, limit: int = 3) -> List[Dict[str, Any]]:
    if not isinstance(related, list):
        return []

    sample: List[Dict[str, Any]] = []
    for protein in related[:limit]:
        if not isinstance(protein, dict):
            continue
        organism = protein.get("organism") if isinstance(protein.get("organism"), dict) else {}
        sequence = protein.get("sequence") if isinstance(protein.get("sequence"), dict) else {}
        sample.append({
            "id": protein.get("id"),
            "name": protein.get("proteinName"),
            "entryType": protein.get("entryType"),
            "sequence_length": sequence.get("length"),
            "organism": organism.get("scientificName"),
            "gene": protein.get("geneName"),
            "proteinExistence": protein.get("proteinExistence")
        })
    return sample


def _compute_numeric_stats(values: List[int], labels: Dict[str, str]) -> Dict[str, Any]:
    if not values:
        return {}

    total = sum(values)
    average = round(total / len(values), 2)
    minimum = min(values)
    maximum = max(values)

    return {
        labels.get("total", "total"): total,
        labels.get("average", "average"): average,
        labels.get("minimum", "minimum"): minimum,
        labels.get("maximum", "maximum"): maximum
    }

