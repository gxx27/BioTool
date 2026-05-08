"""
Build the tool database for the dataset.

Constructing the tools.json file for the dataset.
"""

import os
import json
import re
from typing import Any, Dict, List, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
OUTPUT_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "tools.json")


def _json_schema_type(t: str) -> str:
    t_upper = (t or "").strip().upper()
    if t_upper == "STRING":
        return "string"
    if t_upper == "BOOLEAN":
        return "boolean"
    if t_upper == "NUMBER":
        return "number"
    if t_upper == "INTEGER":
        return "integer"
    # Fallback to string for unknown types
    return "string"


def _make_function_name(namespace: str, api_name: str, used: Dict[str, int]) -> str:
    """
    Build a tool/function name that:
    - Uses only characters matching ^[A-Za-z0-9_-]+$
    - Is at most 64 characters long
    - Is deduplicated with a numeric suffix within the 64-char limit
    """
    # Create a base with clear separators first
    raw = f"{namespace}__{api_name}"
    raw = raw.replace("/", "_").replace(":", "_").replace(" ", "_")

    # Sanitize to allowed charset by replacing disallowed chars with underscore
    safe = re.sub(r"[^A-Za-z0-9_-]+", "_", raw)

    # Normalize repeated separators and trim edges
    safe = re.sub(r"_{2,}", "_", safe)
    safe = re.sub(r"-{2,}", "-", safe)
    safe = safe.strip("_-")

    # Fallback if everything was stripped
    if not safe:
        safe = "tool"

    # Enforce max length for the base name (without suffix)
    base = safe[:64]

    # First occurrence: return as-is (within 64 chars already)
    if base not in used:
        used[base] = 1
        return base

    # Subsequent occurrences: append a numeric suffix, truncating base to fit
    idx = used[base]
    used[base] = idx + 1
    suffix = f"_{idx}"
    limit = 64 - len(suffix)
    truncated = base[:limit].rstrip("_-") or "tool"
    # Ensure final still respects the 64-char limit
    return f"{truncated[:64 - len(suffix)]}{suffix}"


def _build_function(tool_meta: Dict[str, Any], api: Dict[str, Any], namespace: str, used_names: Dict[str, int]) -> Dict[str, Any]:
    required_params = api.get("required_parameters", []) or []
    optional_params = api.get("optional_parameters", []) or []

    properties: Dict[str, Any] = {}
    required: List[str] = []

    def add_param(p: Dict[str, Any], required_flag: bool) -> None:
        name = p.get("name")
        if not name:
            return
        ptype = _json_schema_type(p.get("type", "string"))
        prop: Dict[str, Any] = {"type": ptype}
        if p.get("description"):
            prop["description"] = p["description"]
        # Avoid overwriting if appears in both required and optional
        if name not in properties:
            properties[name] = prop
        if required_flag and name not in required:
            required.append(name)

    for p in required_params:
        add_param(p, True)
    for p in optional_params:
        add_param(p, False)

    api_name = api.get("name", "function")
    # import ipdb; ipdb.set_trace()
    # func_name = _make_function_name(namespace, api_name, used_names)
    # print(f'{namespace}__{api_name} -> {func_name} ({len(func_name)})')
    func_name = api.get("function_name")
    if len(func_name) > 64:
        import ipdb; ipdb.set_trace()

    tool_desc = tool_meta.get("tool_description") or tool_meta.get("title") or tool_meta.get("tool_name")
    api_desc = api.get("description") or ""
    description = api_desc
    if tool_desc:
        description = f"{api_desc} (Source: {tool_desc})" if api_desc else tool_desc

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "additionalProperties": False,
    }
    if required:
        parameters["required"] = required

    return {
        "type": "function",
        "function": {
            "name": func_name,
            "description": description,
            "parameters": parameters,
        },
    }


def _collect_tool_jsons(root: str, subdirs: List[str]) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    for sub in subdirs:
        base = os.path.join(root, sub)
        for dirpath, _dirnames, filenames in os.walk(base):
            for fname in filenames:
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(dirpath, fname)
                results.append((sub, fpath))
    return results


def build_pool() -> List[Dict[str, Any]]:
    tools: List[Dict[str, Any]] = []
    used_names: Dict[str, int] = {}

    json_files = _collect_tool_jsons(BASE_DIR, ["ensembl", "ncbi", "uniprot"])
    for sub, path in json_files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        # Filter only spec files that contain tool metadata
        if not isinstance(data, dict):
            continue
        if "api_list" not in data or "tool_name" not in data:
            continue

        # Derive namespace from relative path, e.g., ensembl/lookup.json -> ensembl_lookup
        rel = os.path.relpath(path, os.path.join(BASE_DIR, sub))
        rel_no_ext = os.path.splitext(rel)[0]
        ns_raw = f"{sub}_{rel_no_ext}"
        namespace = ns_raw.replace(os.sep, "_").replace("-", "_")

        api_list = data.get("api_list", []) or []
        for api in api_list:
            if not isinstance(api, dict):
                continue
            try:
                tool = _build_function(data, api, namespace, used_names)
                tools.append(tool)
            except Exception:
                continue

    # Sort by function name for determinism
    tools.sort(key=lambda t: t.get("function", {}).get("name", "") if isinstance(t.get("function"), dict) else t.get("function", ""))
    return tools


def main() -> None:
    tools = build_pool()
    if not os.path.isdir(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)
    print(json.dumps({
        "tools_written": len(tools),
        "output_file": OUTPUT_FILE,
    }))


if __name__ == "__main__":
    main()