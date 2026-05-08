import requests
from typing import Any, Dict, Optional
import sys
import os

# Import postprocess from the same directory
from .postprocess import summarize_lookup_by_id

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


def lookup_by_id(
    id: str,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    expand: Optional[bool] = None,
    format_: Optional[str] = None,
    mane: Optional[bool] = None,
    phenotypes: Optional[bool] = None,
    species: Optional[str] = None,
    utr: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Find species and database for an id; optional expansion.

    - id: Ensembl stable ID
    - db_type: e.g., "core"
    - expand/mane/phenotypes/utr: boolean-as-0/1 flags
    - format_: "full" or "condensed"
    - species: species name/alias
    """
    url = f"{BASE_URL}/lookup/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    if format_:
        params["format"] = format_
    if mane is not None:
        params["mane"] = _to_bool01(mane)
    if phenotypes is not None:
        params["phenotypes"] = _to_bool01(phenotypes)
    if species:
        params["species"] = species
    if utr is not None:
        params["utr"] = _to_bool01(utr)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_lookup_by_id(result)
    return result


def lookup_by_symbol(
    species: str,
    symbol: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    format_: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    """Find species and database for a symbol; optional expansion.

    - species: e.g., "homo_sapiens"
    - symbol: e.g., "BRCA2"
    - format_: "full" or "condensed"
    """
    url = f"{BASE_URL}/lookup/symbol/{species}/{symbol}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    if format_:
        params["format"] = format_
    return _get_json(url, params, return_response=return_response)


