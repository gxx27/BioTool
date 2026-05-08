"""
Concurrent BioTool evaluation with BLAST/non-BLAST queue separation.
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unified_evaluate import (  # type: ignore
    API_RATE_LIMIT_DELAY,
    call_bioapi_function,
    extract_tool_call,
    load_function_mapping,
    load_predictions,
    normalize_function_call,
)


def is_blast_label(prediction: dict) -> bool:
    label_call = extract_tool_call(prediction.get("label", ""))
    return bool(label_call) and label_call.get("name", "").lower() == "blast"


def evaluate_single(prediction: dict, func_mapping: dict) -> dict:
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

    if predict_call:
        fname = predict_call.get("name", "")
        params = predict_call.get("arguments", {})
        ok, resp = call_bioapi_function(fname, params, func_mapping)
        result["predict_response"] = resp if ok else None
        time.sleep(API_RATE_LIMIT_DELAY)

    if label_call:
        fname = label_call.get("name", "")
        params = label_call.get("arguments", {})
        ok, resp = call_bioapi_function(fname, params, func_mapping)
        result["label_response"] = resp if ok else None
        time.sleep(API_RATE_LIMIT_DELAY)

    result["api_success"] = (
        result["predict_response"] is not None and result["label_response"] is not None
    )
    return result


def _worker(
    tag: str,
    items: list,
    results: list,
    func_mapping: dict,
    counter: dict,
    lock: threading.Lock,
    total: int,
) -> None:
    """Process a queue of (index, prediction) tuples."""
    for idx, pred in items:
        results[idx] = evaluate_single(pred, func_mapping)
        with lock:
            counter["done"] += 1
            done = counter["done"]
        if done % 50 == 0 or done == total:
            em = sum(1 for x in results if x and x.get("exact_match"))
            api = sum(1 for x in results if x and x.get("api_success"))
            print(f"  [{tag}] {done}/{total} done (EM={em}, API={api})")


def evaluate_file(input_file: str, output_file: str, func_mapping: dict) -> str:
    basename = os.path.basename(input_file)
    predictions = load_predictions(input_file)
    n = len(predictions)

    blast_items, non_blast_items = [], []
    for i, pred in enumerate(predictions):
        if is_blast_label(pred):
            blast_items.append((i, pred))
        else:
            non_blast_items.append((i, pred))

    tag = basename.replace(".jsonl", "")
    print(f"\n[{tag}] Starting: {n} total ({len(blast_items)} BLAST, {len(non_blast_items)} non-BLAST)")

    results: list = [None] * n
    counter = {"done": 0}
    lock = threading.Lock()

    t_blast = threading.Thread(
        target=_worker,
        args=(f"{tag}/BLAST", blast_items, results, func_mapping, counter, lock, n),
        daemon=True,
    )
    t_non = threading.Thread(
        target=_worker,
        args=(f"{tag}/other", non_blast_items, results, func_mapping, counter, lock, n),
        daemon=True,
    )

    start = time.time()
    t_blast.start()
    t_non.start()
    t_blast.join()
    t_non.join()
    elapsed = time.time() - start

    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    em = sum(1 for r in results if r and r.get("exact_match"))
    api = sum(1 for r in results if r and r.get("api_success"))
    print(f"[{tag}] DONE in {elapsed:.0f}s — {em} EM, {api} API success → {output_file}")
    return output_file


def run_batch(pairs: list, func_mapping: dict, parallel_evals: int) -> list:
    """Run multiple file evaluations in parallel."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    output_files = []
    with ThreadPoolExecutor(max_workers=parallel_evals) as pool:
        futures = {
            pool.submit(evaluate_file, inp, out, func_mapping): (inp, out)
            for inp, out in pairs
        }
        for fut in as_completed(futures):
            inp, _ = futures[fut]
            try:
                output_files.append(fut.result())
            except Exception as e:
                print(f"[ERROR] {inp}: {e}")
    return output_files


def main() -> None:
    parser = argparse.ArgumentParser(description="Concurrent BioTool evaluation")
    parser.add_argument(
        "--inputs", nargs="+", required=True,
        help='Input:output pairs "predictions.jsonl:analysis.json"',
    )
    parser.add_argument(
        "--parallel-evals", type=int, default=2,
        help="Number of file evaluations to run in parallel (each uses 2 workers).",
    )
    args = parser.parse_args()

    print(f"[{datetime.now():%H:%M:%S}] Loading function mapping...")
    func_mapping = load_function_mapping()
    print(f"  Loaded {len(func_mapping)} functions")

    pairs = []
    for spec in args.inputs:
        if ":" not in spec:
            print(f"Error: expected 'input.jsonl:output.json', got '{spec}'")
            sys.exit(1)
        inp, out = spec.rsplit(":", 1)
        pairs.append((inp, out))

    print(f"\n[{datetime.now():%H:%M:%S}] Starting {len(pairs)} evaluations ({args.parallel_evals} in parallel)")
    print(f"  Total concurrent API calls: {args.parallel_evals} evals × 2 workers = {args.parallel_evals * 2}")

    t0 = time.time()
    output_files = run_batch(pairs, func_mapping, args.parallel_evals)
    print(f"\n[{datetime.now():%H:%M:%S}] All done in {time.time() - t0:.0f}s")
    print(f"  Output files: {output_files}")


if __name__ == "__main__":
    main()
