import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import post_process_accession, post_process_gene, post_process_term, post_process_region

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


def get_phenotype_by_accession(
    accession: str,
    species: str,
    callback: Optional[str] = None,
    include_children: Optional[bool] = None,
    include_pubmed_id: Optional[bool] = None,
    include_review_status: Optional[bool] = None,
    source: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/phenotype/accession/{species}/{accession}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if include_children is not None:
        params["include_children"] = _to_bool01(include_children)
    if include_pubmed_id is not None:
        params["include_pubmed_id"] = _to_bool01(include_pubmed_id)
    if include_review_status is not None:
        params["include_review_status"] = _to_bool01(include_review_status)
    if source:
        params["source"] = source
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = post_process_accession(result)
    return result


def get_phenotype_by_gene(
    gene: str,
    species: str,
    callback: Optional[str] = None,
    include_associated: Optional[bool] = None,
    include_overlap: Optional[bool] = None,
    include_pubmed_id: Optional[bool] = None,
    include_review_status: Optional[bool] = None,
    include_submitter: Optional[bool] = None,
    non_specified: Optional[bool] = None,
    trait: Optional[bool] = None,
    tumour: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/phenotype/gene/{species}/{gene}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if include_associated is not None:
        params["include_associated"] = _to_bool01(include_associated)
    if include_overlap is not None:
        params["include_overlap"] = _to_bool01(include_overlap)
    if include_pubmed_id is not None:
        params["include_pubmed_id"] = _to_bool01(include_pubmed_id)
    if include_review_status is not None:
        params["include_review_status"] = _to_bool01(include_review_status)
    if include_submitter is not None:
        params["include_submitter"] = _to_bool01(include_submitter)
    if non_specified is not None:
        params["non_specified"] = _to_bool01(non_specified)
    if trait is not None:
        params["trait"] = _to_bool01(trait)
    if tumour is not None:
        params["tumour"] = _to_bool01(tumour)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = post_process_gene(result)
    return result


def get_phenotype_by_region(
    region: str,
    species: str,
    callback: Optional[str] = None,
    feature_type: Optional[str] = None,
    include_pubmed_id: Optional[bool] = None,
    include_review_status: Optional[bool] = None,
    include_submitter: Optional[bool] = None,
    non_specified: Optional[bool] = None,
    only_phenotypes: Optional[bool] = None,
    trait: Optional[bool] = None,
    tumour: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/phenotype/region/{species}/{region}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if feature_type:
        params["feature_type"] = feature_type
    if include_pubmed_id is not None:
        params["include_pubmed_id"] = _to_bool01(include_pubmed_id)
    if include_review_status is not None:
        params["include_review_status"] = _to_bool01(include_review_status)
    if include_submitter is not None:
        params["include_submitter"] = _to_bool01(include_submitter)
    if non_specified is not None:
        params["non_specified"] = _to_bool01(non_specified)
    if only_phenotypes is not None:
        params["only_phenotypes"] = _to_bool01(only_phenotypes)
    if trait is not None:
        params["trait"] = _to_bool01(trait)
    if tumour is not None:
        params["tumour"] = _to_bool01(tumour)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = post_process_region(result)
    return result


def get_phenotype_by_term(
    species: str,
    term: str,
    callback: Optional[str] = None,
    include_children: Optional[bool] = None,
    include_pubmed_id: Optional[bool] = None,
    include_review_status: Optional[bool] = None,
    source: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/phenotype/term/{species}/{term}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if include_children is not None:
        params["include_children"] = _to_bool01(include_children)
    if include_pubmed_id is not None:
        params["include_pubmed_id"] = _to_bool01(include_pubmed_id)
    if include_review_status is not None:
        params["include_review_status"] = _to_bool01(include_review_status)
    if source:
        params["source"] = source
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = post_process_term(result)
    return result


