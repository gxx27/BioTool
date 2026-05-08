from collections import Counter
from typing import Any, Dict, List


def _truncate(text: Any, limit: int = 120) -> str:
    if text is None:
        return ""
    text = str(text)
    return text if len(text) <= limit else text[: limit - 3] + "..."


def postprocess_stream_keywords(response: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize UniProt keyword stream results into compact aggregates."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary containing a 'results' list.")

    results = response.get("results") or []
    if not isinstance(results, list):
        raise ValueError("Response['results'] must be a list of keyword entries.")

    keyword_entries = [entry for entry in results if isinstance(entry, dict)]
    total_entries = len(keyword_entries)

    if total_entries == 0:
        return {
            "counts": {"total_keywords": 0},
            "category_summary": [],
            "parents_stats": {},
            "examples": []
        }

    category_counter = Counter()
    parent_counter = Counter()
    keywords_with_links = 0
    max_depth = 0

    parent_name_counter = Counter()

    def _collect_parents(parents_list: List[Dict[str, Any]], depth: int = 0):
        nonlocal max_depth
        if not isinstance(parents_list, list):
            return
        max_depth = max(max_depth, depth)
        for parent in parents_list:
            keyword = parent.get("keyword") if isinstance(parent, dict) else {}
            if isinstance(keyword, dict):
                parent_id = keyword.get("id")
                parent_name = keyword.get("name")
                if parent_id:
                    parent_counter[parent_id] += 1
                if parent_name:
                    parent_name_counter[parent_name] += 1
            parent_parents = parent.get("parents") if isinstance(parent, dict) else []
            if parent_parents:
                _collect_parents(parent_parents, depth + 1)

    samples = []
    sample_size = 5

    for entry in keyword_entries:
        keyword = entry.get("keyword")
        if isinstance(keyword, dict):
            category = keyword.get("category")
            if category:
                category_counter[category] += 1
        parents = entry.get("parents")
        if parents:
            _collect_parents(parents, depth=1)

        links = entry.get("links")
        if isinstance(links, list) and links:
            keywords_with_links += 1

        if len(samples) < sample_size:
            samples.append({
                "keyword_id": keyword.get("id") if isinstance(keyword, dict) else None,
                "keyword_name": keyword.get("name") if isinstance(keyword, dict) else None,
                "category": keyword.get("category") if isinstance(keyword, dict) else None,
                "links": links[:2] if isinstance(links, list) else None,
                "parent_chain": _extract_parent_chain(parents)
            })

    category_summary = [
        {"category": category, "count": count}
        for category, count in category_counter.most_common(10)
    ]

    parents_summary = [
        {"parent_id": parent_id, "occurrences": count}
        for parent_id, count in parent_counter.most_common(10)
    ]

    parent_name_summary = [
        {"parent_name": name, "occurrences": count}
        for name, count in parent_name_counter.most_common(10)
    ]

    summary = {
        "counts": {
            "total_keywords": total_entries,
            "with_links": keywords_with_links,
            "unique_categories": len(category_counter),
            "unique_parents": len(parent_counter),
            "max_hierarchy_depth": max_depth,
        },
        "category_summary": category_summary,
        "parents_stats": parents_summary,
        "parent_name_stats": parent_name_summary,
        "examples": samples,
    }

    return summary


def _extract_parent_chain(parents: Any, limit: int = 4) -> List[str]:
    chain = []

    def _walk(nodes, depth=0):
        if not isinstance(nodes, list) or len(chain) >= limit:
            return
        for node in nodes:
            keyword = node.get("keyword") if isinstance(node, dict) else None
            if isinstance(keyword, dict):
                name = keyword.get("name") or keyword.get("id")
                if name:
                    chain.append(name)
            if len(chain) >= limit:
                break
            _walk(node.get("parents"), depth + 1)

    _walk(parents)
    return chain

