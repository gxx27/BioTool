import os
import requests
from typing import Any, Dict, Optional


ECITMATCH_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/ecitmatch.cgi"


def ecitmatch(
    bdata: str,
    *,
    db: str = "pubmed",
    retmode: str = "xml",
    # Backward-compatibility with older callers that passed `rettype="xml"`
    rettype: Optional[str] = None,
    normalize_separators: bool = True,
    api_key: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 30.0,
) -> Any:
    # Normalize "%0D"/"%0A" to actual line breaks to avoid double-encoding by requests
    if normalize_separators and bdata:
        bdata = (
            bdata.replace("%0D", "\r").replace("%0A", "\n")
        )

    # If caller mistakenly used rettype to pass xml, map it to retmode
    if rettype and not retmode:
        retmode = rettype

    params: Dict[str, Any] = {
        "db": db,
        "retmode": retmode,
        "bdata": bdata,
    }
    if api_key is None:
        api_key = os.getenv("NCBI_API_KEY") or os.getenv("NCBI_EUTILS_API_KEY")
    if api_key:
        params["api_key"] = api_key

    headers = {"Accept": "application/xml, text/xml;q=0.9, */*;q=0.1"}

    response = requests.get(ECITMATCH_URL, params=params, headers=headers, timeout=timeout)
    if return_response:
        return response
    return response.text


__all__ = ["ecitmatch"]


