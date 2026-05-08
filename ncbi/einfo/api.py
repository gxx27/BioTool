import os
import requests
from typing import Any, Dict, Optional


EINFO_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/einfo.fcgi"


def einfo(
    *,
    db: Optional[str] = None,
    version: Optional[str] = None,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 30.0,
) -> Any:
    params: Dict[str, Any] = {"retmode": "json"}
    if db is not None:
        params["db"] = db
    if version is not None:
        params["version"] = version
    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key
    headers = {"accept": "application/json"}
    response = requests.get(EINFO_URL, headers=headers, params=params, timeout=timeout)
    if return_response:
        return response
    try:
        return response.json()
    except Exception:
        return response.text


__all__ = ["einfo"]


