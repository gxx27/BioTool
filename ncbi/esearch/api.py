import os
import requests
from typing import Any, Dict, Optional, Union


ESEARCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"


def esearch(
    db: str,
    term: str,
    *,
    usehistory: Optional[str] = None,
    WebEnv: Optional[str] = None,
    query_key: Optional[int] = None,
    retstart: Optional[int] = None,
    retmax: Optional[int] = None,
    rettype: Optional[str] = None,
    sort: Optional[str] = None,
    field: Optional[str] = None,
    idtype: Optional[str] = None,
    datetype: Optional[str] = None,
    reldate: Optional[int] = None,
    mindate: Optional[str] = None,
    maxdate: Optional[str] = None,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 30.0,
) -> Any:
    params: Dict[str, Any] = {
        "db": db,
        "term": term,
        "retmode": "json",
    }
    if usehistory is not None:
        params["usehistory"] = usehistory
    if WebEnv is not None:
        params["WebEnv"] = WebEnv
    if query_key is not None:
        params["query_key"] = str(query_key)
    if retstart is not None:
        params["retstart"] = str(retstart)
    if retmax is not None:
        params["retmax"] = str(retmax)
    if rettype is not None:
        params["rettype"] = rettype
    if sort is not None:
        params["sort"] = sort
    if field is not None:
        params["field"] = field
    if idtype is not None:
        params["idtype"] = idtype
    if datetype is not None:
        params["datetype"] = datetype
    if reldate is not None:
        params["reldate"] = str(reldate)
    if mindate is not None:
        params["mindate"] = mindate
    if maxdate is not None:
        params["maxdate"] = maxdate

    # Prefer explicit api_key argument; otherwise read from environment
    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key

    headers = {"accept": "application/json"}
    response = requests.get(ESEARCH_URL, headers=headers, params=params, timeout=timeout)
    if return_response:
        return response
    try:
        return response.json()
    except Exception:
        return response.text


__all__ = ["esearch"]


