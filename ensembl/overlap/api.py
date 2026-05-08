import requests
from typing import Any, Dict, Optional, Sequence
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_overlap_translation, postprocess_overlap_id

BASE_URL = "https://rest.ensembl.org"


def _to_bool01(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "1" if value else "0"


def _as_multi(params: Dict[str, Any], key: str, values: Optional[Sequence[str]]) -> None:
    if values:
        params[key] = values


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


def overlap_by_id(
    feature: Sequence[str] | str,
    id: str,
    biotype: Optional[str] = None,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    logic_name: Optional[str] = None,
    misc_set: Optional[str] = None,
    object_type: Optional[str] = None,
    so_term: Optional[str] = None,
    species: Optional[str] = None,
    species_set: Optional[str] = None,
    variant_set: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Retrieve overlapping features by stable ID.

    - feature: one or many of Enum(band, gene, transcript, cds, exon, repeat, simple, misc, variation, somatic_variation, structural_variation, somatic_structural_variation, constrained, regulatory, motif, mane)
    """
    url = f"{BASE_URL}/overlap/id/{id}"
    params: Dict[str, Any] = {}
    if isinstance(feature, str):
        params["feature"] = feature
    else:
        _as_multi(params, "feature", list(feature))
    if biotype:
        params["biotype"] = biotype
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if logic_name:
        params["logic_name"] = logic_name
    if misc_set:
        params["misc_set"] = misc_set
    if object_type:
        params["object_type"] = object_type
    if so_term:
        params["so_term"] = so_term
    if species:
        params["species"] = species
    if species_set:
        params["species_set"] = species_set
    if variant_set:
        params["variant_set"] = variant_set
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_overlap_id(result)
    else:
        return result


def overlap_by_region(
    feature: Sequence[str] | str, # Enum(band, gene, transcript, cds, exon, repeat, simple, misc, variation, somatic_variation, structural_variation, somatic_structural_variation, constrained, regulatory, motif, mane)
    region: str,
    species: str,
    biotype: Optional[str] = None,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    logic_name: Optional[str] = None,
    misc_set: Optional[str] = None,
    so_term: Optional[str] = None,
    species_set: Optional[str] = None,
    trim_downstream: Optional[bool] = None,
    trim_upstream: Optional[bool] = None,
    variant_set: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    """Retrieve overlapping features for a region like '7:140424943-140624564'."""
    url = f"{BASE_URL}/overlap/region/{species}/{region}"
    params: Dict[str, Any] = {}
    if isinstance(feature, str):
        params["feature"] = feature
    else:
        _as_multi(params, "feature", list(feature))
    if biotype:
        params["biotype"] = biotype
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if logic_name:
        params["logic_name"] = logic_name
    if misc_set:
        params["misc_set"] = misc_set
    if so_term:
        params["so_term"] = so_term
    if species_set:
        params["species_set"] = species_set
    if trim_downstream is not None:
        params["trim_downstream"] = _to_bool01(trim_downstream)
    if trim_upstream is not None:
        params["trim_upstream"] = _to_bool01(trim_upstream)
    if variant_set:
        params["variant_set"] = variant_set
    return _get_json(url, params, return_response=return_response)


def overlap_translation(
    id: str,
    callback: Optional[str] = None,
    db_type: Optional[str] = None,
    feature: Optional[str] = None,
    so_term: Optional[str] = None,
    species: Optional[str] = None,
    type_: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """Retrieve features related to a specific translation ID (e.g. domains)."""
    url = f"{BASE_URL}/overlap/translation/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if db_type:
        params["db_type"] = db_type
    if feature:
        params["feature"] = feature
    if so_term:
        params["so_term"] = so_term
    if species:
        params["species"] = species
    if type_:
        params["type"] = type_
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        return postprocess_overlap_translation(result)
    else:
        return result


