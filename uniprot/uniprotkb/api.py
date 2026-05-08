import requests
import json
from typing import Any, Dict, Optional, Union, List
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_stream_uniprotkb, postprocess_search_uniprotkb, postprocess_get_uniprotkb_entry

# ---------------------------------------------------------------------------
FieldList = Union[str, List[str]]


def _to_csv(value: Optional[FieldList]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value.split(",")
    return value


def _to_bool_str(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "true" if value else "false"


def _get_json(url: str, params: Dict[str, Any], return_response: bool = False) -> Any:
    headers = {"accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)

    if return_response:
        return response
    else:
        try:
            return response.json()
        except Exception:
            return response.text


def get_uniprotkb_entry(
    accession: str, 
    fields: Optional[FieldList] = None, 
    return_response: bool = False, 
    postprocess: bool = True,
) -> Any:
    url = f"https://rest.uniprot.org/uniprotkb/{accession}"
    params: Dict[str, Any] = {}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_get_uniprotkb_entry(result)
    else:
        return result


def stream_uniprotkb(
    query: str,
    fields: Optional[FieldList] = None,
    sort: Optional[str] = None,
    includeIsoform: Optional[bool] = None,
    download: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/uniprotkb/search"
    params: Dict[str, Any] = {"query": query}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    if sort:
        params["sort"] = sort
    bool_iso = _to_bool_str(includeIsoform)
    if bool_iso is not None:
        params["includeIsoform"] = bool_iso
    bool_download = _to_bool_str(download)
    if bool_download is not None:
        params["download"] = bool_download
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_stream_uniprotkb(result)
    else:
        return result


def search_uniprotkb(
    query: str,
    fields: Optional[FieldList] = None,
    sort: Optional[str] = None,
    includeIsoform: Optional[bool] = None,
    size: Optional[int] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/uniprotkb/search"
    params: Dict[str, Any] = {"query": query}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    if sort:
        params["sort"] = sort
    bool_iso = _to_bool_str(includeIsoform)
    if bool_iso is not None:
        params["includeIsoform"] = bool_iso
    if size is not None:
        params["size"] = str(size)
    else:
        params["size"] = "25"
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_search_uniprotkb(result)
    else:
        return result
