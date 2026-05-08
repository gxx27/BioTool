# Data Construction Scripts

These scripts document **how the BioTool dataset was assembled**. They are kept
for transparency and reproducibility; they are **not** required to reproduce
the evaluation numbers in the paper. The output of this pipeline is the cleaned
data already shipped in [`../../data/`](../../data) and on the
[Hugging Face Hub](https://huggingface.co/datasets/gxx27/BioTool).

The intermediate artefacts (`params.json`, `observations/`, `user_queries.json`,
…) are no longer included in this repository — the scripts will regenerate
them when re-run.

## Pipeline overview

```
       ┌─────────────────────────────┐
       │   API-spec JSON files       │
       │   under {ncbi,uniprot,      │
       │   ensembl}/<tool>/          │
       └────────────┬────────────────┘
                    │  build_tool.py
                    ▼
       ┌─────────────────────────────┐
       │   data/tools.json           │  (JSON-Schema tool catalog)
       └────────────┬────────────────┘
                    │  get_observation.py
                    ▼
       ┌─────────────────────────────┐
       │   params.json + observations│  (live API responses, indexed by idx)
       └────────────┬────────────────┘
                    │  gen_user_query.py  (uses prompts.py + few_shot.json)
                    ▼
       ┌─────────────────────────────┐
       │   user_queries.json         │  (two queries per (function, params))
       └────────────┬────────────────┘
                    │  judge_user_query.py     (LLM-as-a-judge filter,
                    │                           keep informative=true)
                    ▼
       ┌─────────────────────────────┐
       │   user_queries_judged.json  │
       └────────────┬────────────────┘
                    │  split_dataset.py    (random 80/20)
                    ▼
       ┌─────────────────────────────┐
       │   train.json / test.json    │
       └────────────┬────────────────┘
                    │  convert.py    (wrap with system prompt + tools)
                    ▼
       ┌─────────────────────────────┐
       │   data/BioTool_{train,test} │
       └─────────────────────────────┘
```

## Files

| File | Purpose |
| --- | --- |
| `build_tool.py` | Build `data/tools.json` from per-tool spec JSONs. |
| `get_observation.py` | Execute every parameter combination against the live BioAPIs to produce `observations/{idx}.txt`. |
| `gen_user_query.py` | Generate two natural-language user queries per (function, params) pair using an LLM with chain-of-thought prompting. |
| `prompts.py` | Two-phase prompt builder used by `gen_user_query.py`. |
| `few_shot.json` | Few-shot examples consumed by `prompts.py`. |
| `judge_user_query.py` | LLM-as-a-judge filter that flags queries whose observation is informative enough to answer them. |
| `split_dataset.py` | Random 80/20 train/test split (sample-level). |
| `convert.py` | Wrap raw conversations with a system prompt and the relevant tool schemas — the format ingested by LLaMA-Factory. |
| `create_db_mapping.py` | Rebuild `data/function_mapping.json` from `tools.json` + `user_queries.json`. |

## Paths

All scripts resolve their paths **relative to the repository root** (two
levels above this directory). They can therefore be run from any clone of the
repo without modification — point the relevant environment variables at the
intermediate artefacts you have on disk if you want to override the defaults.
