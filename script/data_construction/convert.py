"""
Wrap raw conversations from `split_dataset.py` with a system prompt and the
relevant tool schemas so the dataset is ready for LLaMA-Factory ingestion.
"""

import argparse
import json
import os
import random
from typing import Any, Dict, List


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
DATA_DIR = os.path.join(REPO_DIR, "data")

DEFAULT_TOOLS_PATH = os.path.join(DATA_DIR, "tools.json")
DEFAULT_TRAIN_INPUT = os.path.join(DATA_DIR, "train.json")
DEFAULT_TEST_INPUT = os.path.join(DATA_DIR, "test.json")
DEFAULT_TRAIN_OUTPUT = os.path.join(DATA_DIR, "BioTool_train.json")
DEFAULT_TEST_OUTPUT = os.path.join(DATA_DIR, "BioTool_test.json")

DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant that can call tools. "
    "Use the provided tools when appropriate."
)


def load_tools(tools_path: str) -> List[Dict[str, Any]]:
    with open(tools_path, "r", encoding="utf-8") as f:
        return json.load(f)


def select_random_tool(tools: List[Dict[str, Any]], exclude_name: str = "esearch") -> Dict[str, Any]:
    available = [t for t in tools if t["function"]["name"] != exclude_name]
    return random.choice(available)


def process_conversations(
    input_file: str,
    output_file: str,
    system_prompt: str,
    tool_pool: List[Dict[str, Any]],
    random_tool: Dict[str, Any],
) -> None:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    processed: List[Dict[str, Any]] = []
    for item in data:
        gold_name = json.loads(item["conversations"][1]["value"])["name"]
        fixed_tool = next(
            (t for t in tool_pool if t["function"]["name"] == gold_name), None
        )
        if fixed_tool is None:
            continue
        processed.append({
            "conversations": [
                {"from": "system", "value": system_prompt},
                *item["conversations"][:-1],
            ],
            "tools": json.dumps([fixed_tool, random_tool]),
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools_path", default=DEFAULT_TOOLS_PATH)
    parser.add_argument("--train_input", default=DEFAULT_TRAIN_INPUT)
    parser.add_argument("--train_output", default=DEFAULT_TRAIN_OUTPUT)
    parser.add_argument("--test_input", default=DEFAULT_TEST_INPUT)
    parser.add_argument("--test_output", default=DEFAULT_TEST_OUTPUT)
    parser.add_argument("--system_prompt", default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    tools = load_tools(args.tools_path)
    random_tool = select_random_tool(tools)

    print(f"Processing {args.train_input} ...")
    process_conversations(args.train_input, args.train_output, args.system_prompt, tools, random_tool)
    print(f"  -> {args.train_output}")

    print(f"Processing {args.test_input} ...")
    process_conversations(args.test_input, args.test_output, args.system_prompt, tools, random_tool)
    print(f"  -> {args.test_output}")


if __name__ == "__main__":
    main()
