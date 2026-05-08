import os
import requests
from typing import Any, Dict, Optional, Union


ESUMMARY_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


def esummary(
    *,
    db: Optional[str] = None,
    id: Optional[Union[str, int]] = None,
    query_key: Optional[int] = None,
    WebEnv: Optional[str] = None,
    retstart: Optional[int] = None,
    retmax: Optional[int] = None,
    retmode: Optional[str] = None,
    version: Optional[str] = None,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 60.0,
) -> Any:
    """
    Call NCBI ESummary to retrieve document summaries (DocSums).

    Either provide a UID list via `id`, or a history reference via both
    `query_key` and `WebEnv`.
    """
    # Basic validation of mutually exclusive inputs
    if id is None and not (query_key is not None and WebEnv is not None):
        raise ValueError(
            "ESummary requires either 'id' or both 'query_key' and 'WebEnv'."
        )

    params: Dict[str, Any] = {}
    if db is not None:
        params["db"] = db
    if id is not None:
        params["id"] = str(id)
    if query_key is not None:
        params["query_key"] = str(query_key)
    if WebEnv is not None:
        params["WebEnv"] = WebEnv
    if retstart is not None:
        params["retstart"] = str(retstart)
    if retmax is not None:
        params["retmax"] = str(retmax)
    if retmode is not None:
        params["retmode"] = retmode
    if version is not None:
        params["version"] = version

    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key

    headers: Dict[str, str] = {}
    if isinstance(retmode, str) and retmode.lower() == "json":
        headers["Accept"] = "application/json"
    else:
        headers["Accept"] = "application/xml, text/xml;q=0.9, */*;q=0.1"

    response = requests.get(ESUMMARY_URL, headers=headers, params=params, timeout=timeout)
    if return_response:
        return response
    if headers.get("Accept") == "application/json":
        try:
            return response.json()
        except Exception:
            return response.text
    return response.text


__all__ = ["esummary"]



