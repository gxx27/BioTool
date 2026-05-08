import time
import requests
from typing import Any, Dict, Optional, Tuple, Union

from .postprocess import (
    postprocess_blast_submit,
    decode_blast_response,
    should_retry_blast_retrieve,
    summarize_blast,
)

BLAST_URL = "https://blast.ncbi.nlm.nih.gov/Blast.cgi"


def _post(url: str,
          data: Dict[str, Any],
          *,
          accept_json: bool = False,
          timeout: Optional[float] = 60.0) -> Any:
    headers: Dict[str, str] = {}
    if accept_json:
        headers["accept"] = "application/json"
    response = requests.post(url, headers=headers, data=data, timeout=timeout)
    response.raise_for_status()
    return response.text


def _get(url: str,
         params: Dict[str, Any],
         *,
         accept_json: bool = False,
         return_response: bool = False,
         timeout: Optional[float] = 60.0) -> Any:
    headers: Dict[str, str] = {}
    if accept_json:
        headers["accept"] = "application/json"
    response = requests.get(url, headers=headers, params=params, timeout=timeout)
    response.raise_for_status()
    if return_response:
        return response
    return decode_blast_response(response, accept_json=accept_json)


_MIN_WAIT_SECONDS: float = 1.0
_BACKOFF_FACTOR: float = 2.0
_MAX_ATTEMPTS: int = 6
_MAX_WAIT_SECONDS: float = 120.0


def _coerce_wait_seconds(rtoe: Union[int, float, str, None]) -> float:
    try:
        seconds = float(rtoe)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return _MIN_WAIT_SECONDS
    return max(seconds, _MIN_WAIT_SECONDS)


def blast(
    query: str,
    database: str,
    program: str = "blastn",
    *,
    FILTER: Optional[str] = None,
    EXPECT: Optional[Union[float, str]] = None,
    WORD_SIZE: Optional[int] = None,
    GAPCOSTS: Optional[str] = None,
    MATRIX: Optional[str] = None,
    COMPOSITION_BASED_STATISTICS: Optional[int] = None,
    HITLIST_SIZE: Optional[int] = None,
    SHORT_QUERY_ADJUST: Optional[str] = None,
    FORMAT_TYPE: Optional[str] = None,
    DESCRIPTIONS: Optional[int] = None,
    ALIGNMENTS: Optional[int] = None,
    NCBI_GI: Optional[str] = None,
    timeout: Optional[float] = 60.0,
    postprocess: bool = True,
) -> Any:
    data: Dict[str, Any] = {
        "CMD": "Put",
        "QUERY": query,
        "DATABASE": database,
        "PROGRAM": program,
    }
    if FILTER is not None:
        data["FILTER"] = FILTER
    if EXPECT is not None:
        data["EXPECT"] = EXPECT
    if WORD_SIZE is not None:
        data["WORD_SIZE"] = str(WORD_SIZE)
    if GAPCOSTS is not None:
        data["GAPCOSTS"] = GAPCOSTS
    if MATRIX is not None:
        data["MATRIX"] = MATRIX
    if COMPOSITION_BASED_STATISTICS is not None:
        data["COMPOSITION_BASED_STATISTICS"] = str(COMPOSITION_BASED_STATISTICS)
    if HITLIST_SIZE is not None:
        data["HITLIST_SIZE"] = str(HITLIST_SIZE)
    if SHORT_QUERY_ADJUST is not None:
        data["SHORT_QUERY_ADJUST"] = SHORT_QUERY_ADJUST
    if FORMAT_TYPE is not None:
        data["FORMAT_TYPE"] = FORMAT_TYPE
    if DESCRIPTIONS is not None:
        data["DESCRIPTIONS"] = str(DESCRIPTIONS)
    if ALIGNMENTS is not None:
        data["ALIGNMENTS"] = str(ALIGNMENTS)
    if NCBI_GI is not None:
        data["NCBI_GI"] = NCBI_GI

    accept_json = isinstance(FORMAT_TYPE, str) and ("json" in FORMAT_TYPE.lower())
    result = _post(BLAST_URL, data, accept_json=accept_json, timeout=timeout)
    if postprocess:
        submit_info = postprocess_blast_submit(result)
        rid = submit_info["rid"]
        rtoe = submit_info["rtoe"]
        wait_seconds = _coerce_wait_seconds(rtoe)

        retrieve_kwargs: Dict[str, Any] = {}
        if FORMAT_TYPE is not None:
            retrieve_kwargs["FORMAT_TYPE"] = FORMAT_TYPE
        if DESCRIPTIONS is not None:
            retrieve_kwargs["DESCRIPTIONS"] = DESCRIPTIONS
        if ALIGNMENTS is not None:
            retrieve_kwargs["ALIGNMENTS"] = ALIGNMENTS
        if NCBI_GI is not None:
            retrieve_kwargs["NCBI_GI"] = NCBI_GI

        attempts = 0
        current_wait = wait_seconds
        while True:
            time.sleep(current_wait)
            attempts += 1
            retrieve_result = blast_retrieve(rid, timeout=timeout, **retrieve_kwargs)
            retry, error_message = should_retry_blast_retrieve(retrieve_result)
            if not retry:
                if error_message:
                    raise RuntimeError(error_message)
                return summarize_blast(retrieve_result)

            if attempts >= _MAX_ATTEMPTS:
                raise TimeoutError(
                    f"BLAST retrieve timed out for RID {rid} after {attempts} attempts."
                )

            current_wait = min(current_wait * _BACKOFF_FACTOR, _MAX_WAIT_SECONDS)
            wait_seconds = current_wait

    return result


def blast_retrieve(
    rid: str,
    *,
    FORMAT_TYPE: Optional[str] = None,
    DESCRIPTIONS: Optional[int] = None,
    ALIGNMENTS: Optional[int] = None,
    NCBI_GI: Optional[str] = None,
    return_response: bool = False,
    timeout: Optional[float] = 60.0,
) -> Any:
    params: Dict[str, Any] = {
        "CMD": "Get",
        "RID": rid,
    }
    if FORMAT_TYPE is not None:
        params["FORMAT_TYPE"] = FORMAT_TYPE
    if DESCRIPTIONS is not None:
        params["DESCRIPTIONS"] = str(DESCRIPTIONS)
    if ALIGNMENTS is not None:
        params["ALIGNMENTS"] = str(ALIGNMENTS)
    if NCBI_GI is not None:
        params["NCBI_GI"] = NCBI_GI

    accept_json = isinstance(FORMAT_TYPE, str) and ("json" in FORMAT_TYPE.lower())
    return _get(BLAST_URL, params, accept_json=accept_json, return_response=return_response, timeout=timeout)

__all__ = ["blast", "blast_retrieve"]


