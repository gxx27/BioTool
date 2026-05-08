import requests
import json
from typing import Any, Dict, Optional, Union, List
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_search_taxonomy, postprocess_stream_taxonomy

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


def get_taxonomy_by_id(taxonId: str, fields: Optional[FieldList] = None, return_response: bool = False) -> Any:
    url = f"https://rest.uniprot.org/taxonomy/{taxonId}"
    params: Dict[str, Any] = {}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    return _get_json(url, params, return_response=return_response)


def stream_taxonomy(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    download: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/taxonomy/stream"
    params: Dict[str, Any] = {"query": query}
    if sort:
        params["sort"] = sort
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    bool_download = _to_bool_str(download)
    if bool_download is not None:
        params["download"] = bool_download
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_stream_taxonomy(result)
    else:
        return result


def search_taxonomy(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    size: Optional[int] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/taxonomy/search"
    params: Dict[str, Any] = {"query": query}
    if sort:
        params["sort"] = sort
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    if size is not None:
        params["size"] = str(size)
    else:
        params["size"] = "25"
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_search_taxonomy(result)
    else:
        return result
