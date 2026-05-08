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

def get_archive_id(id: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    """Use the given id to return its latest version.

    - id: Ensembl stable ID (e.g., "ENSG00000157764")
    - callback: JSONP callback name (only for JSONP)
    """
    url = f"{BASE_URL}/archive/id/{id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response)


