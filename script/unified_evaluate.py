"""
Unified BioTool evaluation script.
"""

import argparse
import json
import os
import sys
import time
import importlib
import importlib.util
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from tqdm import tqdm


# ======================== Configuration ========================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")
TOOLS_PATH = os.path.join(DATA_DIR, "tools.json")
FUNCTION_MAPPING_PATH = os.path.join(DATA_DIR, "function_mapping.json")
MEDCPT_MODEL = "ncbi/MedCPT-Query-Encoder"
API_RATE_LIMIT_DELAY = 0.34  # seconds between API calls


# ======================== Data Loading ========================

def load_function_mapping() -> Dict[str, Tuple[str, str]]:
    """Load mapping from function names to (database, tool) tuples."""
    with open(FUNCTION_MAPPING_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {fn: (info["database"], info["tool"]) for fn, info in raw.items()}


def load_db_mapping() -> Dict[str, str]:
    """Load mapping from function names to database name (lower-cased)."""
    with open(FUNCTION_MAPPING_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return {fn: info["database"].lower() for fn, info in raw.items()}


def load_predictions(file_path: str) -> List[Dict[str, Any]]:
    """Load predictions from a JSONL or JSON file."""
    abs_path = os.path.abspath(file_path)
    predictions: List[Dict[str, Any]] = []

    if abs_path.endswith(".json") and not abs_path.endswith(".jsonl"):
        with open(abs_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data

    with open(abs_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                predictions.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return predictions


# ======================== Tool Call Extraction ========================

def extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
    """Extract a tool call dict from various model output formats."""
    if not text:
        return None

    # Format 1: <tool_call> JSON </tool_call>
    if "<tool_call>" in text and "</tool_call>" in text:
        try:
            start = text.find("<tool_call>") + len("<tool_call>")
            end = text.find("</tool_call>")
            call_data = json.loads(text[start:end].strip())
            return call_data
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 2: Action: tool_name\nAction Input: JSON
    if "Action:" in text and "Action Input:" in text:
        try:
            action_start = text.find("Action:") + len("Action:")
            action_end = text.find("\n", action_start)
            if action_end == -1:
                action_end = len(text)
            func_name = text[action_start:action_end].strip()

            input_start = text.find("Action Input:") + len("Action Input:")
            input_end = text.find("\n", input_start)
            if input_end == -1:
                input_end = len(text)
            args_content = text[input_start:input_end].strip().strip("`")
            args = json.loads(args_content)
            return {"name": func_name, "arguments": args}
        except (json.JSONDecodeError, ValueError):
            pass

    # Format 3: Raw JSON with "name" + "parameters" or "arguments"
    try:
        call_data = json.loads(text.strip())
        if isinstance(call_data, dict) and "name" in call_data:
            if "parameters" in call_data:
                return {"name": call_data["name"], "arguments": call_data["parameters"]}
            if "arguments" in call_data:
                return call_data
    except (json.JSONDecodeError, ValueError):
        pass

    return None


def normalize_function_call(call: Dict[str, Any]) -> str:
    """Canonicalize a function call for exact-match comparison."""
    normalized = {
        "name": call.get("name", ""),
        "arguments": call.get("arguments", {}),
    }
    if isinstance(normalized["arguments"], dict):
        normalized["arguments"] = dict(sorted(normalized["arguments"].items()))
    return json.dumps(normalized, sort_keys=True)


# ======================== BioAPI Calling ========================

def _resolve_api_module(root: str, database: str, tool: str) -> Any:
    """Dynamically import the api module for a (database, tool).

    The api.py modules use ``from .postprocess import ...``, so the database
    and tool directories must be importable as proper packages (each contains
    an empty ``__init__.py``). We register ``root`` on ``sys.path`` once and
    delegate to ``importlib.import_module``.
    """
    if root not in sys.path:
        sys.path.insert(0, root)
    return importlib.import_module(f"{database}.{tool}.api")


def _stringify_result(result: Any) -> str:
    """Coerce an API result into a string for downstream comparison."""
    if result is None:
        return ""
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="ignore")
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception:
        return str(result)


def call_bioapi_function(
    func_name: str, params: Dict[str, Any], func_mapping: Dict[str, Tuple[str, str]]
) -> Tuple[bool, str]:
    """Invoke a BioAPI function. Returns (success, result_str)."""
    if func_name not in func_mapping:
        return False, f"Function {func_name} not found in mapping"

    database, tool = func_mapping[func_name]
    try:
        module = _resolve_api_module(ROOT_DIR, database, tool)
        func = getattr(module, func_name)
        result = func(**params)
        return True, _stringify_result(result)
    except Exception as e:
        return False, str(e)


# ======================== Phase 1: EM + API Calls ========================

def evaluate_single(
    prediction: Dict[str, Any], func_mapping: Dict[str, Tuple[str, str]]
) -> Dict[str, Any]:
    """Evaluate a single prediction (EM check + live API calls)."""
    predict_text = prediction.get("predict", "")
    label_text = prediction.get("label", "")

    predict_call = extract_tool_call(predict_text)
    label_call = extract_tool_call(label_text)

    result = {
        "prompt": prediction.get("prompt", ""),
        "exact_match": False,
        "predict_call": predict_call,
        "label_call": label_call,
        "api_success": False,
        "predict_response": None,
        "label_response": None,
        "similarity": None,
        "error": None,
    }

    if predict_call and label_call:
        if normalize_function_call(predict_call) == normalize_function_call(label_call):
            result["exact_match"] = True
            return result

    predict_success, predict_response = False, None
    if predict_call:
        func_name = predict_call.get("name", "")
        params = predict_call.get("arguments", {})
        predict_success, predict_response = call_bioapi_function(func_name, params, func_mapping)
        time.sleep(API_RATE_LIMIT_DELAY)

    label_success, label_response = False, None
    if label_call:
        func_name = label_call.get("name", "")
        params = label_call.get("arguments", {})
        label_success, label_response = call_bioapi_function(func_name, params, func_mapping)
        time.sleep(API_RATE_LIMIT_DELAY)

    result["predict_response"] = predict_response if predict_success else None
    result["label_response"] = label_response if label_success else None
    result["api_success"] = predict_success and label_success

    return result


def run_evaluation_phase1(input_file: str, output_file: str, func_mapping: Dict) -> List[Dict]:
    """Phase 1: evaluate predictions (EM + API calls). No GPU required."""
    print(f"\n[Phase 1] Evaluating {input_file}")
    predictions = load_predictions(input_file)
    if not predictions:
        print(f"  No predictions found in {input_file}")
        return []

    print(f"  Loaded {len(predictions)} predictions")
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    results: List[Dict[str, Any]] = []
    for pred in tqdm(predictions, desc=f"Eval {os.path.basename(input_file)}"):
        results.append(evaluate_single(pred, func_mapping))

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    em = sum(1 for r in results if r["exact_match"])
    api = sum(1 for r in results if r["api_success"])
    print(f"  Results: {len(results)} total, {em} EM, {api} API success")
    print(f"  Saved to {output_file}")
    return results


# ======================== Phase 2: MedCPT Similarity ========================

class MedCPTCalculator:
    """Compute cosine similarity using MedCPT-Query-Encoder."""

    def __init__(self, model_name: str = MEDCPT_MODEL):
        import torch
        from transformers import AutoTokenizer, AutoModel

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"  Loading MedCPT model on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(self.device).eval()
        self._torch = torch

    def get_embedding(self, text: str) -> np.ndarray:
        if not text or not isinstance(text, str):
            return np.zeros(768)
        try:
            with self._torch.no_grad():
                encoded = self.tokenizer(
                    text, truncation=True, padding=True,
                    return_tensors="pt", max_length=512,
                )
                encoded = {k: v.to(self.device) for k, v in encoded.items()}
                embeds = self.model(**encoded).last_hidden_state[:, 0, :]
                return embeds.cpu().numpy().squeeze()
        except Exception as e:
            print(f"  Embedding error: {e}")
            return np.zeros(768)

    def similarity(self, text1: str, text2: str) -> float:
        from sklearn.metrics.pairwise import cosine_similarity
        emb1 = self.get_embedding(text1)
        emb2 = self.get_embedding(text2)
        return float(np.clip(cosine_similarity([emb1], [emb2])[0][0], -1.0, 1.0))


def run_similarity_phase2(analysis_files: List[str]) -> None:
    """Phase 2: compute MedCPT similarity for all analysis files."""
    files_needing_sim: List[Tuple[str, int]] = []
    for fp in analysis_files:
        if not os.path.exists(fp):
            print(f"  Skipping (not found): {fp}")
            continue
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)
        need = sum(
            1 for item in data
            if item.get("api_success") and item.get("predict_response")
            and item.get("label_response") and item.get("similarity") is None
        )
        if need > 0:
            files_needing_sim.append((fp, need))

    if not files_needing_sim:
        print("[Phase 2] No files need similarity computation.")
        return

    total = sum(n for _, n in files_needing_sim)
    print(f"\n[Phase 2] Computing MedCPT similarity for {len(files_needing_sim)} files ({total} samples)")

    calculator = MedCPTCalculator()
    for fp, _ in files_needing_sim:
        print(f"\n  Processing {os.path.basename(fp)}...")
        with open(fp, "r", encoding="utf-8") as f:
            data = json.load(f)

        count = 0
        for item in tqdm(data, desc=f"Sim {os.path.basename(fp)}"):
            if (
                item.get("api_success")
                and item.get("predict_response")
                and item.get("label_response")
                and item.get("similarity") is None
            ):
                item["similarity"] = calculator.similarity(
                    item["predict_response"], item["label_response"]
                )
                item["similarity_model"] = "MedCPT-Query-Encoder"
                count += 1

        with open(fp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  Computed similarity for {count} samples in {os.path.basename(fp)}")

    print("\n[Phase 2] Similarity computation complete.")


# ======================== Phase 3: Metrics Calculation ========================

def compute_metrics(results: List[Dict], db_mapping: Dict[str, str]) -> Dict[str, Dict]:
    """
    Compute EM, AS and BioTool Score per database (NCBI, UniProt, Ensembl) and overall.

    Returns: {db_name: {"em": float, "as": float, "biotool_score": float, "count": int}}
    """
    db_buckets: Dict[str, List] = {"ncbi": [], "uniprot": [], "ensembl": []}

    for r in results:
        func_name = None
        label_call = r.get("label_call")
        if isinstance(label_call, dict):
            func_name = label_call.get("name")
        if not func_name:
            predict_call = r.get("predict_call")
            if isinstance(predict_call, dict):
                func_name = predict_call.get("name")

        db = db_mapping.get(func_name, "").lower() if func_name else ""
        if db in db_buckets:
            db_buckets[db].append(r)

    def _calc(items: List[Dict]) -> Dict:
        n = len(items)
        if n == 0:
            return {"em": 0.0, "as": 0.0, "biotool_score": 0.0, "count": 0}

        em_count = sum(1 for r in items if r.get("exact_match"))
        as_count = sum(1 for r in items if r.get("exact_match") or r.get("api_success"))

        scores = []
        for r in items:
            if r.get("exact_match"):
                scores.append(1.0)
            elif r.get("api_success"):
                sim = r.get("similarity")
                scores.append(float(sim) if sim is not None else 0.0)
            else:
                scores.append(0.0)

        return {
            "em": em_count / n * 100,
            "as": as_count / n * 100,
            "biotool_score": float(np.mean(scores)) * 100,
            "count": n,
        }

    metrics = {db: _calc(items) for db, items in db_buckets.items()}
    metrics["overall"] = _calc(results)
    return metrics


def print_metrics(metrics: Dict[str, Dict], label: str) -> None:
    """Pretty-print metrics for a single analysis file."""
    dbs = ["ncbi", "uniprot", "ensembl", "overall"]
    header = f"{'':20s} {'NCBI':>10s} {'UniProt':>10s} {'Ensembl':>10s} {'Overall':>10s}"

    print(f"\n{'=' * 65}")
    print(f"  {label}")
    print(f"{'=' * 65}")
    print(header)
    print("-" * 65)

    for metric_name, key in [
        ("Exact Match (%)", "em"),
        ("API Success (%)", "as"),
        ("BioTool Score (%)", "biotool_score"),
    ]:
        row = f"{metric_name:20s}"
        for db in dbs:
            val = metrics.get(db, {}).get(key, 0.0)
            row += f" {val:>9.1f}"
        print(row)

    counts_row = f"{'Sample Count':20s}"
    for db in dbs:
        counts_row += f" {metrics.get(db, {}).get('count', 0):>9d}"
    print(counts_row)
    print(f"{'=' * 65}")


# ======================== Tables with Mean +/- Std ========================

def compute_tables_from_config(config_path: str) -> Dict[str, Any]:
    """
    Generate tables with mean +/- std from an experiment config JSON.

    Config format:
    {
        "base_dir": "<optional repo root, defaults to repo root>",
        "categories": {
            "Category Name": {
                "Model Name": {
                    "runs": ["path/to/run1.json", "path/to/run2.json", ...]
                }
            }
        }
    }
    """
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    base_dir = config.get("base_dir", ROOT_DIR)
    db_mapping = load_db_mapping()
    dbs = ["ncbi", "uniprot", "ensembl", "overall"]

    all_tables_data: Dict[str, Any] = {}

    for category_name, models in config.get("categories", {}).items():
        print(f"\n{'#' * 70}")
        print(f"  Category: {category_name}")
        print(f"{'#' * 70}")

        table_data: Dict[str, Any] = {}
        for model_name, model_cfg in models.items():
            run_paths = model_cfg.get("runs", [])
            run_metrics_list: List[Dict[str, Dict]] = []

            for rp in run_paths:
                full_path = rp if os.path.isabs(rp) else os.path.join(base_dir, rp)
                if not os.path.exists(full_path):
                    print(f"  Warning: {full_path} not found, skipping")
                    continue
                with open(full_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                run_metrics_list.append(compute_metrics(data, db_mapping))

            if not run_metrics_list:
                print(f"  {model_name}: no valid runs found")
                continue

            aggregated: Dict[str, Dict[str, Dict[str, float]]] = {}
            for db in dbs:
                for key in ["em", "as", "biotool_score"]:
                    vals = [rm[db][key] for rm in run_metrics_list if db in rm]
                    aggregated.setdefault(db, {})[key] = {
                        "mean": float(np.mean(vals)) if vals else 0.0,
                        "std": float(np.std(vals, ddof=0)) if vals else 0.0,
                        "n": len(vals),
                    }

            table_data[model_name] = aggregated
            print(f"  {model_name}: {len(run_metrics_list)} runs loaded")

        all_tables_data[category_name] = table_data

    _print_biotool_score_table(all_tables_data, dbs)
    _print_em_as_table(all_tables_data, dbs)
    return all_tables_data


def _fmt(mean: float, std: float, n: int) -> str:
    if n <= 1:
        return f"{mean:.1f}"
    return f"{mean:.1f}±{std:.1f}"


def _print_biotool_score_table(all_data: Dict, dbs: List[str]) -> None:
    print(f"\n{'=' * 80}")
    print("  BioTool Score (%) — Mean ± Std across runs")
    print(f"{'=' * 80}")
    header = f"{'Model':25s}"
    for db in dbs:
        header += f" {db.upper():>12s}"
    print(header)
    print("-" * 80)

    for cat_name, models in all_data.items():
        print(f"  [{cat_name}]")
        for model_name, agg in models.items():
            row = f"  {model_name:23s}"
            for db in dbs:
                info = agg.get(db, {}).get("biotool_score", {"mean": 0, "std": 0, "n": 0})
                row += f" {_fmt(info['mean'], info['std'], info['n']):>12s}"
            print(row)
        print()


def _print_em_as_table(all_data: Dict, dbs: List[str]) -> None:
    print(f"\n{'=' * 120}")
    print("  Exact Match (EM) & API Success (AS) (%) — Mean ± Std across runs")
    print(f"{'=' * 120}")
    header = f"{'Model':25s}"
    for db in dbs:
        header += f" {'EM':>12s} {'AS':>12s}"
    print(header)
    print("-" * 120)

    for cat_name, models in all_data.items():
        print(f"  [{cat_name}]")
        for model_name, agg in models.items():
            row = f"  {model_name:23s}"
            for db in dbs:
                em_info = agg.get(db, {}).get("em", {"mean": 0, "std": 0, "n": 0})
                as_info = agg.get(db, {}).get("as", {"mean": 0, "std": 0, "n": 0})
                row += f" {_fmt(em_info['mean'], em_info['std'], em_info['n']):>12s}"
                row += f" {_fmt(as_info['mean'], as_info['std'], as_info['n']):>12s}"
            print(row)
        print()


# ======================== CLI ========================

def cmd_evaluate(args: argparse.Namespace) -> None:
    func_mapping = load_function_mapping()
    print(f"Loaded mapping for {len(func_mapping)} functions")

    output_files: List[str] = []
    for pair in args.inputs:
        if ":" not in pair:
            print(f"Error: expected 'input.jsonl:output.json' format, got '{pair}'")
            sys.exit(1)
        input_file, output_file = pair.rsplit(":", 1)
        run_evaluation_phase1(input_file, output_file, func_mapping)
        output_files.append(output_file)

    if args.with_similarity:
        run_similarity_phase2(output_files)

    print("\n[Evaluate] All files processed.")


def cmd_similarity(args: argparse.Namespace) -> None:
    run_similarity_phase2(args.files)


def cmd_metrics(args: argparse.Namespace) -> None:
    db_mapping = load_db_mapping()
    with open(args.file, "r", encoding="utf-8") as f:
        data = json.load(f)
    metrics = compute_metrics(data, db_mapping)
    print_metrics(metrics, os.path.basename(args.file))


def cmd_tables(args: argparse.Namespace) -> None:
    compute_tables_from_config(args.config)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Unified BioTool evaluation script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_eval = subparsers.add_parser("evaluate", help="Evaluate prediction JSONL files")
    p_eval.add_argument(
        "--inputs", nargs="+", required=True,
        help="Input:output pairs in format 'predictions.jsonl:analysis.json'",
    )
    p_eval.add_argument(
        "--with-similarity", action="store_true",
        help="Also compute MedCPT similarity after API calls (needs GPU)",
    )

    p_sim = subparsers.add_parser("similarity", help="Compute MedCPT similarity")
    p_sim.add_argument("--files", nargs="+", required=True, help="Analysis JSON files")

    p_met = subparsers.add_parser("metrics", help="Compute metrics for one file")
    p_met.add_argument("--file", required=True, help="Analysis JSON file")

    p_tab = subparsers.add_parser("tables", help="Generate mean ± std tables")
    p_tab.add_argument("--config", required=True, help="Experiment config JSON")

    args = parser.parse_args()
    {
        "evaluate": cmd_evaluate,
        "similarity": cmd_similarity,
        "metrics": cmd_metrics,
        "tables": cmd_tables,
    }[args.command](args)


if __name__ == "__main__":
    main()
