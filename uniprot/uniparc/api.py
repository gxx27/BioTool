import requests
import json
from typing import Any, Dict, Optional, Union, List
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_stream_uniparc, postprocess_search_uniparc, postprocess_get_uniparc_by_upi

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


def get_uniparc_by_upi(
    upi: str,
    fields: Optional[FieldList] = None,
    dbTypes: Optional[FieldList] = None,
    active: Optional[bool] = None,
    taxonIds: Optional[FieldList] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/uniparc/%7Bupi%7D"
    params: Dict[str, Any] = {"upi": upi}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    if dbTypes:
        params["dbTypes"] = dbTypes
    bool_active = _to_bool_str(active)
    if bool_active is not None:
        params["active"] = bool_active
    if taxonIds:
        params["taxonIds"] = taxonIds
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_get_uniparc_by_upi(result)
    else:
        return result


def get_uniparc_light(upi: str, fields: Optional[FieldList] = None, return_response: bool = False) -> Any:
    url = f"https://rest.uniprot.org/uniparc/{upi}/light"
    params: Dict[str, Any] = {}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    return _get_json(url, params, return_response=return_response)


def get_uniparc_databases(
    upi: str,
    fields: Optional[FieldList] = None,
    id: Optional[str] = None, # db id
    dbTypes: Optional[FieldList] = None,
    active: Optional[bool] = None,
    taxonIds: Optional[FieldList] = None,
    size: Optional[int] = None,
    return_response: bool = False,
) -> Any:
    url = f"https://rest.uniprot.org/uniparc/{upi}/databases"
    params: Dict[str, Any] = {}
    csv_fields = _to_csv(fields)
    if csv_fields:
        params["fields"] = csv_fields
    if id is not None:
        params["id"] = id
    csv_db_types = _to_csv(dbTypes)
    if csv_db_types:
        params["dbTypes"] = csv_db_types
    bool_active = _to_bool_str(active)
    if bool_active is not None:
        params["active"] = bool_active
    if taxonIds:
        params["taxonIds"] = taxonIds
    if size is not None:
        params["size"] = str(size)
    else:
        params["size"] = "3"
    return _get_json(url, params, return_response=return_response)


def stream_uniparc(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    download: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/uniparc/search"
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
        return postprocess_stream_uniparc(result)
    else:
        return result


def search_uniparc(
    query: str,
    sort: Optional[str] = None,
    fields: Optional[FieldList] = None,
    size: Optional[int] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = "https://rest.uniprot.org/uniparc/search"
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
        return postprocess_search_uniparc(result)
    else:
        return result
