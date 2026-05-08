from collections import Counter
from typing import Any, Dict, List


def postprocess_stream_uniref(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniRef stream results into concise aggregates and samples."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary containing a 'results' list.")

    results = response.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Response['results'] must be a list of UniRef entries.")

    entries = [entry for entry in results if isinstance(entry, dict)]
    total_entries = len(entries)

    if total_entries == 0:
        return {
            "counts": {"total_clusters": 0},
            "entry_type_distribution": [],
            "taxon_distribution": [],
            "member_stats": {},
            "sequence_stats": {},
            "examples": []
        }

    entry_type_counter = Counter()
    taxon_counter = Counter()
    taxon_name_counter = Counter()
    member_counts: List[int] = []
    organism_counts: List[int] = []
    sequence_lengths: List[int] = []

    examples: List[Dict[str, Any]] = []
    sample_size = 3

    for entry in entries:
        entry_type = entry.get("entryType")
        if entry_type:
            entry_type_counter[entry_type] += 1

        common_taxon = entry.get("commonTaxon") or {}
        taxon_id = common_taxon.get("taxonId") if isinstance(common_taxon, dict) else None
        taxon_name = common_taxon.get("scientificName") if isinstance(common_taxon, dict) else None
        if taxon_id:
            taxon_counter[taxon_id] += 1
        if taxon_name:
            taxon_name_counter[taxon_name] += 1

        member_count = entry.get("memberCount")
        organism_count = entry.get("organismCount")
        if isinstance(member_count, int):
            member_counts.append(member_count)
        if isinstance(organism_count, int):
            organism_counts.append(organism_count)

        representative = entry.get("representativeMember") or {}
        sequence = representative.get("sequence") if isinstance(representative, dict) else {}
        seq_length = sequence.get("length") if isinstance(sequence, dict) else None
        if isinstance(seq_length, int):
            sequence_lengths.append(seq_length)

        if len(examples) < sample_size:
            examples.append({
                "id": entry.get("id"),
                "name": entry.get("name"),
                "entryType": entry_type,
                "memberCount": member_count,
                "organismCount": organism_count,
                "commonTaxon": {
                    "taxonId": taxon_id,
                    "scientificName": taxon_name
                } if taxon_id or taxon_name else None,
                "representative": {
                    "organismTaxId": representative.get("organismTaxId"),
                    "sequenceLength": seq_length,
                    "proteinName": representative.get("proteinName"),
                    "memberId": representative.get("memberId")
                }
            })

    entry_type_distribution = [
        {"entryType": etype, "count": count}
        for etype, count in entry_type_counter.most_common()
    ]

    taxon_distribution = [
        {"taxonId": taxon_id, "count": count}
        for taxon_id, count in taxon_counter.most_common(10)
    ]

    taxon_name_distribution = [
        {"scientificName": name, "count": count}
        for name, count in taxon_name_counter.most_common(10)
    ]

    member_stats = _compute_numeric_stats(member_counts, labels={
        "total": "total_members",
        "average": "avg_members_per_cluster",
        "minimum": "min_members",
        "maximum": "max_members"
    })

    organism_stats = _compute_numeric_stats(organism_counts, labels={
        "total": "total_organisms",
        "average": "avg_organisms_per_cluster",
        "minimum": "min_organisms",
        "maximum": "max_organisms"
    })

    sequence_stats = _compute_numeric_stats(sequence_lengths, labels={
        "total": "total_sequence_length",
        "average": "avg_sequence_length",
        "minimum": "min_sequence_length",
        "maximum": "max_sequence_length"
    })

    summary = {
        "counts": {
            "total_clusters": total_entries,
            "clusters_with_sequences": len(sequence_lengths),
            "unique_entry_types": len(entry_type_counter),
            "unique_taxa": len(taxon_counter)
        },
        "entry_type_distribution": entry_type_distribution,
        "taxon_distribution": taxon_distribution,
        "taxon_name_distribution": taxon_name_distribution,
        "member_stats": member_stats,
        "organism_stats": organism_stats,
        "sequence_stats": sequence_stats,
        "examples": examples
    }

    return summary


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

