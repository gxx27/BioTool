from collections import defaultdict
from typing import List, Dict, Any
import re

def _truncate(text: str, n: int = 120) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= n else text[: n - 3] + "..."

def _collect_examples(items: List[Dict[str, Any]], *,
                      type_key: str,
                      max_per_type: int = 2,
                      max_total: int = 8) -> List[Dict[str, Any]]:
    """
    Collect up to `max_per_type` examples per type (feature_type/type),
    capped at `max_total` overall. Each example is concise and readable.
    """
    by_type = defaultdict(list)
    for r in items:
        t = r.get(type_key, "unknown")
        by_type[t].append(r)

    examples = []
    for t, group in by_type.items():
        for r in group[:max_per_type]:
            start, end = r.get("start"), r.get("end")
            pos = f"{start}-{end}" if start is not None and end is not None else "N/A"
            examples.append({
                "type": t,
                "id": r.get("id"),
                "description": _truncate(r.get("description", "")),
                "position": pos,
                "interpro": r.get("interpro"),
                "extra": {k: v for k, v in r.items()
                          if k not in {type_key, "id", "description", "start", "end", "interpro"} and v not in (None, "")}
            })
            if len(examples) >= max_total:
                return examples
    return examples


def postprocess_overlap_translation(raw_response: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Postprocess the raw response from overlap_translation to produce:
      - summary: merged stats + insights in one place
      - examples: small, representative sample items
    """
    if not raw_response:
        return {"summary": {"note": "No features found."}, "examples": []}

    # ----- Basic counts and spans -----
    total_features = len(raw_response)
    type_counts = defaultdict(int)
    positions = []
    for r in raw_response:
        t = r.get("type", "unknown")
        type_counts[t] += 1
        if "start" in r and "end" in r and r["start"] is not None and r["end"] is not None:
            positions.append((r["start"], r["end"]))

    unique_types = list(type_counts.keys())
    if positions:
        min_start = min(s for s, _ in positions)
        max_end = max(e for _, e in positions)
        total_length = max_end - min_start + 1 if max_end >= min_start else 0
        # Simple span-sum / total_length approximation of coverage (bounded to [0,1])
        span_sum = sum(max(0, e - s + 1) for s, e in positions)
        coverage = round((span_sum / total_length), 2) if total_length > 0 else 0.0
        position_span = {"min_start": min_start, "max_end": max_end}
    else:
        coverage = 0.0
        position_span = {}

    # ----- Biological highlights consolidated into summary -----
    summary_highlights: Dict[str, Any] = {}

    # Transmembrane
    tm_types = ["TMHMM", "Phobius"]
    tm_features = [r for r in raw_response
                   if r.get("type") in tm_types and "transmembrane" in r.get("description", "").lower()]
    tm_positions = sorted({(r["start"], r["end"])
                           for r in tm_features if r.get("start") is not None and r.get("end") is not None})
    if tm_positions:
        summary_highlights["transmembrane"] = {
            "count": len(tm_positions),
            "positions": [f"{s}-{e}" for s, e in tm_positions]
        }

    # Signal peptide
    signal_features = [r for r in raw_response
                       if "signal" in (r.get("description", "").lower() + " " + r.get("type", "").lower())]
    if signal_features:
        details = []
        for r in signal_features[:5]:
            s = r.get("start", "?")
            e = r.get("end", "?")
            details.append(_truncate(f"{r.get('type','unknown')}: {r.get('description','N/A')} ({s}-{e})", 140))
        summary_highlights["signal_peptide"] = {"present": True, "details": details}
    else:
        summary_highlights["signal_peptide"] = {"present": False}

    # Major domains
    domain_types = ["Pfam", "PRINTS", "PANTHER", "NCBIfam", "TIGRfam"]
    domains = [r for r in raw_response if r.get("type") in domain_types]
    if domains:
        uniq = []
        seen = set()
        for r in domains:
            key = (r.get("id"), r.get("interpro"))
            if key not in seen:
                seen.add(key)
                desc = _truncate(r.get("description", ""), 50)
                uniq.append(f"{r.get('id','?')}: {desc}" + (f" (InterPro: {r.get('interpro')})" if r.get("interpro") else ""))
            if len(uniq) >= 10:
                break
        summary_highlights["major_domains"] = uniq

    # Structural models
    struct_types = ["sifts", "alphafold"]
    struct_features = [r for r in raw_response if r.get("type") in struct_types]
    if struct_features:
        dates = []
        coverages = []
        for r in struct_features:
            m = re.search(r"\((\d{4}/\d{2}/\d{2})\)", r.get("description", "") or "")
            if m:
                dates.append(m.group(1))
            if r.get("start") is not None and r.get("end") is not None:
                coverages.append((r["start"], r["end"]))
        unique_dates = sorted(set(dates))
        date_range = f"{unique_dates[0]} to {unique_dates[-1]}" if unique_dates else "N/A"
        full_len = position_span.get("max_end", 0)
        is_full = (len(coverages) > 0 and all(s == 1 and e == full_len for s, e in coverages)) if full_len else False
        avg_span = round(sum(e - s + 1 for s, e in coverages) / len(coverages), 1) if coverages else 0
        summary_highlights["structural_models"] = {
            "count": len(struct_features),
            "date_range": date_range,
            "coverage": "Full" if is_full else f"Partial (avg span: {avg_span})"
        }

    # Low complexity (Seg)
    seg_count = sum(1 for r in raw_response if r.get("type") == "Seg")
    if seg_count:
        seg_positions = sorted({(r["start"], r["end"])
                                for r in raw_response
                                if r.get("type") == "Seg" and r.get("start") is not None and r.get("end") is not None})
        sample = [f"{s}-{e}" for s, e in seg_positions[:5]]
        if len(seg_positions) > 5:
            sample.append("...")
        summary_highlights["low_complexity_regions"] = {
            "count": seg_count,
            "sample_positions": sample
        }

    # ----- Build final summary + examples -----
    summary: Dict[str, Any] = {
        "counts": {
            "total_features": total_features,
            "unique_types": unique_types,
            "by_type": dict(type_counts)
        },
        "span": position_span,
        "coverage_estimate": coverage,
        "highlights": summary_highlights
    }

    examples = _collect_examples(raw_response, type_key="type", max_per_type=1, max_total=3)
    return {"summary": summary, "examples": examples}


def postprocess_overlap_id(raw_response: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Postprocess the raw response from overlap_by_id to produce:
      - summary: merged stats + insights in one place
      - examples: small, representative sample items
    """
    if not raw_response:
        return {"summary": {"note": "No features found."}, "examples": []}

    # ----- Basic counts and spans -----
    total_features = len(raw_response)
    type_counts = defaultdict(int)
    positions = []
    for r in raw_response:
        t = r.get("feature_type", "unknown")
        type_counts[t] += 1
        if "start" in r and "end" in r and r["start"] is not None and r["end"] is not None:
            positions.append((r["start"], r["end"]))

    unique_types = list(type_counts.keys())
    if positions:
        min_start = min(s for s, _ in positions)
        max_end = max(e for _, e in positions)
        total_length = max_end - min_start + 1 if max_end >= min_start else 0
        sum_lengths = sum(max(0, e - s + 1) for s, e in positions)
        density = round((sum_lengths / total_length), 2) if total_length > 0 else 0.0
        position_span = {"min_start": min_start, "max_end": max_end}
    else:
        density = 0.0
        position_span = {}

    # ----- Genomic/feature highlights -----
    summary_highlights: Dict[str, Any] = {}

    # Strand / assemblies / regions
    strands = sorted({r.get("strand", 0) for r in raw_response})
    assemblies = sorted({r.get("assembly_name", "") for r in raw_response if r.get("assembly_name")})
    seq_regions = sorted({r.get("seq_region_name", "") for r in raw_response if r.get("seq_region_name")})
    if strands:
        summary_highlights["strands"] = strands
    if assemblies:
        summary_highlights["assemblies"] = assemblies
    if seq_regions:
        summary_highlights["seq_regions"] = seq_regions

    # Constitutive
    if any("constitutive" in r for r in raw_response):
        const_count = sum(1 for r in raw_response if r.get("constitutive") == 1)
        summary_highlights["constitutive_count"] = const_count

    # Parents (e.g., transcript IDs)
    parents = sorted({r.get("Parent") for r in raw_response if r.get("Parent")})
    if parents:
        summary_highlights["parents_sample"] = parents[:5]

    # Exon-centric details
    if "exon" in unique_types:
        exon_group = [r for r in raw_response if r.get("feature_type") == "exon"]
        exon_pos = sorted((r["start"], r["end"]) for r in exon_group if r.get("start") is not None and r.get("end") is not None)
        exon_info: Dict[str, Any] = {}
        # Introns from adjacent exon gaps
        if len(exon_pos) > 1:
            intron_lengths = [exon_pos[i + 1][0] - exon_pos[i][1] - 1
                              for i in range(len(exon_pos) - 1)
                              if exon_pos[i + 1][0] > exon_pos[i][1]]
            if intron_lengths:
                exon_info["introns"] = {
                    "count": len(intron_lengths),
                    "avg_length": round(sum(intron_lengths) / len(intron_lengths), 1),
                    "min": min(intron_lengths),
                    "max": max(intron_lengths)
                }
        # Rank / coding status via phases
        ranks = [r.get("rank") for r in exon_group if isinstance(r.get("rank"), int) and r.get("rank", 0) > 0]
        if ranks:
            exon_info["max_rank"] = max(ranks)
        phases = {r.get("ensembl_phase", -1) for r in exon_group}
        end_phases = {r.get("ensembl_end_phase", -1) for r in exon_group}
        exon_info["coding_status"] = "coding" if any(p != -1 for p in phases | end_phases) else "non-coding"
        if exon_info:
            summary_highlights["exon_summary"] = exon_info

    # Repeats
    if "repeat" in unique_types:
        repeat_group = [r for r in raw_response if r.get("feature_type") == "repeat"]
        logic_names = sorted({r.get("logic_name") for r in repeat_group if r.get("logic_name")})
        if logic_names:
            summary_highlights["repeat_logic_names"] = logic_names[:5]
        rpt_positions = sorted({(r["start"], r["end"])
                                for r in repeat_group
                                if r.get("start") is not None and r.get("end") is not None})
        if rpt_positions:
            sample = [f"{s}-{e}" for s, e in rpt_positions[:5]]
            if len(rpt_positions) > 5:
                sample.append("...")
            summary_highlights["repeat_coverage"] = {
                "unique_spans": len(rpt_positions),
                "sample_positions": sample
            }

    # ----- Build final summary + examples -----
    summary: Dict[str, Any] = {
        "counts": {
            "total_features": total_features,
            "unique_types": unique_types,
            "by_type": dict(type_counts)
        },
        "span": position_span,
        "feature_density": density,
        "highlights": summary_highlights
    }

    examples = _collect_examples(raw_response, type_key="feature_type")
    return {"summary": summary, "examples": examples}
