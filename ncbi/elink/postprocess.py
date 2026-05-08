"""Postprocessing helpers for NCBI ELink responses."""

from collections import Counter
from typing import Any, Dict, List, Optional

ID_SAMPLE_LIMIT = 5
ID_URL_LIST_LIMIT = 3
LINKOUT_SAMPLE_LIMIT = 5
LINK_SAMPLE_LIMIT = 10
TOP_COUNT_LIMIT = 5
TEXT_PREVIEW_LIMIT = 120


def _truncate(text: Optional[str], limit: int = TEXT_PREVIEW_LIMIT) -> Optional[str]:
    if not isinstance(text, str):
        return None
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _summarize_ids(ids: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(ids, list) or not ids:
        return None

    trimmed = [str(item) for item in ids[:ID_SAMPLE_LIMIT]]
    summary: Dict[str, Any] = {"ids": trimmed}
    if len(ids) > ID_SAMPLE_LIMIT:
        summary["additional"] = len(ids) - ID_SAMPLE_LIMIT
    return summary


def _summarize_linkouts(idurllist: Any) -> Optional[List[Dict[str, Any]]]:
    if not isinstance(idurllist, list) or not idurllist:
        return None

    summaries: List[Dict[str, Any]] = []

    for entry in idurllist[:ID_URL_LIST_LIMIT]:
        if not isinstance(entry, dict):
            continue

        objurls = entry.get("objurls")
        if not isinstance(objurls, list):
            objurls = []

        provider_counter: Counter[str] = Counter()
        category_counter: Counter[str] = Counter()
        subject_counter: Counter[str] = Counter()

        for obj in objurls:
            if not isinstance(obj, dict):
                continue
            provider = obj.get("provider")
            provider_name = None
            if isinstance(provider, dict):
                provider_name = provider.get("name") or provider.get("nameabbr")
            if isinstance(provider_name, str) and provider_name.strip():
                provider_counter[provider_name.strip()] += 1

            categories = obj.get("categories")
            if isinstance(categories, list):
                category_counter.update(c for c in categories if isinstance(c, str))

            subject_types = obj.get("subjecttypes")
            if isinstance(subject_types, list):
                subject_counter.update(s for s in subject_types if isinstance(s, str))

        samples: List[Dict[str, Any]] = []
        for obj in objurls[:LINKOUT_SAMPLE_LIMIT]:
            if not isinstance(obj, dict):
                continue
            provider = obj.get("provider") if isinstance(obj.get("provider"), dict) else {}
            provider_name = None
            if isinstance(provider, dict):
                provider_name = provider.get("name") or provider.get("nameabbr")

            url_info = obj.get("url")
            url_value = None
            if isinstance(url_info, dict):
                url_value = url_info.get("value")
            elif isinstance(url_info, str):
                url_value = url_info

            sample = {
                "url": _truncate(url_value),
                "linkname": _truncate(obj.get("linkname")),
            }
            if provider_name:
                sample["provider"] = provider_name
            categories = obj.get("categories")
            if isinstance(categories, list) and categories:
                sample["categories"] = categories[:TOP_COUNT_LIMIT]
            subject_types = obj.get("subjecttypes")
            if isinstance(subject_types, list) and subject_types:
                sample["subject_types"] = subject_types[:TOP_COUNT_LIMIT]
            samples.append({k: v for k, v in sample.items() if v})

        entry_summary: Dict[str, Any] = {
            "id": entry.get("id"),
            "total_links": len(objurls),
        }

        if provider_counter:
            entry_summary["top_providers"] = dict(provider_counter.most_common(TOP_COUNT_LIMIT))
        if category_counter:
            entry_summary["categories"] = dict(category_counter.most_common(TOP_COUNT_LIMIT))
        if subject_counter:
            entry_summary["subject_types"] = dict(subject_counter.most_common(TOP_COUNT_LIMIT))
        if samples:
            entry_summary["examples"] = samples
        if len(objurls) > LINKOUT_SAMPLE_LIMIT:
            entry_summary["additional_examples"] = len(objurls) - LINKOUT_SAMPLE_LIMIT

        summaries.append(entry_summary)

    if len(idurllist) > ID_URL_LIST_LIMIT:
        summaries.append({"note": f"{len(idurllist) - ID_URL_LIST_LIMIT} additional id/url groups truncated"})

    return summaries or None


def _parse_score(score: Any) -> Optional[float]:
    if score in (None, ""):
        return None
    try:
        return float(score)
    except (TypeError, ValueError):
        return None


def _summarize_links(links: Any) -> Dict[str, Any]:
    summary: Dict[str, Any] = {"total": 0}
    if not isinstance(links, list) or not links:
        return summary

    summary["total"] = len(links)

    examples: List[Dict[str, Any]] = []
    score_counter: Counter[str] = Counter()

    for link in links[:LINK_SAMPLE_LIMIT]:
        if isinstance(link, dict):
            link_id = link.get("id")
            example: Dict[str, Any] = {"id": str(link_id) if link_id is not None else None}
            score = link.get("score")
            parsed_score = _parse_score(score)
            if parsed_score is not None:
                example["score"] = parsed_score
                score_counter[str(parsed_score)] += 1
            elif isinstance(score, str) and score.strip():
                example["score"] = score.strip()
                score_counter[score.strip()] += 1
            examples.append({k: v for k, v in example.items() if v is not None})
        else:
            examples.append({"id": str(link)})

    if isinstance(links[0], dict):
        for link in links:
            if not isinstance(link, dict):
                continue
            score = link.get("score")
            parsed_score = _parse_score(score)
            key = str(parsed_score) if parsed_score is not None else (score.strip() if isinstance(score, str) else None)
            if key:
                score_counter[key] += 0  # ensure presence even if already counted

        score_counter = Counter(score_counter)
    else:
        score_counter = Counter()

    if examples:
        summary["examples"] = examples
    if summary["total"] > LINK_SAMPLE_LIMIT:
        summary["additional"] = summary["total"] - LINK_SAMPLE_LIMIT
    if score_counter:
        summary["scores"] = dict(score_counter.most_common(TOP_COUNT_LIMIT))

    return summary


def _summarize_linksetdb(linksetdb: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(linksetdb, dict):
        return None

    summary: Dict[str, Any] = {
        "dbto": linksetdb.get("dbto"),
        "linkname": linksetdb.get("linkname"),
    }

    links = linksetdb.get("links")
    summary["links"] = _summarize_links(links)

    webenv = linksetdb.get("webenv") or linksetdb.get("WebEnv")
    query_key = linksetdb.get("querykey") or linksetdb.get("QueryKey")
    if webenv or query_key:
        summary["history"] = {k: v for k, v in {"webenv": webenv, "queryKey": query_key}.items() if v}

    return summary


def _summarize_linkset(linkset: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(linkset, dict):
        return None

    summary: Dict[str, Any] = {}

    dbfrom = linkset.get("dbfrom")
    if isinstance(dbfrom, str):
        summary["dbfrom"] = dbfrom

    ids_summary = _summarize_ids(linkset.get("ids"))
    if ids_summary:
        summary["source_ids"] = ids_summary

    history = {}
    webenv = linkset.get("webenv") or linkset.get("WebEnv")
    query_key = linkset.get("querykey") or linkset.get("QueryKey")
    if webenv:
        history["webenv"] = webenv
    if query_key:
        history["queryKey"] = query_key
    if history:
        summary["history"] = history

    linkouts = _summarize_linkouts(linkset.get("idurllist"))
    if linkouts:
        summary["linkouts"] = linkouts

    linksetdbs = linkset.get("linksetdbs")
    if isinstance(linksetdbs, list) and linksetdbs:
        summarized_dbs = []
        for db in linksetdbs:
            db_summary = _summarize_linksetdb(db)
            if db_summary:
                summarized_dbs.append(db_summary)
        if summarized_dbs:
            summary["link_dbs"] = summarized_dbs

    if not summary:
        return None
    return summary


def postprocess_elink(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize NCBI ELink responses into concise aggregates."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    header_summary: Dict[str, Any] = {}
    header = response.get("header")
    if isinstance(header, dict):
        for key in ("type", "version"):
            value = header.get(key)
            if value:
                header_summary[key] = value

    linksets = response.get("linksets")
    linkset_summaries: List[Dict[str, Any]] = []
    if isinstance(linksets, list):
        for linkset in linksets:
            summarized = _summarize_linkset(linkset)
            if summarized:
                linkset_summaries.append(summarized)

    result: Dict[str, Any] = {}
    if header_summary:
        result["header"] = header_summary

    result["summary"] = {"linkset_count": len(linkset_summaries)}

    if linkset_summaries:
        result["linksets"] = linkset_summaries

    return result
























