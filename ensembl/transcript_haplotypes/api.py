import requests
from typing import Any, Dict, Optional


BASE_URL = "https://rest.ensembl.org"


def _to_bool01(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "1" if value else "0"


def _get_json(url: str, params: Dict[str, Any], return_response: bool = False) -> Any:
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)
    if return_response:
        return response
    else:
        try:
            return response.json()
        except Exception:
            return response.text


def get_transcript_haplotypes(
    id: str,
    species: str,
    aligned_sequences: Optional[bool] = None,
    callback: Optional[str] = None,
    samples: Optional[bool] = None,
    sequence: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/transcript_haplotypes/{species}/{id}"
    params: Dict[str, Any] = {}
    if aligned_sequences is not None:
        params["aligned_sequences"] = _to_bool01(aligned_sequences)
    if callback:
        params["callback"] = callback
    if samples is not None:
        params["samples"] = _to_bool01(samples)
    if sequence is not None:
        params["sequence"] = _to_bool01(sequence)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = postprocess_transcript_haplotypes(result)
    return result

def postprocess_transcript_haplotypes(result):
    """
    Summarizes the haplotype data by extracting key stats and top haplotypes.
    """
    if not isinstance(result, dict):
        return {"error": "Invalid result format"}

    summary = {
        "transcript_id": result.get("transcript_id"),
        "total_haplotype_count": result.get("total_haplotype_count"),
        "total_population_counts_summary": {k: v for k, v in sorted(result.get("total_population_counts", {}).items(), key=lambda x: x[1], reverse=True)[:5]},
    }

    def summarize_list(hap_list, hap_type):
        if not hap_list:
            return {"count": 0}
        sorted_haps = sorted(hap_list, key=lambda x: x.get("frequency", 0), reverse=True)
        hap = sorted_haps[0]
        top_hap = {
            "name": hap.get("name"),
            "frequency": hap.get("frequency"),
            "count": hap.get("count"),
            "diffs": hap.get("diffs", [])[:3],  # Limit to first 3 diffs
            "population_frequencies_summary": {k: v for k, v in sorted(hap.get("population_frequencies", {}).items(), key=lambda x: x[1], reverse=True)[:5]},
            "seq_trunc": hap.get("seq", "")[:50] + "..." if hap.get("seq") else None,
        }
        return {
            "count": len(hap_list),
            "avg_frequency": sum(h.get("frequency", 0) for h in hap_list) / len(hap_list) if hap_list else 0,
            "top_haplotype": top_hap,
            "indel_percentage": (sum(1 for h in hap_list if h.get("has_indel", 0) > 0) / len(hap_list)) * 100 if hap_list else 0,
        }

    summary["cds_haplotypes_summary"] = summarize_list(result.get("cds_haplotypes", []), "cds")
    summary["protein_haplotypes_summary"] = summarize_list(result.get("protein_haplotypes", []), "protein")

    return summary