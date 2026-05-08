from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple

_MAX_SETS = 3
_KEEP_POPS: Tuple[str, ...] = ("ALL", "NFE", "EAS", "AFR")
_MAX_TRAITS = 5
_MAX_CLINVAR = 3
_MAX_EXTERNAL = 2
_ROUND = 3

_POP_MAP: Tuple[Tuple[str, str], ...] = (
    ("Non-Finnish European", "NFE"),
    ("East Asian", "EAS"),
    ("African/African-American", "AFR"),
    ("Latino", "AMR"),
    ("Finnish", "FIN"),
    ("Ashkenazi Jewish", "ASJ"),
    ("South Asian", "SAS"),
    ("Middle Eastern", "MDE"),
    ("Amish", "AMI"),
    ("gnomAD genomes", "ALL"),  # keep last so specific pops match first
)

def _pop_code(label: str) -> Optional[str]:
    for needle, code in _POP_MAP:
        if needle in (label or ""):
            return code
    return None

def _prune(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: _prune(v) for k, v in o.items() if v not in (None, {}, [], ())}
    if isinstance(o, list):
        return [_prune(v) for v in o if v not in (None, {}, [], ())]
    return o

def post_process_query_beacon(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simplify and normalize a GA4GH Beacon v2 response.

    Returns:
        A compact, readable, and semantically clear dictionary for function-calling or LLM training.
    """
    # Keep the full summary instead of just a boolean
    out: Dict[str, Any] = {
        "Summary": (result or {}).get("responseSummary", {})
    }

    sets: List[Dict[str, Any]] = ((result.get("response", {}) or {}).get("resultSets", []) or [])[:_MAX_SETS]

    rsids: List[str] = []
    clinvars: List[str] = []
    genes: List[str] = []
    traits: List[str] = []
    pops: Dict[str, float] = {}
    sources: List[str] = []
    externals: List[str] = []

    v_core: Optional[Dict[str, Any]] = None
    consequence: Optional[str] = None

    for s in sets:
        sid = s.get("id")
        if sid:
            sources.append(sid)
        externals.extend(s.get("externalUrl", []) or [])

        for r in s.get("results", []) or []:
            v = r.get("variation") or {}
            loc = ((v.get("location") or {}).get("interval") or {})
            alts = (v.get("alternateBases") or "")
            alt_list = [a.strip() for a in alts.split(",") if a.strip()] if alts else []
            alt = alt_list[0] if alt_list else None

            if not v_core:
                v_core = {
                    "Chromosome": ((v.get("location") or {}).get("sequence_id")),
                    "Position": (loc.get("start") or {}).get("value"),
                    "ReferenceBase": v.get("referenceBases"),
                    "AlternateBase": alt,
                    "VariantType": v.get("variantType"),
                }

            for ident in r.get("identifiers", []) or []:
                if ident.startswith("dbSNP:"):
                    rsids.append(ident.split(":", 1)[1])
                elif ident.startswith("ClinVar:"):
                    clinvars.append(ident.split(":", 1)[1])

            ma = r.get("MolecularAttributes") or {}
            genes.extend(ma.get("geneIds", []) or [])
            effs = ma.get("molecularEffects", []) or []
            if not consequence and effs:
                consequence = effs[0].get("id") or effs[0].get("label")

            clin = (r.get("variantLevelData") or {}).get("clinicalInterpretations", []) or []
            for ci in clin:
                eff = ci.get("effect") or {}
                tid = eff.get("id") or eff.get("label")
                if tid:
                    traits.append(tid)

            freqs = ((r.get("FrequencyInPopulations") or {}).get("frequencies") or [])
            for f in freqs:
                code = _pop_code(f.get("population") or "")
                if code:
                    af = f.get("alleleFrequency")
                    if af is None:
                        continue
                    if code == "ALL":
                        pops.setdefault("Overall", round(float(af), _ROUND))
                    elif code in _KEEP_POPS:
                        pops.setdefault(code, round(float(af), _ROUND))

    if v_core:
        rsid = (sorted(set(rsids)) or [None])[0]
        out["VariantInfo"] = {
            **v_core,
            "rsID": rsid,
            "GeneIDs": sorted(set(genes))[:3],
            "Consequence": consequence,
        }

    out["Identifiers"] = {
        "dbSNP": (sorted(set(rsids)) or [None])[0],
        "ClinVar": sorted(set(clinvars))[:_MAX_CLINVAR],
    }

    out["Frequencies"] = {
        "AlleleFrequency": pops.get("Overall"),
        "PopulationFrequencies": {k: v for k, v in pops.items() if k != "Overall"},
    }

    compact_traits = [
        t for t in sorted(set(traits))
        if isinstance(t, str) and t.startswith(("EFO:", "MONDO:", "HP:"))
    ]
    out["AssociatedTraits"] = compact_traits[:_MAX_TRAITS]

    out["DataSources"] = [s for s in sources if s][: _MAX_SETS]
    out["ExternalLinks"] = sorted(set(externals))[:_MAX_EXTERNAL]

    return _prune(out)
