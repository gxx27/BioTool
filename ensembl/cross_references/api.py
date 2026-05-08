import requests
from typing import Any, Dict, Optional
import sys
import os

# Import postprocess from the same directory
from .postprocess import summarize_xrefs_by_id

BASE_URL = "https://rest.ensembl.org"


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


def get_xrefs_by_symbol(
    species: str,
    symbol: str,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    external_db: Optional[str] = None,
    object_type: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    """Lookup external symbol and return linked Ensembl objects.

    - species: e.g., "homo_sapiens"
    - symbol: e.g., "BRCA2"
    - db_type: e.g., "core"
    - external_db: e.g., "HGNC"
    - object_type: e.g., "gene" or "transcript"
    """
    url = f"{BASE_URL}/xrefs/symbol/{species}/{symbol}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if external_db:
        params["external_db"] = external_db
    if object_type:
        params["object_type"] = object_type
    return _get_json(url, params, return_response=return_response)


def get_xrefs_by_id(
    id: str,
    all_levels: Optional[bool] = None,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    external_db: Optional[str] = None,
    object_type: Optional[str] = None,
    species: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Lookup Ensembl id to retrieve external references.

    - id: Ensembl stable ID (e.g., "ENSG00000157764")
    - all_levels: include references for linked features
    - db_type: e.g., "core"
    - external_db: e.g., "HGNC"
    - object_type: e.g., "gene" or "transcript"
    - species: e.g., "homo_sapiens"
    """
    url = f"{BASE_URL}/xrefs/id/{id}"
    params: Dict[str, Any] = {}
    if all_levels is not None:
        params["all_levels"] = "1" if all_levels else "0"
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if external_db:
        params["external_db"] = external_db
    if object_type:
        params["object_type"] = object_type
    if species:
        params["species"] = species
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_xrefs_by_id(result)
    return result


def lookup_xref_name(
    name: str,
    species: str,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    external_db: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    """Lookup by external reference primary accession or display label.

    - species: e.g., "human" or "homo_sapiens"
    - name: e.g., "BRCA2"
    - db_type: e.g., "core"
    - external_db: e.g., "HGNC"
    """
    url = f"{BASE_URL}/xrefs/name/{species}/{name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if external_db:
        params["external_db"] = external_db
    return _get_json(url, params, return_response=return_response)


