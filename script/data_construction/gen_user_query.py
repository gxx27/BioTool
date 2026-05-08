"""
Generate the user queries for the dataset with access to the API.

With multiple requests at the same time to the API to speed up the process.
"""

import asyncio
import json
import os
import random
from typing import Any, Dict, List, Tuple

from tqdm import tqdm
from openai import AsyncOpenAI
from prompts import build_prompts, parse_cot_response


# Paths (relative to the repository root, two levels above this file).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))
PARAMS_PATH = os.path.join(BASE_DIR, "params.json")
TOOLS_PATH = os.path.join(BASE_DIR, "data", "tools.json")
FEW_SHOT_PATH = os.path.join(SCRIPT_DIR, "few_shot.json")
OBSERVATIONS_DIR = os.path.join(BASE_DIR, "observations")
OUTPUT_PATH = os.path.join(BASE_DIR, "user_queries.json")

# Model/config
MODEL_NAME = os.environ.get("GEN_LLM_MODEL", "o3-2025-04-16")
TEST_NUM = int(os.environ.get("GEN_TEST_NUM", "0"))

# Concurrency/retries
CONCURRENCY = int(os.environ.get("GEN_CONCURRENCY", "16"))
REQUEST_TIMEOUT = float(os.environ.get("GEN_REQUEST_TIMEOUT", "60"))
MAX_RETRIES = int(os.environ.get("GEN_MAX_RETRIES", "5"))
RETRY_BACKOFF_BASE = float(os.environ.get("GEN_RETRY_BACKOFF_BASE", "0.8"))


def _load_json(path: str) -> Any:
    with open(os.path.abspath(path), "r", encoding="utf-8") as f:
        return json.load(f)


def _build_func_docs(tools_items: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    func_docs: Dict[str, Dict[str, Any]] = {}
    for entry in tools_items:
        fn = entry.get("function") or {}
        name = fn.get("name")
        if isinstance(name, str):
            func_docs[name] = fn
    return func_docs


def load_observation_result(idx: int) -> Dict[str, Any]:
    observation_path = os.path.join(OBSERVATIONS_DIR, f"{idx}.txt")
    try:
        with open(observation_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"error": "Function call result not available"}


def _to_messages(doc: Dict[str, Any], params: Dict[str, Any], few_shot_items: List[Dict[str, Any]], observation_result: Dict[str, Any]) -> List[Dict[str, str]]:
    sys_prompt, user_prompt = build_prompts(doc, params, few_shot_items, observation_result)
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _parse_questions(content: str) -> List[str]:
    content = (content or "").strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            queries = [str(x).strip() for x in data if isinstance(x, str)]
            if len(queries) >= 2 and queries[0] and queries[1] and queries[0] != queries[1]:
                return queries[:2]
    except Exception:
        pass
    lines = [ln.strip("- •\t ") for ln in content.splitlines() if ln.strip()]
    uniq: List[str] = []
    for ln in lines:
        if ln and ln not in uniq:
            uniq.append(ln)
        if len(uniq) == 2:
            break
    return uniq[:2]


async def _call_one(index: int, rec: Dict[str, Any], func_docs: Dict[str, Dict[str, Any]], few_shot_items: List[Dict[str, Any]], client: AsyncOpenAI) -> Tuple[int, Dict[str, Any]]:
    fn_name = rec.get("function")
    params = rec.get("params")
    doc = func_docs.get(fn_name, {})
    idx = rec.get("idx", 0)

    observation_result = load_observation_result(idx)
    messages = _to_messages(doc, params, few_shot_items, observation_result)

    for attempt in range(MAX_RETRIES):
        try:
            for i in range(5):
                resp = await client.chat.completions.create(
                    model=MODEL_NAME,
                        messages=messages,
                        timeout=REQUEST_TIMEOUT,
                    )
                content = (resp.choices[0].message.content or "").strip()
                questions = parse_cot_response(content)

                if len(questions) == 2 and len(questions[0]) > 10 and len(questions[1]) > 10:
                    break

            out = {
                "database": rec.get("database"),
                "tool": rec.get("tool"),
                "function": fn_name,
                "params": params,
                "queries": questions,
                "idx": rec.get("idx"),
            }
            return index, out
        except Exception:
            if attempt == MAX_RETRIES - 1:
                out = {
                    "database": rec.get("database"),
                    "tool": rec.get("tool"),
                    "function": fn_name,
                    "params": params,
                    "queries": [],
                    "idx": rec.get("idx"),
                }
                return index, out
            await asyncio.sleep(min(RETRY_BACKOFF_BASE * (2 ** attempt) + random.random() * 0.25, 10.0))


async def async_main() -> None:
    params_items: List[Dict[str, Any]] = _load_json(PARAMS_PATH)
    tools_items: List[Dict[str, Any]] = _load_json(TOOLS_PATH)
    few_shot_items: List[Dict[str, Any]] = _load_json(FEW_SHOT_PATH)

    func_docs = _build_func_docs(tools_items)

    rnd = random.Random()
    rnd.shuffle(params_items)
    if TEST_NUM > 0:
        params_items = params_items[:TEST_NUM]

    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY")
    )

    sem = asyncio.Semaphore(CONCURRENCY)

    async def bounded_call(idx: int, rec: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        async with sem:
            return await _call_one(idx, rec, func_docs, few_shot_items, client)

    tasks = [asyncio.create_task(bounded_call(i, rec)) for i, rec in enumerate(params_items)]

    # Ordered writes with progress bar
    next_to_write = 0
    pending: Dict[int, Dict[str, Any]] = {}
    out_path = os.path.abspath(OUTPUT_PATH)
    with open(out_path, "w", encoding="utf-8") as fout, tqdm(total=len(tasks)) as pbar:
        fout.write("[\n")
        first = True
        for fut in asyncio.as_completed(tasks):
            idx, item = await fut
            pending[idx] = item
            while next_to_write in pending:
                rec = pending.pop(next_to_write)
                line = json.dumps(rec, ensure_ascii=False, indent=2)
                if first:
                    fout.write(line)
                    first = False
                else:
                    fout.write(",\n" + line)
                next_to_write += 1
                pbar.update(1)
        fout.write("\n]\n")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()


