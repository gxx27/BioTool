import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import post_process_query_beacon

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


def get_beacon(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/beacon"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_query_beacon(
    alternateBases: str,
    assemblyId: str,
    referenceBases: str,
    referenceName: str,
    start: int,
    end: Optional[int] = None,
    variantType: Optional[str] = None,
    callback: Optional[str] = None,
    dataset_ids: Optional[str] = None,
    includeResultsetResponses: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Beacon allele query. Either alternate_bases or variantType is required.

    - include_resultset_responses: one of ALL, HIT, MISS, NONE
    - dataset_ids: identifiers of datasets (comma-separated)
    """
    url = f"{BASE_URL}/ga4gh/beacon/query"
    params: Dict[str, Any] = {
        "assemblyId": assemblyId,
        "referenceName": referenceName,
        "start": start,
        "referenceBases": referenceBases,
    }
    if end:
        params["end"] = end
    if alternateBases:
        params["alternateBases"] = alternateBases
    if variantType:
        params["variantType"] = variantType
    assert alternateBases or variantType, "Either alternateBases or variantType is required"

    if callback:
        params["callback"] = callback
    if dataset_ids:
        params["datasetIds"] = dataset_ids
    if includeResultsetResponses:
        params["includeResultsetResponses"] = includeResultsetResponses
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = post_process_query_beacon(result)
    return result


def get_ga4gh_features(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/features/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_callsets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/callsets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_datasets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/datasets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_featuresets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/featuresets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_variants(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/variants/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_variantsets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/variantsets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_references(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/references/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_referencesets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/referencesets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_ga4gh_variantannotationsets(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/ga4gh/variantannotationsets/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


