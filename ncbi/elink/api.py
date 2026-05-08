import os
import time
import requests
from typing import Any, Dict, Optional
import sys
import os

# Import postprocess from the same directory
from .postprocess import postprocess_elink

ELINK_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"


def elink(
    *,
    dbfrom: str,
    db: Optional[str] = None,
    cmd: str = "neighbor",
    id: Optional[str] = None,
    query_key: Optional[int] = None,
    WebEnv: Optional[str] = None,
    idtype: Optional[str] = None,
    linkname: Optional[str] = None,
    term: Optional[str] = None,
    holding: Optional[str] = None,
    datetype: Optional[str] = None,
    reldate: Optional[int] = None,
    mindate: Optional[str] = None,
    maxdate: Optional[str] = None,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 300.0,
    postprocess: bool = True,
) -> Any:
    params: Dict[str, Any] = {
        "dbfrom": dbfrom,
        "cmd": cmd,
        "retmode": "json",
    }
    if db is not None:
        params["db"] = db
    if id is not None:
        params["id"] = id
    if query_key is not None:
        params["query_key"] = str(query_key)
    if WebEnv is not None:
        params["WebEnv"] = WebEnv
    if idtype is not None:
        params["idtype"] = idtype
    if linkname is not None:
        params["linkname"] = linkname
    if term is not None:
        params["term"] = term
    if holding is not None:
        params["holding"] = holding
    if datetype is not None:
        params["datetype"] = datetype
    if reldate is not None:
        params["reldate"] = str(reldate)
    if mindate is not None:
        params["mindate"] = mindate
    if maxdate is not None:
        params["maxdate"] = maxdate
    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key

    headers = {"accept": "application/json"}
    response = requests.get(ELINK_URL, headers=headers, params=params, timeout=timeout)

    if return_response:
        return response
    try:
        result = response.json()
        if postprocess:
            return postprocess_elink(result)
        else:
            return result
    except Exception:
        return response.text


__all__ = ["elink"]
