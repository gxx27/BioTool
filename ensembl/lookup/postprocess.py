from collections import Counter
from typing import Any, Dict, List


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def summarize_lookup_by_id(response: Dict[str, Any]) -> Dict[str, Any]:
    """Condense `lookup_by_id` responses into compact, informative summaries."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    overview_keys = [
        "id",
        "object_type",
        "species",
        "assembly_name",
        "biotype",
        "source",
        "logic_name",
        "version",
        "db_type",
        "start",
        "end",
        "strand",
    ]

    overview = {key: response.get(key) for key in overview_keys if response.get(key) is not None}

    transcripts = response.get("Transcript") or []
    transcripts = [item for item in transcripts if isinstance(item, dict)]

    transcript_count = len(transcripts)
    biotype_counter = Counter(t.get("biotype") for t in transcripts if t.get("biotype"))
    canonical_transcript = response.get("canonical_transcript")

    exon_lengths: List[int] = []
    exon_total = 0
    translation_lengths: List[int] = []
    translations_collected: List[Dict[str, Any]] = []

    transcript_summaries: List[Dict[str, Any]] = []
    sample_size = 3

    for transcript in transcripts:
        exons = transcript.get("Exon") or []
        exons = [e for e in exons if isinstance(e, dict)]
        exon_total += len(exons)
        for exon in exons:
            start = _safe_int(exon.get("start"))
            end = _safe_int(exon.get("end"))
            if start and end and end >= start:
                exon_lengths.append(end - start + 1)

        translation = transcript.get("Translation") or {}
        if isinstance(translation, dict) and translation:
            length = _safe_int(translation.get("length"))
            if length:
                translation_lengths.append(length)
            translations_collected.append({
                "id": translation.get("id"),
                "length": length,
                "start": translation.get("start"),
                "end": translation.get("end"),
                "parent": translation.get("Parent"),
            })

        if len(transcript_summaries) < sample_size:
            transcript_summaries.append({
                "id": transcript.get("id"),
                "is_canonical": bool(transcript.get("is_canonical")),
                "biotype": transcript.get("biotype"),
                "length": transcript.get("length"),
                "exon_count": len(exons),
                "translation": translation.get("id") if isinstance(translation, dict) else None,
            })

    exon_stats: Dict[str, Any] = {}
    if exon_lengths:
        exon_stats = {
            "total_exons": exon_total,
            "average_length": round(sum(exon_lengths) / len(exon_lengths), 1),
            "min_length": min(exon_lengths),
            "max_length": max(exon_lengths),
        }

    translation_stats: Dict[str, Any] = {}
    if translation_lengths:
        translation_stats = {
            "total_translations": len(translation_lengths),
            "average_length": round(sum(translation_lengths) / len(translation_lengths), 1),
            "min_length": min(translation_lengths),
            "max_length": max(translation_lengths),
            "samples": translations_collected[:3],
        }

    summary = {
        "overview": overview,
        "counts": {
            "transcripts": transcript_count,
            "transcript_biotypes": dict(biotype_counter),
            "exons": exon_total,
            "translations": len(translation_lengths),
        },
        "canonical_transcript": canonical_transcript,
        "transcripts_sample": transcript_summaries,
        "exon_stats": exon_stats,
        "translation_stats": translation_stats,
    }

    return summary

