# LLaMA-Factory Configs

These YAML files reproduce **all open-source training and inference runs**
reported in the BioTool paper. They are designed to be dropped into a
[LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory) checkout and run via
`llamafactory-cli train <config.yaml>`.

## Configs

| YAML | Model | Mode | Output dir |
| --- | --- | --- | --- |
| `qwen3_4b.yaml` | Qwen3-4B-Instruct | full SFT | `saves/qwen3_4b/full/sft` |
| `qwen3_4b_predict.yaml` | (loads the SFT'd Qwen3-4B above) | inference on test split | `saves/qwen3_4b/full/predict` |
| `qwen3_8b_lora.yaml` | Qwen3-8B | LoRA SFT | `saves/qwen3_8b/lora/sft` |
| `qwen3_8b_lora_predict.yaml` | Qwen3-8B + adapter | inference | `saves/qwen3_8b/lora/predict` |
| `qwen2_5_7b_lora.yaml` | Qwen2.5-7B-Instruct | LoRA SFT | `saves/qwen2_5_7b/lora/sft` |
| `qwen2_5_7b_lora_predict.yaml` | Qwen2.5-7B + adapter | inference | `saves/qwen2_5_7b/lora/predict` |
| `llama3_1_8b_lora.yaml` | Llama-3.1-8B-Instruct | LoRA SFT | `saves/llama3_1_8b/lora/sft` |
| `llama3_1_8b_lora_predict.yaml` | Llama-3.1-8B + adapter | inference | `saves/llama3_1_8b/lora/predict` |

The headline model in the paper is **Qwen3-4B fully fine-tuned on
`BioTool_train.json`** (`qwen3_4b.yaml`), released on the Hugging Face Hub as
[`gxx27/BioTool-finetuned-Qwen3-4B`](https://huggingface.co/gxx27/BioTool-finetuned-Qwen3-4B).

## How to use these configs

1. **Clone LLaMA-Factory** and install its dependencies:
   ```bash
   git clone https://github.com/hiyouga/LLaMA-Factory.git
   cd LLaMA-Factory
   pip install -e ".[torch,metrics]"
   ```

2. **Copy the BioTool data into LLaMA-Factory's `data/` directory:**
   ```bash
   cp /path/to/BioAPI/data/BioTool_train.json LLaMA-Factory/data/train.json
   cp /path/to/BioAPI/data/BioTool_test.json  LLaMA-Factory/data/test.json
   ```

3. **Register both splits in `LLaMA-Factory/data/dataset_info.json`** by adding
   the following two entries:
   ```json
   "train_biotool": {
     "file_name": "train.json",
     "formatting": "sharegpt",
     "columns": {
       "messages": "conversations",
       "system": "system",
       "tools": "tools"
     }
   },
   "test_biotool": {
     "file_name": "test.json",
     "formatting": "sharegpt",
     "columns": {
       "messages": "conversations",
       "system": "system",
       "tools": "tools"
     }
   }
   ```

4. **Copy the configs you want to run** into LLaMA-Factory's example tree, e.g.
   ```bash
   cp /path/to/BioAPI/llamafactory_cfgs/qwen3_4b.yaml          LLaMA-Factory/examples/train_full/
   cp /path/to/BioAPI/llamafactory_cfgs/qwen3_4b_predict.yaml  LLaMA-Factory/examples/train_full/
   cp /path/to/BioAPI/llamafactory_cfgs/*lora*.yaml            LLaMA-Factory/examples/train_lora/
   ```

5. **Train, then run inference:**
   ```bash
   # Full SFT of Qwen3-4B
   llamafactory-cli train examples/train_full/qwen3_4b.yaml

   # Generate predictions on the held-out BioTool test split
   llamafactory-cli train examples/train_full/qwen3_4b_predict.yaml
   # -> saves/qwen3_4b/full/predict/generated_predictions.jsonl
   ```

6. **Score the predictions** with the BioTool evaluation pipeline:
   ```bash
   cd /path/to/BioAPI
   bash script/run_eval.sh evaluate \
       LLaMA-Factory/saves/qwen3_4b/full/predict/generated_predictions.jsonl:analysis/qwen3_4b.json
   bash script/run_eval.sh similarity analysis/qwen3_4b.json
   bash script/run_eval.sh metrics    analysis/qwen3_4b.json
   ```
