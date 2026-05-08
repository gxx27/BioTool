"""
Async OpenRouter function-calling runner for BioTool ShareGPT-style data.
"""

import asyncio
import json
import os
import random
import sys
from typing import Any, Dict, List, Tuple

from openai import AsyncOpenAI
from tqdm import tqdm


# Model mappings
MODEL_MAP = {
    "gpt5_1": "openai/gpt-5.1",
    "gpt5_1_codex": "openai/gpt-5.1-codex",
    "claude": "anthropic/claude-sonnet-4.5",
    "gemini": "google/gemini-3.1-pro-preview",
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(ROOT_DIR, "data")

TOOLS_PATH = os.environ.get("EVAL_TOOLS_PATH", os.path.join(DATA_DIR, "tools.json"))
DATA_PATH = os.environ.get("EVAL_DATA_PATH", os.path.join(DATA_DIR, "BioTool_test.json"))
RESULTS_DIR = os.environ.get("EVAL_OUTPUT_DIR", os.path.join(ROOT_DIR, "results"))

MODEL_KEY = os.environ.get("EVAL_MODEL", "gpt5_1")
MODEL_NAME = os.environ.get("EVAL_MODEL_NAME") or MODEL_MAP.get(MODEL_KEY)
OUTPUT_PATH = os.environ.get(
    "EVAL_OUTPUT_PATH", os.path.join(RESULTS_DIR, f"{MODEL_KEY}.jsonl")
)

CONCURRENCY = int(os.environ.get("EVAL_CONCURRENCY", "16"))
REQUEST_TIMEOUT = float(os.environ.get("EVAL_REQUEST_TIMEOUT", "60"))
MAX_RETRIES = int(os.environ.get("EVAL_MAX_RETRIES", "5"))
RETRY_BACKOFF_BASE = float(os.environ.get("EVAL_RETRY_BACKOFF_BASE", "1.0"))
MAX_SAMPLES = int(os.environ.get("EVAL_MAX_SAMPLES", "0"))

DEFAULT_SYSTEM_PROMPT = (
    "You are a biomedicine function-calling assistant. Always respond by calling exactly one function "
    "from the provided tools with a single tool call. Do not answer with natural language. "
    "If the query is ambiguous, choose the most reasonable default. Fill arguments strictly "
    "according to the JSON schema (correct keys, types, enums); do not include extra keys."
)


def load_tools(path: str) -> List[Dict[str, Any]]:
    with open(os.path.abspath(path), "r", encoding="utf-8") as f:
        return json.load(f)


def load_dataset(path: str) -> List[Dict[str, Any]]:
    abs_path = os.path.abspath(path)
    if abs_path.endswith(".jsonl"):
        data: List[Dict[str, Any]] = []
        with open(abs_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data.append(json.loads(line))
                except Exception:
                    continue
        return data
    with open(abs_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {abs_path}")
    return data


def to_openai_messages(example: Dict[str, Any]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
    ]
    for turn in example.get("conversations", []):
        sender = (turn.get("from") or turn.get("role") or "").lower()
        value = turn.get("value") or turn.get("content") or ""
        if sender in ("human", "user"):
            messages.append({"role": "user", "content": value})
    return messages


def build_gold_label(example: Dict[str, Any]) -> str:
    parts: List[str] = []
    for turn in example.get("conversations", []):
        sender = (turn.get("from") or turn.get("role") or "").lower()
        if sender == "function_call":
            val = (turn.get("value") or "").strip()
            if not val:
                continue
            if "<tool_call>" in val:
                parts.append(val)
            else:
                parts.append("<tool_call>\n" + val + "\n</tool_call>")
    return "\n".join(parts)


def first_user_prompt(messages: List[Dict[str, str]]) -> str:
    for m in messages:
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


async def _call_one(
    index: int,
    example: Dict[str, Any],
    tools: List[Dict[str, Any]],
    client: AsyncOpenAI,
    model_name: str,
) -> Tuple[int, str]:
    messages = to_openai_messages(example)

    # Allow per-example tool subsets if present.
    per_ex_tools = example.get("tools")
    if isinstance(per_ex_tools, str):
        try:
            per_ex_tools = json.loads(per_ex_tools)
        except Exception:
            per_ex_tools = None
    active_tools = per_ex_tools if isinstance(per_ex_tools, list) and per_ex_tools else tools

    for attempt in range(MAX_RETRIES):
        try:
            resp = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=active_tools,
                tool_choice="required",
                timeout=REQUEST_TIMEOUT,
            )
            msg = resp.choices[0].message
            if getattr(msg, "tool_calls", None):
                tool_call = msg.tool_calls[0].function
                try:
                    args_obj = (
                        json.loads(tool_call.arguments)
                        if isinstance(tool_call.arguments, str)
                        else tool_call.arguments
                    )
                except Exception:
                    args_obj = tool_call.arguments
                call_obj = {"name": tool_call.name, "arguments": args_obj}
                predict_str = "<tool_call>\n" + json.dumps(call_obj, ensure_ascii=False) + "\n</tool_call>"
            else:
                predict_str = msg.content or ""

            rec = {
                "prompt": first_user_prompt(messages),
                "predict": predict_str,
                "label": build_gold_label(example),
                "tools": active_tools,
            }
            return index, json.dumps(rec, ensure_ascii=False)
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"[ERROR] index={index} model={model_name} failed after {MAX_RETRIES} attempts: {e}")
                rec = {
                    "prompt": first_user_prompt(messages),
                    "predict": "",
                    "label": build_gold_label(example),
                }
                return index, json.dumps(rec, ensure_ascii=False)
            sleep_s = min(RETRY_BACKOFF_BASE * (2 ** attempt) + random.random() * 0.25, 20.0)
            await asyncio.sleep(sleep_s)


async def async_main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    if not MODEL_NAME:
        print(
            f"ERROR: Unknown EVAL_MODEL='{MODEL_KEY}'. Set EVAL_MODEL_NAME or use one of: "
            f"{', '.join(MODEL_MAP)}",
            file=sys.stderr,
        )
        sys.exit(1)

    tools = load_tools(TOOLS_PATH)
    data = load_dataset(DATA_PATH)
    if MAX_SAMPLES > 0:
        data = data[:MAX_SAMPLES]

    out_dir = os.path.dirname(os.path.abspath(OUTPUT_PATH))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    client = AsyncOpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded_call(idx: int, ex: Dict[str, Any]) -> Tuple[int, str]:
        async with sem:
            return await _call_one(idx, ex, tools, client, MODEL_NAME)

    tasks = [asyncio.create_task(bounded_call(i, ex)) for i, ex in enumerate(data)]

    next_to_write = 0
    pending: Dict[int, str] = {}
    out_path = os.path.abspath(OUTPUT_PATH)
    print(f"Writing predictions to {out_path}")
    with open(out_path, "w", encoding="utf-8") as fout, tqdm(total=len(tasks)) as pbar:
        for fut in asyncio.as_completed(tasks):
            idx, line = await fut
            pending[idx] = line
            while next_to_write in pending:
                fout.write(pending.pop(next_to_write) + "\n")
                next_to_write += 1
            pbar.update(1)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
