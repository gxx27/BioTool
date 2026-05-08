"""
Split user_queries.json into train/test sets (random 4:1) in OpenAI chat format.
"""

import argparse
import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

DEFAULT_QUERIES_PATH = os.path.join(REPO_DIR, "user_queries.json")
DEFAULT_OBSERVATIONS_DIR = os.path.join(REPO_DIR, "observations")
DEFAULT_OUTPUT_DIR = os.path.join(REPO_DIR, "data")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: str, obj: Any) -> None:
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _load_observation(observations_dir: str, obs_idx: Any) -> Tuple[str, Optional[str]]:
    """
    Load observation from observations_dir/{obs_idx}.txt.
    Returns (content_string, error_message).
    """
    try:
        obs_int = int(obs_idx)
    except Exception:
        return json.dumps({"error": "invalid obs_idx", "obs_idx": obs_idx}, ensure_ascii=False), "invalid obs_idx"

    obs_path = os.path.join(observations_dir, f"{obs_int}.txt")
    if not os.path.isfile(obs_path):
        return json.dumps({"error": "observation not found", "path": obs_path}, ensure_ascii=False), "observation not found"

    # Observation files are usually JSON; keep them as a JSON string for tool message content.
    try:
        with open(obs_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return json.dumps(obj, ensure_ascii=False), None
    except Exception:
        # Fall back to raw text.
        try:
            with open(obs_path, "r", encoding="utf-8") as f:
                txt = f.read()
            return txt, "observation not json"
        except Exception as e:
            return json.dumps({"error": "failed to read observation", "path": obs_path, "detail": str(e)}, ensure_ascii=False), "failed to read observation"


def _to_openai_sample(entry: Dict[str, Any], observations_dir: str) -> Dict[str, Any]:
    query = entry.get("query") or ""
    function_name = entry.get("function") or ""
    params = entry.get("params") or {}
    obs_idx = entry.get("obs_idx", entry.get("idx"))

    observation_content, obs_err = _load_observation(observations_dir, obs_idx)

    fc_payload = {"name": str(function_name), "arguments": params}
    conversations = [
        {"from": "human", "value": str(query)},
        {"from": "function_call", "value": json.dumps(fc_payload, ensure_ascii=False)},
        {"from": "observation", "value": observation_content},
    ]

    # Keep the sample minimal; attach only an optional flag for debugging.
    if obs_err:
        conversations.append({"from": "gpt", "value": f"[observation_error] {obs_err}"})

    return {"conversations": conversations}


def random_split(entries: List[Dict[str, Any]], seed: int = 42, train_ratio: float = 0.8) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    random.seed(seed)
    items = list(entries)
    random.shuffle(items)
    n_train = int(len(items) * train_ratio)
    return items[:n_train], items[n_train:]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries_path", default=DEFAULT_QUERIES_PATH)
    parser.add_argument("--observations_dir", default=DEFAULT_OBSERVATIONS_DIR)
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--require_informative", action="store_true", help="If set, keep only entries with informative=true")
    args = parser.parse_args()

    data = _read_json(args.queries_path)
    if not isinstance(data, list):
        raise ValueError("user_queries.json must be a list")

    entries: List[Dict[str, Any]] = []
    for e in data:
        if not isinstance(e, dict):
            continue
        if args.require_informative and e.get("informative") is not True:
            continue
        entries.append(e)

    samples = [_to_openai_sample(e, args.observations_dir) for e in entries]
    train, test = random_split(samples, seed=args.seed, train_ratio=args.train_ratio)

    out_dir = args.output_dir
    train_path = os.path.join(out_dir, "train_random_v2.json")
    test_path = os.path.join(out_dir, "test_random_v2.json")
    _write_json(train_path, train)
    _write_json(test_path, test)

    summary = {
        "input_entries": len(data),
        "kept_entries": len(entries),
        "samples": len(samples),
        "train": len(train),
        "test": len(test),
        "seed": args.seed,
        "train_ratio": args.train_ratio,
        "queries_path": args.queries_path,
        "observations_dir": args.observations_dir,
        "output_dir": args.output_dir,
        "require_informative": args.require_informative,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()


