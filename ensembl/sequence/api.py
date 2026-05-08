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


def get_sequence_by_id(
    id: str,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    end: Optional[int] = None,
    expand_3prime: Optional[int] = None,
    expand_5prime: Optional[int] = None,
    format_: Optional[str] = None,
    mask: Optional[str] = None,
    mask_feature: Optional[bool] = None,
    multiple_sequences: Optional[bool] = None,
    object_type: Optional[str] = None,
    species: Optional[str] = None,
    start: Optional[int] = None,
    type_: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/sequence/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if end is not None:
        params["end"] = end
    if expand_3prime is not None:
        params["expand_3prime"] = expand_3prime
    if expand_5prime is not None:
        params["expand_5prime"] = expand_5prime
    if format_:
        params["format"] = format_
    if mask:
        params["mask"] = mask
    if mask_feature is not None:
        params["mask_feature"] = _to_bool01(mask_feature)
    if multiple_sequences is not None:
        params["multiple_sequences"] = _to_bool01(multiple_sequences)
    if object_type:
        params["object_type"] = object_type
    if species:
        params["species"] = species
    if start is not None:
        params["start"] = start
    if type_:
        params["type"] = type_
    return _get_json(url, params, return_response=return_response)


def get_sequence_by_region(
    region: str,
    species: str,
    callback: Optional[str] = None,
    coord_system: Optional[str] = None,
    coord_system_version: Optional[str] = None,
    expand_3prime: Optional[int] = None,
    expand_5prime: Optional[int] = None,
    format_: Optional[str] = None,
    mask: Optional[str] = None,
    mask_feature: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/sequence/region/{species}/{region}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if coord_system:
        params["coord_system"] = coord_system
    if coord_system_version:
        params["coord_system_version"] = coord_system_version
    if expand_3prime is not None:
        params["expand_3prime"] = expand_3prime
    if expand_5prime is not None:
        params["expand_5prime"] = expand_5prime
    if format_:
        params["format"] = format_
    if mask:
        params["mask"] = mask
    if mask_feature is not None:
        params["mask_feature"] = _to_bool01(mask_feature)
    return _get_json(url, params, return_response=return_response)


