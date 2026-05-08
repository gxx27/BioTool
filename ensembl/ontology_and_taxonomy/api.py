import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import postprocess_get_taxonomy_classification, postprocess_get_taxonomy_name, postprocess_ontology_ancestors

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


# Ontology endpoints
def get_ontology_ancestors(
    id: str,
    callback: Optional[str] = None,
    ontology: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/ontology/ancestors/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if ontology:
        params["ontology"] = ontology
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_ontology_ancestors(result)
    else:
        return result


def get_ontology_ancestors_chart(
    id: str,
    callback: Optional[str] = None,
    ontology: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/ontology/ancestors/chart/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if ontology:
        params["ontology"] = ontology
    return _get_json(url, params, return_response=return_response)


def get_ontology_descendants(
    id: str,
    callback: Optional[str] = None,
    closest_term: Optional[bool] = None,
    ontology: Optional[str] = None,
    subset: Optional[str] = None,
    zero_distance: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/ontology/descendants/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if closest_term is not None:
        params["closest_term"] = _to_bool01(closest_term)
    if ontology:
        params["ontology"] = ontology
    if subset:
        params["subset"] = subset
    if zero_distance is not None:
        params["zero_distance"] = _to_bool01(zero_distance)
    return _get_json(url, params, return_response=return_response)


def get_ontology_id(
    id: str,
    callback: Optional[str] = None,
    relation: Optional[str] = None,
    simple: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/ontology/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if relation:
        params["relation"] = relation
    if simple is not None:
        params["simple"] = _to_bool01(simple)
    return _get_json(url, params, return_response=return_response)


def get_ontology_name(
    name: str,
    callback: Optional[str] = None,
    ontology: Optional[str] = None,
    relation: Optional[str] = None,
    simple: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/ontology/name/{name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if ontology:
        params["ontology"] = ontology
    if relation:
        params["relation"] = relation
    if simple is not None:
        params["simple"] = _to_bool01(simple)
    return _get_json(url, params, return_response=return_response)


# Taxonomy endpoints
def get_taxonomy_classification(
    id: str,
    callback: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/taxonomy/classification/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = postprocess_get_taxonomy_classification(result)
    return result


def get_taxonomy_id(
    id: str,
    callback: Optional[str] = None,
    simple: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/taxonomy/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if simple is not None:
        params["simple"] = _to_bool01(simple)
    return _get_json(url, params, return_response=return_response)


def get_taxonomy_name(
    name: str,
    callback: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/taxonomy/name/{name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_get_taxonomy_name(result)
    else:
        return result


