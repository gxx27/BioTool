# Scripts

The `script/` directory hosts everything required to **reproduce the experiments
in the BioTool paper**. The auxiliary scripts that were used to **construct the
dataset itself** live in [`data_construction/`](./data_construction).

## Core evaluation scripts

| File | Purpose |
| --- | --- |
| [`openai_eval_func.py`](./openai_eval_func.py) | Generate tool-calling predictions for closed-source models (GPT-5.1, GPT-5.1-Codex, Claude Sonnet 4.5, Gemini 3.1 Pro) through the OpenRouter API. |
| [`unified_evaluate.py`](./unified_evaluate.py) | The single entry-point for evaluation. Exposes four sub-commands — `evaluate` (Exact-Match + live BioAPI calls), `similarity` (MedCPT response-similarity scoring), `metrics` (per-database EM / AS / BioTool Score), and `tables` (mean ± std across runs). |
| [`concurrent_evaluate.py`](./concurrent_evaluate.py) | Parallel evaluation driver that splits each prediction file into a slow BLAST queue and a fast non-BLAST queue. Reuses `unified_evaluate.py` for the actual scoring. |
| [`run_eval.sh`](./run_eval.sh) | Convenience wrapper around the three scripts above. |

## End-to-end pipeline

```bash
# 1. Generate predictions for the four closed-source baselines via OpenRouter.
export OPENROUTER_API_KEY=<your_key>
bash script/run_eval.sh openrouter

# 2. Generate predictions for fine-tuned / direct-inference open-source models
#    using LLaMA-Factory and the configs in `llamafactory_cfgs/`.
#    See `llamafactory_cfgs/README.md` for instructions.

# 3. Score every prediction JSONL file (Exact Match + live BioAPI calls).
bash script/run_eval.sh evaluate \
    results/gpt5_1.jsonl:analysis/gpt5_1.json \
    results/claude.jsonl:analysis/claude.json

# 4. Add MedCPT response-level similarity (needs GPU briefly).
bash script/run_eval.sh similarity analysis/gpt5_1.json analysis/claude.json

# 5. Inspect the metrics for any single analysis file.
bash script/run_eval.sh metrics analysis/gpt5_1.json
```

All four operations are exposed as native sub-commands on
`unified_evaluate.py` (`evaluate`, `similarity`, `metrics`, `tables`); see the
docstring at the top of the file.

## Data dependencies

`unified_evaluate.py` and `openai_eval_func.py` read from `data/` only:

- `data/tools.json` — JSON-Schema list of all 127 BioTool tools.
- `data/BioTool_test.json` — the held-out test split (1,408 samples).
- `data/function_mapping.json` — function-name → `{database, tool}` map used
  to dispatch live BioAPI calls and bucket metrics by database.

No other repo-level files are required at evaluation time.
