from collections import Counter, defaultdict
from typing import Any, Dict, List


def _truncate(text: Any, limit: int = 120) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _top_from_counter(counter: Counter, top_n: int = 5) -> List[Dict[str, Any]]:
    if not counter:
        return []
    items = counter.most_common(top_n)
    captured = sum(value for _, value in items)
    total = sum(counter.values())
    top_list = [
        {
            "label": label,
            "value": value,
        }
        for label, value in items
    ]
    if len(counter) > top_n and total > captured:
        top_list.append({"label": "Others", "value": total - captured})
    return top_list


def summarize_xrefs_by_id(response: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize the result of `get_xrefs_by_id` into compact aggregates."""

    if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
        raise ValueError("Response must be a list of dictionaries.")

    if not response:
        return {
            "counts": {"total_records": 0},
            "database_summary": {},
            "go_highlights": {},
            "samples": []
        }

    total_records = len(response)

    dbname_counter = Counter()
    db_display_names: Dict[str, str] = {}
    info_type_counter = Counter()
    linkage_counter = Counter()
    info_text_counter = Counter()

    description_count = 0
    synonyms_count = 0
    display_id_counter = Counter()
    primary_id_counter = Counter()

    go_entries: List[Dict[str, Any]] = []

    for item in response:
        dbname = item.get("dbname")
        if dbname:
            dbname_counter[dbname] += 1
        db_display = item.get("db_display_name")
        if dbname and db_display and dbname not in db_display_names:
            db_display_names[dbname] = db_display

        info_type = item.get("info_type")
        if info_type:
            info_type_counter[info_type] += 1

        info_text = item.get("info_text")
        if info_text:
            info_text_counter[info_text] += 1

        if item.get("description"):
            description_count += 1

        if item.get("synonyms"):
            if isinstance(item.get("synonyms"), list) and item["synonyms"]:
                synonyms_count += 1

        display_id = item.get("display_id")
        if display_id:
            display_id_counter[display_id] += 1

        primary_id = item.get("primary_id")
        if primary_id:
            primary_id_counter[primary_id] += 1

        if dbname == "GO":
            go_entries.append(item)
            linkage_types = item.get("linkage_types") or []
            if isinstance(linkage_types, (list, tuple)):
                linkage_counter.update(str(link) for link in linkage_types if link)
            else:
                linkage_counter[str(linkage_types)] += 1

    # --- Database summary ---
    top_databases = []
    for dbname, count in dbname_counter.most_common(10):
        top_databases.append({
            "dbname": dbname,
            "display_name": db_display_names.get(dbname, dbname),
            "count": count
        })

    # --- GO specific highlights ---
    go_summary: Dict[str, Any] = {}
    if go_entries:
        unique_terms = {entry.get("primary_id") for entry in go_entries if entry.get("primary_id")}
        go_summary = {
            "total": len(go_entries),
            "unique_terms": len(unique_terms),
            "top_linkage_types": _top_from_counter(linkage_counter, top_n=5)
        }

    # --- Info text consolidation (top reasons / provenance) ---
    provenance = _top_from_counter(info_text_counter, top_n=5)

    # --- Sample entries (one per top database, up to 3) ---
    samples: List[Dict[str, Any]] = []
    collected = 0
    seen_db = set()
    for dbname, _ in dbname_counter.most_common():
        if collected >= 3:
            break
        for item in response:
            if item.get("dbname") != dbname or dbname in seen_db:
                continue
            sample = {
                "dbname": dbname,
                "display_name": db_display_names.get(dbname, dbname),
                "info_type": item.get("info_type"),
                "display_id": item.get("display_id"),
                "primary_id": item.get("primary_id"),
                "description": _truncate(item.get("description")),
                "linkage_types": (item.get("linkage_types") or [])[:3],
            }
            extras = {k: v for k, v in item.items() if k not in {
                "dbname", "db_display_name", "info_type", "display_id", "primary_id",
                "description", "linkage_types", "synonyms"
            } and v not in (None, "", [], {})}
            if extras:
                sample["extra_fields"] = extras
            samples.append(sample)
            seen_db.add(dbname)
            collected += 1
            break

    summary = {
        "counts": {
            "total_records": total_records,
            "unique_databases": len(dbname_counter),
            "unique_info_types": len(info_type_counter),
            "with_descriptions": description_count,
            "with_synonyms": synonyms_count,
            "distinct_display_ids": len(display_id_counter),
            "distinct_primary_ids": len(primary_id_counter)
        },
        "database_summary": {
            "top_databases": top_databases,
            "info_type_distribution": dict(info_type_counter),
            "provenance": provenance
        },
        "go_highlights": go_summary,
        "samples": samples
    }

    return summary

