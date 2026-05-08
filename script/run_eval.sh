#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPT_DIR="${REPO_DIR}/script"
RESULTS_DIR="${REPO_DIR}/results"
ANALYSIS_DIR="${REPO_DIR}/analysis"
mkdir -p "${RESULTS_DIR}" "${ANALYSIS_DIR}"

cmd=${1:-help}
shift || true

case "$cmd" in
  openrouter)
    if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
      echo "ERROR: OPENROUTER_API_KEY must be set." >&2
      exit 1
    fi
    cd "${SCRIPT_DIR}"
    for MODEL in gpt5_1 gpt5_1_codex claude gemini; do
      echo "=== Generating predictions for ${MODEL} ==="
      EVAL_MODEL="${MODEL}" \
      EVAL_OUTPUT_DIR="${RESULTS_DIR}" \
        python openai_eval_func.py
    done
    ;;

  evaluate)
    if [[ $# -eq 0 ]]; then
      echo "Usage: $0 evaluate <pred1.jsonl:out1.json> [pred2.jsonl:out2.json ...]" >&2
      exit 1
    fi
    cd "${REPO_DIR}"
    python "${SCRIPT_DIR}/concurrent_evaluate.py" --inputs "$@" --parallel-evals 2
    ;;

  similarity)
    if [[ $# -eq 0 ]]; then
      echo "Usage: $0 similarity <analysis1.json> [analysis2.json ...]" >&2
      exit 1
    fi
    cd "${REPO_DIR}"
    python "${SCRIPT_DIR}/unified_evaluate.py" similarity --files "$@"
    ;;

  metrics)
    if [[ $# -eq 0 ]]; then
      echo "Usage: $0 metrics <analysis.json>" >&2
      exit 1
    fi
    cd "${REPO_DIR}"
    python "${SCRIPT_DIR}/unified_evaluate.py" metrics --file "$@"
    ;;

  help|--help|-h|"")
    sed -n '2,20p' "$0"
    ;;

  *)
    echo "Unknown command: $cmd" >&2
    sed -n '2,20p' "$0"
    exit 1
    ;;
esac
