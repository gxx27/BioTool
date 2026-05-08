import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import summarize_tree, summarize_cafe_tree, summarize_homology, summarize_alignment_region

BASE_URL = "https://rest.ensembl.org"


def _to_bool01(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "1" if value else "0"


def _get_json(url: str, params: Dict[str, Any], headers: Optional[Dict[str, str]] = None, return_response: bool = False) -> Any:
    if headers is None:
        headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)
    if return_response:
        return response
    else:
        try:
            return response.json()
        except Exception:
            return response.text


# Cafe genetree endpoints
def get_cafe_genetree_by_id(
    id: str,
    callback: Optional[str] = None,
    compara: Optional[str] = None,
    nh_format: Optional[str] = None,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/cafe/genetree/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if compara:
        params["compara"] = compara
    if nh_format:
        params["nh_format"] = nh_format
    result = _get_json(url, params)
    if postprocess:
        result = summarize_cafe_tree(result)
    return result


def get_cafe_genetree_by_member_symbol(
    species: str,
    symbol: str,
    callback: Optional[str] = None,
    compara: Optional[str] = None,
    db_type: Optional[str] = None,
    external_db: Optional[str] = None,
    nh_format: Optional[str] = None,
    object_type: Optional[str] = None,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/cafe/genetree/member/symbol/{species}/{symbol}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if compara:
        params["compara"] = compara
    if db_type:
        params["db_type"] = db_type
    if external_db:
        params["external_db"] = external_db
    if nh_format:
        params["nh_format"] = nh_format
    if object_type:
        params["object_type"] = object_type
    result = _get_json(url, params)
    if postprocess:
        result = summarize_cafe_tree(result)
    return result


def get_cafe_genetree_by_member_id(
    id: str,
    species: str,
    callback: Optional[str] = None,
    compara: Optional[str] = None,
    db_type: Optional[str] = None,
    nh_format: Optional[str] = None,
    object_type: Optional[str] = None,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/cafe/genetree/member/id/{species}/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if compara:
        params["compara"] = compara
    if db_type:
        params["db_type"] = db_type
    if nh_format:
        params["nh_format"] = nh_format
    if object_type:
        params["object_type"] = object_type
    result = _get_json(url, params)
    if postprocess:
        result = summarize_cafe_tree(result)
    return result


# Gene tree endpoints
def get_genetree_by_id(
    id: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    cigar_line: Optional[bool] = None,
    clusterset_id: Optional[str] = None,
    compara: Optional[str] = None,
    nh_format: Optional[str] = None,
    prune_species: Optional[str] = None,
    prune_taxon: Optional[int] = None,
    sequence: Optional[str] = None,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/genetree/id/{id}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if cigar_line is not None:
        params["cigar_line"] = _to_bool01(cigar_line)
    if clusterset_id:
        params["clusterset_id"] = clusterset_id
    if compara:
        params["compara"] = compara
    if nh_format:
        params["nh_format"] = nh_format
    if prune_species:
        params["prune_species"] = prune_species
    if prune_taxon is not None:
        params["prune_taxon"] = str(prune_taxon)
    if sequence:
        params["sequence"] = sequence
    result = _get_json(url, params)
    if postprocess:
        result = summarize_tree(result)
    return result


def get_genetree_member_by_symbol(
    species: str,
    symbol: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    cigar_line: Optional[bool] = None,
    clusterset_id: Optional[str] = None,
    compara: Optional[str] = None,
    db_type: Optional[str] = None,
    external_db: Optional[str] = None,
    nh_format: Optional[str] = None,
    object_type: Optional[str] = None,
    prune_species: Optional[str] = None,
    prune_taxon: Optional[int] = None,
    sequence: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/genetree/member/symbol/{species}/{symbol}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if cigar_line is not None:
        params["cigar_line"] = _to_bool01(cigar_line)
    if clusterset_id:
        params["clusterset_id"] = clusterset_id
    if compara:
        params["compara"] = compara
    if db_type:
        params["db_type"] = db_type
    if external_db:
        params["external_db"] = external_db
    if nh_format:
        params["nh_format"] = nh_format
    if object_type:
        params["object_type"] = object_type
    if prune_species:
        params["prune_species"] = prune_species
    if prune_taxon is not None:
        params["prune_taxon"] = str(prune_taxon)
    if sequence:
        params["sequence"] = sequence
    result = _get_json(url, params, headers={"Content-Type":"application/json"}, return_response=return_response)
    if postprocess:
        result = summarize_tree(result)
    return result


def get_genetree_member_by_id(
    id: str,
    species: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    cigar_line: Optional[bool] = None,
    clusterset_id: Optional[str] = None,
    compara: Optional[str] = None,
    db_type: Optional[str] = None,
    nh_format: Optional[str] = None,
    object_type: Optional[str] = None,
    prune_species: Optional[str] = None,
    prune_taxon: Optional[int] = None,
    sequence: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/genetree/member/id/{species}/{id}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if cigar_line is not None:
        params["cigar_line"] = _to_bool01(cigar_line)
    if clusterset_id:
        params["clusterset_id"] = clusterset_id
    if compara:
        params["compara"] = compara
    if db_type:
        params["db_type"] = db_type
    if nh_format:
        params["nh_format"] = nh_format
    if object_type:
        params["object_type"] = object_type
    if prune_species:
        params["prune_species"] = prune_species
    if prune_taxon is not None:
        params["prune_taxon"] = str(prune_taxon)
    if sequence:
        params["sequence"] = sequence
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_tree(result)
    return result


# Alignment
def get_alignment_region(
    region: str,
    species: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    compact: Optional[bool] = None,
    compara: Optional[str] = None,
    display_species_set: Optional[str] = None,
    mask: Optional[str] = None,
    method: Optional[str] = None,
    species_set: Optional[str] = None,
    species_set_group: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/alignment/region/{species}/{region}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if compact is not None:
        params["compact"] = _to_bool01(compact)
    if compara:
        params["compara"] = compara
    if display_species_set:
        params["display_species_set"] = display_species_set
    if mask:
        params["mask"] = mask
    if method:
        params["method"] = method
    if species_set:
        params["species_set"] = species_set
    if species_set_group:
        params["species_set_group"] = species_set_group
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_alignment_region(result)
    return result


# Homology
def get_homology_by_id(
    id: str,
    species: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    cigar_line: Optional[bool] = None,
    compara: Optional[str] = None,
    format_: Optional[str] = None,
    sequence: Optional[str] = None,
    target_species: Optional[str] = None,
    target_taxon: Optional[int] = None,
    type_: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/homology/id/{species}/{id}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if cigar_line is not None:
        params["cigar_line"] = _to_bool01(cigar_line)
    if compara:
        params["compara"] = compara
    if format_:
        params["format"] = format_
    if sequence:
        params["sequence"] = sequence
    if target_species:
        params["target_species"] = target_species
    if target_taxon is not None:
        params["target_taxon"] = str(target_taxon)
    if type_:
        params["type"] = type_
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_homology(result)
    return result


def get_homology_by_symbol(
    species: str,
    symbol: str,
    aligned: Optional[bool] = None,
    callback: Optional[str] = None,
    cigar_line: Optional[bool] = None,
    compara: Optional[str] = None,
    external_db: Optional[str] = None,
    format_: Optional[str] = None,
    sequence: Optional[str] = None,
    target_species: Optional[str] = None,
    target_taxon: Optional[int] = None,
    type_: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/homology/symbol/{species}/{symbol}"
    params: Dict[str, Any] = {}
    if aligned is not None:
        params["aligned"] = _to_bool01(aligned)
    if callback:
        params["callback"] = callback
    if cigar_line is not None:
        params["cigar_line"] = _to_bool01(cigar_line)
    if compara:
        params["compara"] = compara
    if external_db:
        params["external_db"] = external_db
    if format_:
        params["format"] = format_
    if sequence:
        params["sequence"] = sequence
    if target_species:
        params["target_species"] = target_species
    if target_taxon is not None:
        params["target_taxon"] = str(target_taxon)
    if type_:
        params["type"] = type_
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_homology(result)
    return result


