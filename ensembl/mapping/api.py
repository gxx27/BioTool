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


def map_cdna_to_genome(
    id: str,
    region: str,
    callback: Optional[str] = None,
    include_original_region: Optional[bool] = None,
    species: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/map/cdna/{id}/{region}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if include_original_region is not None:
        params["include_original_region"] = _to_bool01(include_original_region)
    if species:
        params["species"] = species
    return _get_json(url, params, return_response=return_response)


def map_cds_to_genome(
    id: str,
    region: str,
    callback: Optional[str] = None,
    include_original_region: Optional[bool] = None,
    species: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/map/cds/{id}/{region}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if include_original_region is not None:
        params["include_original_region"] = _to_bool01(include_original_region)
    if species:
        params["species"] = species
    return _get_json(url, params, return_response=return_response)


def map_assembly(
    asm_one: str,
    asm_two: str,
    region: str,
    species: str,
    callback: Optional[str] = None,
    coord_system: Optional[str] = None,
    target_coord_system: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/map/{species}/{asm_one}/{region}/{asm_two}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if coord_system:
        params["coord_system"] = coord_system
    if target_coord_system:
        params["target_coord_system"] = target_coord_system
    return _get_json(url, params, return_response=return_response)


def map_translation_to_genome(
    id: str,
    region: str,
    callback: Optional[str] = None,
    species: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/map/translation/{id}/{region}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if species:
        params["species"] = species
    return _get_json(url, params, return_response=return_response)


