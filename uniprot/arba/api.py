import requests
import json
from typing import Any, Dict, Optional, Union, List
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_search_arba, postprocess_stream_arba

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


def get_arba_by_id(arbaId: str, fields: Optional[FieldList] = None, return_response: bool = False) -> Any:
    """Get ARBA entry by ARBA ID.

    - arba_id: e.g., "ARBA00000063"
    - fields: list or comma-separated string
    """
    url = f"https://rest.uniprot.org/arba/{arbaId}"
    params: Dict[str, Any] = {}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    return _get_json(url, params, return_response=return_response)


def stream_arba(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    download: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Stream ARBA search results for a query.

    - query: search criteria
    - sort: e.g., "rule_id asc"
    - fields: list or comma-separated string
    - download: if True/False, converted to "true"/"false"
    """
    url = "https://rest.uniprot.org/arba/search"
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
        return postprocess_stream_arba(result)
    else:
        return result


def search_arba(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    size: Optional[int] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Paginated ARBA search.

    - query: search criteria
    - sort: optional sort field
    - fields: list or comma-separated string
    - size: page size (max 500)
    """
    url = "https://rest.uniprot.org/arba/search"
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
        return postprocess_search_arba(result)
    else:
        return result
