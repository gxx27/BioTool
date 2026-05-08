"""Helpers for parsing BLAST submit responses and retrieving results."""

import html
import io
import json
import re
import zipfile
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

_QBLAST_BLOCK_PATTERN = re.compile(
    r"<!--\s*QBlastInfoBegin(?P<body>.*?)QBlastInfoEnd\s*-->",
    re.IGNORECASE | re.DOTALL,
)

_KEY_VALUE_PATTERN = re.compile(r"^(?P<key>[A-Za-z0-9_]+)\s*=\s*(?P<value>\S+)")


def _parse_numeric(value: str) -> Union[int, float, str]:
    """Attempt to coerce `value` into int/float, otherwise return original string."""

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        return value


def postprocess_blast_submit(response_text: str) -> Dict[str, Union[str, int, float]]:
    """Extract RID and RTOE values from a BLAST submit HTML response.

    Parameters
    ----------
    response_text:
        The raw text returned by the BLAST `CMD=Put` request.

    Returns
    -------
    Dict[str, Union[str, int, float]]
        A dictionary containing the `rid` and `rtoe` values.  The `rtoe` value
        is converted to an ``int`` or ``float`` when possible.

    Raises
    ------
    ValueError
        If the BLAST info block or required fields are missing.
    """

    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Response text must be a non-empty string.")

    match = _QBLAST_BLOCK_PATTERN.search(response_text)
    if not match:
        raise ValueError("Unable to locate QBlastInfo block in response.")

    body = match.group("body") or ""
    values: Dict[str, Union[str, int, float]] = {}

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        key_match = _KEY_VALUE_PATTERN.match(line)
        if not key_match:
            continue
        key = key_match.group("key").upper()
        value = key_match.group("value")
        if key == "RTOE":
            values["rtoe"] = _parse_numeric(value)
        elif key == "RID":
            values["rid"] = value

    rid = values.get("rid")
    rtoe = values.get("rtoe")

    if rid is None:
        raise ValueError("RID not found in QBlastInfo block.")
    if rtoe is None:
        raise ValueError("RTOE not found in QBlastInfo block.")

    return {"rid": rid, "rtoe": rtoe}


def decode_blast_response(response: requests.Response, *, accept_json: bool) -> Any:
    """Decode a BLAST retrieve response into a Python object when possible."""

    if accept_json:
        try:
            return response.json()
        except ValueError:
            pass

    content = response.content
    if _looks_like_zip(content):
        parsed = _parse_zip_json(content)
        if parsed is not None:
            return parsed

    text = response.text
    if _looks_like_html(response, text):
        parsed_html = parse_blast_html_result(text)
        if parsed_html is not None:
            return parsed_html

    if accept_json:
        try:
            return json.loads(text)
        except ValueError:
            pass
    return text


def should_retry_blast_retrieve(result: Any) -> Tuple[bool, Optional[str]]:
    """Inspect a BLAST retrieve payload to determine whether to retry the request."""

    if isinstance(result, dict):
        status = result.get("status")
        if isinstance(status, str):
            status_upper = status.upper()
            if status_upper == "WAITING":
                return True, None
            if status_upper == "FAILED":
                message = result.get("message")
                message_text = message if isinstance(message, str) and message else None
                return False, message_text or "BLAST reported failure during retrieval."
        message = result.get("message")
        if isinstance(message, str):
            message_upper = message.upper()
            if "WAITING" in message_upper:
                return True, None
            if "FAILED" in message_upper or "ERROR" in message_upper:
                return False, message

    if isinstance(result, str):
        upper = result.upper()
        if "STATUS=WAITING" in upper:
            return True, None
        if "STATUS=FAILED" in upper or "ERROR" in upper:
            return False, "BLAST reported failure during retrieval."
    return False, None


def _looks_like_zip(content: bytes) -> bool:
    return content[:4] == b"PK\x03\x04"


def _looks_like_html(response: requests.Response, text: str) -> bool:
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" in content_type:
        return True
    stripped = text.lstrip()
    return stripped.startswith("<!DOCTYPE html") or stripped.startswith("<html")


def _parse_zip_json(content: bytes) -> Any:
    buffer = io.BytesIO(content)
    with zipfile.ZipFile(buffer) as zf:
        json_entries: Dict[str, Any] = {}
        other_entries: Dict[str, Any] = {}
        for name in zf.namelist():
            with zf.open(name) as entry:
                data = entry.read()
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                other_entries[name] = data
                continue
            try:
                json_entries[name] = json.loads(text)
            except json.JSONDecodeError:
                other_entries[name] = text

    if not json_entries:
        return {"files": other_entries} if other_entries else None

    manifest_candidates = [
        payload
        for payload in json_entries.values()
        if isinstance(payload, dict) and "BlastJSON" in payload
    ]

    reports = []
    for manifest in manifest_candidates:
        entries = manifest.get("BlastJSON") or []
        for entry in entries:
            filename = entry.get("File") if isinstance(entry, dict) else None
            if filename and filename in json_entries:
                reports.append(json_entries[filename])

    if reports:
        return reports[0] if len(reports) == 1 else reports

    if len(json_entries) == 1:
        return next(iter(json_entries.values()))

    combined = {**json_entries, **other_entries}
    return combined if combined else None


