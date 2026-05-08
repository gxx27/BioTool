import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import postprocess_variants

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


def variant_recoder(
    id: str,
    species: str,
    callback: Optional[str] = None,
    failed: Optional[bool] = None,
    fields: Optional[str] = None,
    ga4gh_vrs: Optional[bool] = None,
    gencode_basic: Optional[bool] = None,
    gencode_primary: Optional[bool] = None,
    minimal: Optional[bool] = None,
    var_synonyms: Optional[bool] = None,
    vcf_string: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/variant_recoder/{species}/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if failed is not None:
        params["failed"] = _to_bool01(failed)
    if fields:
        params["fields"] = fields
    if ga4gh_vrs is not None:
        params["ga4gh_vrs"] = _to_bool01(ga4gh_vrs)
    if gencode_basic is not None:
        params["gencode_basic"] = _to_bool01(gencode_basic)
    if gencode_primary is not None:
        params["gencode_primary"] = _to_bool01(gencode_primary)
    if minimal is not None:
        params["minimal"] = _to_bool01(minimal)
    if var_synonyms is not None:
        params["var_synonyms"] = _to_bool01(var_synonyms)
    if vcf_string is not None:
        params["vcf_string"] = _to_bool01(vcf_string)
    return _get_json(url, params, return_response=return_response)


def get_variation(
    id: str,
    species: str,
    callback: Optional[str] = None,
    genotypes: Optional[bool] = None,
    genotyping_chips: Optional[bool] = None,
    phenotypes: Optional[bool] = None,
    pops: Optional[bool] = None,
    population_genotypes: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/variation/{species}/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if genotypes is not None:
        params["genotypes"] = _to_bool01(genotypes)
    if genotyping_chips is not None:
        params["genotyping_chips"] = _to_bool01(genotyping_chips)
    if phenotypes is not None:
        params["phenotypes"] = _to_bool01(phenotypes)
    if pops is not None:
        params["pops"] = _to_bool01(pops)
    if population_genotypes is not None:
        params["population_genotypes"] = _to_bool01(population_genotypes)
    return _get_json(url, params, return_response=return_response)


def get_variation_by_pmcid(
    pmcid: str, 
    species: str, 
    callback: Optional[str] = None, 
    return_response: bool = False,
    postprocess: bool = True, 
) -> Any:
    url = f"{BASE_URL}/variation/{species}/pmcid/{pmcid}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = postprocess_variants(result)
    return result


def get_variation_by_pmid(
    pmid: str, 
    species: str, 
    callback: Optional[str] = None, 
    return_response: bool = False,
    postprocess: bool = True, 
) -> Any:
    url = f"{BASE_URL}/variation/{species}/pmid/{pmid}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = postprocess_variants(result)
    return result


