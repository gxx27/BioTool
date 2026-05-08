from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# ---------- Config ----------

@dataclass(frozen=True)
class VEPCompactConfig:
    # When a transcript list is longer than this, we compact it.
    compact_threshold: int = 5
    # How many transcripts to keep when compacting.
    keep_top_k: int = 5
    # Keys to keep from each transcript (others will be dropped).
    keep_keys: Optional[List[str]] = None

# Default keys to keep (lean but useful for LLMs)
DEFAULT_KEEP_KEYS = [
    # identifiers
    "transcript_id", "transcript_version", "gene_id", "gene_symbol", "gene_symbol_source", "hgnc_id",
    # consequence / effect
    "consequence_terms", "impact", "biotype",
    # position
    "strand", "cds_start", "cds_end", "cdna_start", "cdna_end", "protein_start", "protein_end",
    # sequence-level details
    "codons", "amino_acids", "variant_allele",
    # popular annotations (if requested from VEP)
    "cadd_raw", "cadd_phred", "conservation", "loeuf",
    # transcript preference flags (may or may not exist)
    "canonical", "mane_select", "appris", "ccds", "tsl",
    # HGVS strings if present
    "hgvsc", "hgvsp",
]

# Heavy fields to drop if they appear
DROP_HEAVY_KEYS = [
    "phenotypes", "pubmed_id", "domains", "uniprot", "flags", "gene_pheno",
]

# Global default config (edit here if you want different defaults—no api.py changes needed)
DEFAULT_CONFIG = VEPCompactConfig(
    compact_threshold=5,
    keep_top_k=5,
    keep_keys=DEFAULT_KEEP_KEYS,
)

# ---------- Ranking utilities ----------

# VEP consequence severity (lower is worse / more severe)
VEP_SEVERITY_RANK = {
    "transcript_ablation": 1, "splice_acceptor_variant": 2, "splice_donor_variant": 3,
    "stop_gained": 4, "frameshift_variant": 5, "stop_lost": 6, "start_lost": 7,
    "transcript_amplification": 8, "inframe_insertion": 9, "inframe_deletion": 10,
    "missense_variant": 11, "protein_altering_variant": 12, "splice_region_variant": 13,
    "incomplete_terminal_codon_variant": 14, "start_retained_variant": 15, "stop_retained_variant": 16,
    "synonymous_variant": 17, "coding_sequence_variant": 18, "mature_miRNA_variant": 19,
    "5_prime_UTR_variant": 20, "3_prime_UTR_variant": 21, "non_coding_transcript_exon_variant": 22,
    "intron_variant": 23, "NMD_transcript_variant": 24, "non_coding_transcript_variant": 25,
    "upstream_gene_variant": 26, "downstream_gene_variant": 27, "TFBS_ablation": 28,
    "TFBS_amplification": 29, "TF_binding_site_variant": 30, "regulatory_region_ablation": 31,
    "regulatory_region_amplification": 32, "feature_elongation": 33,
    "regulatory_region_variant": 34, "feature_truncation": 35, "intergenic_variant": 36,
}
APPRIS_PREF = {"principal1":1,"principal2":2,"principal3":3,"principal4":4,"principal5":5,
               "alternative1":6,"alternative2":7,"minor":8}

def _min_severity(terms: List[str]) -> int:
    if not terms: return 100
    return min(VEP_SEVERITY_RANK.get(t, 100) for t in terms)

def _appris_rank(val: Optional[str]) -> int:
    if not val: return 999
    return APPRIS_PREF.get(str(val).lower(), 999)

def _len_proxy(tc: Dict[str, Any]) -> int:
    if isinstance(tc.get("cds_end"), int) and isinstance(tc.get("cds_start"), int):
        return max(0, tc["cds_end"] - tc["cds_start"])
    if isinstance(tc.get("protein_end"), int) and isinstance(tc.get("protein_start"), int):
        return max(0, tc["protein_end"] - tc["protein_start"])
    if isinstance(tc.get("cdna_end"), int) and isinstance(tc.get("cdna_start"), int):
        return max(0, tc["cdna_end"] - tc["cdna_start"])
    return 0

def _score(tc: Dict[str, Any]) -> Tuple:
    # Lower tuple == better
    canonical = 0 if tc.get("canonical") else 1
    mane = 0 if tc.get("mane_select") else 1
    appris = _appris_rank(tc.get("appris"))
    ccds = 0 if tc.get("ccds") else 1
    severity = _min_severity(tc.get("consequence_terms", []))
    length = -_len_proxy(tc)  # prefer longer
    return (canonical, mane, appris, ccds, severity, length, tc.get("transcript_id", ""))

def _compact_one(tc: Dict[str, Any], keep_keys: List[str]) -> Dict[str, Any]:
    out = {}
    for k in keep_keys:
        if k in tc and tc[k] is not None:
            if not (isinstance(tc[k], (list, dict)) and not tc[k]):  # drop empties
                out[k] = tc[k]
    # Ensure heavy keys don’t sneak in
    for k in DROP_HEAVY_KEYS:
        out.pop(k, None)
    return out

# ---------- Public API ----------

def vep_compact(
    result: List[Dict[str, Any]],
    config: VEPCompactConfig = DEFAULT_CONFIG,
) -> List[Dict[str, Any]]:
    """
    Compact a VEP HGVS JSON result (list; usually length 1).
    If transcript_consequences > config.compact_threshold, keep best config.keep_top_k.
    Otherwise keep all transcripts but strip to essential keys.
    """
    if not result:
        return result

    processed: List[Dict[str, Any]] = []
    keep_keys = config.keep_keys or DEFAULT_KEEP_KEYS

    for entry in result:
        e = dict(entry)
        seq = e.get("transcript_consequences") or []
        if not isinstance(seq, list) or not seq:
            processed.append(e)
            continue

        # sort by preferences/severity
        ranked = sorted(seq, key=_score)

        if len(ranked) > config.compact_threshold:
            ranked = ranked[:config.keep_top_k]

        e["transcript_consequences"] = [_compact_one(tc, keep_keys) for tc in ranked]
        processed.append(e)

    return processed

# Optional: allow changing the module-wide default without touching api.py
def set_default_config(new_config: VEPCompactConfig) -> None:
    global DEFAULT_CONFIG
    DEFAULT_CONFIG = new_config
