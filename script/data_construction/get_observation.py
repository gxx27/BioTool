"""
Get the observations for the dataset.

Collect the function calling results for the dataset.
Simplied version:
1. Scans for *_params_clean.json files.
2. Aggregates them into params.json.
3. Executes each function call and saves the output to observations/{idx}.txt.
"""

import importlib
import importlib.util
import io
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from tqdm import tqdm

# Paths are resolved relative to the repository root (two levels above this file).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
TOOLS_PATH = os.path.join(ROOT_DIR, "data", "tools.json")
PARAMS_JSON_PATH = os.path.join(ROOT_DIR, "params.json")
OBSERVATIONS_DIR = os.path.join(ROOT_DIR, "observations")


def _ensure_dir(path: str) -> None:
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)


def _load_json(path: str) -> Any:
    with io.open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: Any) -> None:
    _ensure_dir(os.path.dirname(path))
    with io.open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _stringify_result(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, (str, bytes)):
        return result.decode("utf-8", errors="ignore") if isinstance(result, bytes) else result
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception:
        return str(result)


def _should_sleep_long(database: str, tool: str, func_name: str) -> bool:
    if database.lower() == "ncbi":
        if tool.lower() == "blast":
            return True
    return False


def _rate_limit_sleep(database: str, tool: str, func_name: str) -> None:
    if _should_sleep_long(database, tool, func_name):
        time.sleep(2.0)
    else:
        time.sleep(0.5)

def _resolve_api_module(root: str, database: str, tool: str) -> Any:
    """Import ``<database>.<tool>.api`` from a repo with ``api.py`` packages."""
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(f"{database}.{tool}.api")


def _call_function(module: Any, func_name: str, params: Dict[str, Any]) -> Any:
    if not hasattr(module, func_name):
        raise AttributeError(f"Function not found: {func_name}")
    func = getattr(module, func_name)
    return func(**params)


def _load_tools_function_names(tools_json_path: str) -> Set[str]:
    try:
        data = _load_json(tools_json_path)
    except Exception:
        return set()
    names: Set[str] = set()
    if isinstance(data, list):
        for item in data:
            try:
                if isinstance(item, dict) and item.get("type") == "function":
                    fn = item.get("function") or {}
                    name = fn.get("name")
                    if isinstance(name, str) and name:
                        names.add(name)
            except Exception:
                continue
    return names


def _iter_params_clean_files(root_dir: str) -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []
    for dirpath, _, filenames in os.walk(root_dir):
        for fname in filenames:
            if not fname.endswith("_params_clean.json"):
                continue
            rel = os.path.relpath(dirpath, root_dir)
            parts = rel.split(os.sep)
            if len(parts) < 2:
                continue
            database, tool = parts[0], parts[1]
            results.append((database, tool, os.path.join(dirpath, fname)))
    return results


def build_queries_from_params(
    params_root: str,
    tools_path: str,
) -> List[Dict[str, Any]]:
    """
    Scans for *_params_clean.json files and aggregates them into a list of query items.
    Filters out 'blast' and functions not in tools.json.
    """
    allowed_functions: Set[str] = _load_tools_function_names(tools_path)
    items: List[Dict[str, Any]] = []
    idx = 0
    
    print("Scanning for params files...")
    files = _iter_params_clean_files(params_root)
    
    for database, tool, file_path in tqdm(files, desc="Building queries"):
        function = os.path.basename(file_path)[:-len("_params_clean.json")]
        if 'blast' in function: # skip blast for now
            continue
        if allowed_functions and (function not in allowed_functions):
            continue
        try:
            params_list = _load_json(file_path)
        except Exception:
            continue
        if not isinstance(params_list, list):
            continue
        for params in params_list:
            if not isinstance(params, dict):
                continue
            items.append({
                "database": database,
                "tool": tool,
                "function": function,
                "params": params,
                "idx": idx,
            })
            idx += 1
    
    return items


def process_queries(
    data: List[Dict[str, Any]],
    out_dir: str,
    root_dir: str,
) -> None:
    """
    Iterates through query items, calls the API, and saves the result.
    """
    _ensure_dir(out_dir)

    print(f"Processing {len(data)} items", file=sys.stderr)
    for item in tqdm(data, desc="Calling APIs"):
        idx = item.get("idx")
        if idx is None:
            continue

        if idx != 4057:
            continue
            
        try:
            database = item.get("database") or ""
            tool = item.get("tool") or ""
            func_name = item.get("function") or ""
            params = dict(item.get("params") or {})

            if 'blast' in func_name: # skip blast for now
                continue

            # Rate limit before each call
            _rate_limit_sleep(database, tool, func_name)

            module = _resolve_api_module(root_dir, database, tool)
            result = _call_function(module, func_name, params)

            text = _stringify_result(result)
            out_path = os.path.join(out_dir, f"{idx}.txt")
            with io.open(out_path, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            # Log error to stdout
            try:
                error_record = {
                    "idx": idx,
                    "database": database,
                    "tool": tool,
                    "function": func_name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                }
                print(json.dumps(error_record, ensure_ascii=False))
            except Exception:
                print(f"{idx} ERROR: {e}")
            continue


def main() -> None:
    # 1. Build queries from params files
    queries = build_queries_from_params(
        params_root=ROOT_DIR,
        tools_path=TOOLS_PATH,
    )
    
    # 2. Write combined params.json
    _write_json(PARAMS_JSON_PATH, queries)
    print(f"Wrote {len(queries)} items to {PARAMS_JSON_PATH}")
    
    # 3. Process queries and create observations
    process_queries(queries, OBSERVATIONS_DIR, ROOT_DIR)


if __name__ == "__main__":
    main()