_HTML_STATUS_PATTERN = re.compile(
    r"QBlastInfoBegin\s*Status\s*=\s*(?P<status>[A-Za-z]+)", re.IGNORECASE
)

_HTML_HIT_ROW_PATTERN = re.compile(
    r'<tr[^>]*id="dtr_(?P<row_id>\d+)"[^>]*>(?P<body>.*?)</tr>',
    re.IGNORECASE | re.DOTALL,
)

_HTML_CELL_PATTERN = re.compile(r"<td[^>]*>(?P<content>.*?)</td>", re.IGNORECASE | re.DOTALL)


def parse_blast_html_result(html_text: str, *, max_hits: int = 50) -> Optional[Dict[str, Any]]:
    """Extract a lightweight summary from a BLAST HTML report."""

    if not isinstance(html_text, str):
        return None

    summary: Dict[str, Any] = {
        "format": "html",
        "status": None,
        "message": None,
        "hits": [],
    }

    status_match = _HTML_STATUS_PATTERN.search(html_text)
    if status_match:
        summary["status"] = status_match.group("status").upper()

    if "No significant similarity found" in html_text:
        summary["message"] = "No significant similarity found."
        summary["hits"] = []
        return summary

    hits: List[Dict[str, Any]] = []
    for row_match in _HTML_HIT_ROW_PATTERN.finditer(html_text):
        body = row_match.group("body")
        cells = [html_unescape(cell) for cell in _HTML_CELL_PATTERN.findall(body)]
        if len(cells) < 12:
            continue
        hit = {
            "description": _extract_cell_text(cells[1]),
            "scientific_name": _extract_cell_text(cells[2]),
            "common_name": _extract_cell_text(cells[3]),
            "taxid": _coerce_numeric(_extract_cell_text(cells[4])),
            "max_score": _coerce_numeric(_extract_cell_text(cells[5])),
            "total_score": _coerce_numeric(_extract_cell_text(cells[6])),
            "query_cover": _coerce_percentage(_extract_cell_text(cells[7])),
            "e_value": _coerce_numeric(_extract_cell_text(cells[8])),
            "percent_identity": _coerce_percentage(_extract_cell_text(cells[9])),
            "accession_length": _coerce_numeric(_extract_cell_text(cells[10])),
            "accession": _extract_accession(cells[11]),
        }
        hits.append(hit)
        if len(hits) >= max_hits:
            break

    if hits:
        summary["hits"] = hits
        return summary

    return summary if summary.get("status") else None


def _extract_cell_text(raw: str) -> str:
    cleaned = re.sub(r"<[^>]+>", "", raw)
    cleaned = html.unescape(cleaned)
    return " ".join(cleaned.split())


def _extract_accession(raw: str) -> Optional[str]:
    match = re.search(r">([^<>]+)</a>", raw)
    if match:
        return html.unescape(match.group(1)).strip()
    return _extract_cell_text(raw) or None


def _coerce_numeric(value: str) -> Union[int, float, str, None]:
    value = value.strip()
    if not value:
        return None
    try:
        if value.lower().startswith("e"):
            return float(value)
        return int(value.replace(",", ""))
    except ValueError:
        try:
            return float(value.replace("%", ""))
        except ValueError:
            return value


def _coerce_percentage(value: str) -> Optional[float]:
    value = value.strip().rstrip("%")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def html_unescape(fragment: str) -> str:
    return html.unescape(fragment)

def summarize_blast(result, top_hits=10, max_hsps=1):
    """
    Keep full alignments but limit how many hits/hsps are retained.
    """

    result = result['BlastOutput2']['report']['results']['search']
    hits_out = []
    hits = result.get("hits", [])[:top_hits]
    for hit in hits:
        desc = hit.get("description", [{}])[0]
        hsps = hit.get("hsps", [])[:max_hsps]
        best = hsps[0] if hsps else {}
        hit_entry = {
            "id": desc.get("id"),
            "title": desc.get("title"),
            "taxid": desc.get("taxid"),
            "sciname": desc.get("sciname"),
            "evalue": best.get("evalue"),
            "bitscore": best.get("bit_score"),
            "identity": best.get("identity"),
            "align_len": best.get("align_len"),
            "gaps": best.get("gaps"),
            "q_from": best.get("query_from"),
            "q_to": best.get("query_to"),
            "h_from": best.get("hit_from"),
            "h_to": best.get("hit_to"),
            "q_cov": round((best.get("align_len") or 0) / max(1, result.get("query_len", 1)), 3),
            "num_hsps": len(hsps),
            "alignment": {
                "qseq": best.get("qseq", ""),
                "hseq": best.get("hseq", ""),
                "midline": best.get("midline", ""),
            },
        }
        hits_out.append(hit_entry)

    return {
        "query_id": result.get("query_id"),
        "query_title": result.get("query_title"),
        "query_len": result.get("query_len"),
        "total_hits": len(result.get("hits", [])),
        "db_num": result.get("stat", {}).get("db_num"),
        "db_len": result.get("stat", {}).get("db_len"),
        "hits": hits_out,
    }


__all__ = [
    "postprocess_blast_submit",
    "decode_blast_response",
    "should_retry_blast_retrieve",
    "parse_blast_html_result",
    "summarize_blast",
]

