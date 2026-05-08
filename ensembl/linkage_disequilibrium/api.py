import requests
from typing import Any, Dict, Optional
import sys
import os

# Import postprocess from the same directory
from .postprocess import ld_region_postprocess

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


def get_ld_around_variant(
    id: str,
    population_name: str,
    species: str,
    attribs: Optional[bool] = None,
    callback: Optional[str] = None,
    d_prime: Optional[float] = None,
    r2: Optional[float] = None,
    window_size: Optional[int] = None,
    return_response: bool = False,
) -> Any:
    """LD values between a variant and others in a window centered on it."""
    url = f"{BASE_URL}/ld/{species}/{id}/{population_name}"
    params: Dict[str, Any] = {}
    if attribs is not None:
        params["attribs"] = _to_bool01(attribs)
    if callback:
        params["callback"] = callback
    if d_prime is not None:
        params["d_prime"] = d_prime
    if r2 is not None:
        params["r2"] = r2
    if window_size is not None:
        params["window_size"] = window_size
    return _get_json(url, params, return_response=return_response)


def get_ld_pairwise(
    id1: str,
    id2: str,
    species: str,
    callback: Optional[str] = None,
    d_prime: Optional[float] = None,
    population_name: Optional[str] = None,
    r2: Optional[float] = None,
    return_response: bool = False,
) -> Any:
    """LD values between two variants, optionally for a population."""
    url = f"{BASE_URL}/ld/{species}/pairwise/{id1}/{id2}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if d_prime is not None:
        params["d_prime"] = d_prime
    if population_name:
        params["population_name"] = population_name
    if r2 is not None:
        params["r2"] = r2
    return _get_json(url, params, return_response=return_response)


def get_ld_region(
    population_name: str,
    region: str,
    species: str,
    callback: Optional[str] = None,
    d_prime: Optional[float] = None,
    r2: Optional[float] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    """LD values between all variant pairs in a region for a population."""
    url = f"{BASE_URL}/ld/{species}/region/{region}/{population_name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if d_prime is not None:
        params["d_prime"] = d_prime
    if r2 is not None:
        params["r2"] = r2
    
    results = _get_json(url, params, return_response=return_response)
    if postprocess:
        results = ld_region_postprocess(results)
    return results


