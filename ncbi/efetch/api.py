import os
import requests
from typing import Any, Dict, Optional, Union

# Import postprocess from the same directory
from .postprocess import postprocess_efetch

EFETCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def efetch(
    *,
    db: Optional[str] = None,
    id: Optional[Union[str, int]] = None,
    query_key: Optional[int] = None,
    WebEnv: Optional[str] = None,
    retmode: Optional[str] = "xml",
    rettype: Optional[str] = None,
    retstart: Optional[int] = None,
    retmax: Optional[int] = None,
    strand: Optional[int] = None,
    seq_start: Optional[int] = None,
    seq_stop: Optional[int] = None,
    complexity: Optional[int] = None,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 60.0,
    postprocess: bool = True,
) -> Any:
    params: Dict[str, Any] = {}
    if db is not None:
        params["db"] = db
    if id is not None:
        params["id"] = str(id)
    if query_key is not None:
        params["query_key"] = str(query_key)
    if WebEnv is not None:
        params["WebEnv"] = WebEnv
    if retmode is not None:
        params["retmode"] = retmode
    if rettype is not None:
        params["rettype"] = rettype
    if retstart is not None:
        params["retstart"] = str(retstart)
    if retmax is not None:
        params["retmax"] = str(retmax)
    if strand is not None:
        params["strand"] = str(strand)
    if seq_start is not None:
        params["seq_start"] = str(seq_start)
    if seq_stop is not None:
        params["seq_stop"] = str(seq_stop)
    if complexity is not None:
        params["complexity"] = str(complexity)

    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key

    headers: Dict[str, str] = {}
    if isinstance(retmode, str) and retmode.lower() == "json":
        headers["accept"] = "application/json"

    response = requests.get(EFETCH_URL, headers=headers, params=params, timeout=timeout)
    if return_response:
        return response

    if postprocess:
        return postprocess_efetch(response.text)
    else:
        return response.text


__all__ = ["efetch"]


