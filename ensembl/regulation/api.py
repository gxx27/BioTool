import requests
from typing import Any, Dict, Optional


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


def get_binding_matrix(
    binding_matrix: str,
    species: str,
    callback: Optional[str] = None,
    unit: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    """Return the specified binding matrix.

    - species: e.g., "homo_sapiens"
    - binding_matrix_stable_id: stable ID of the binding matrix
    - unit: unit of the matrix elements
    """
    url = f"{BASE_URL}/species/{species}/binding_matrix/{binding_matrix}/"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if unit:
        params["unit"] = unit
    return _get_json(url, params, return_response=return_response)


