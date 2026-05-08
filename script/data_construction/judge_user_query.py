"""
Judge whether each generated user query is answerable given the corresponding observation.
"""

import json
import os
import random
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(SCRIPT_DIR))

INPUT_PATH = os.environ.get("JUDGE_INPUT_PATH", os.path.join(BASE_DIR, "user_queries.json"))
OBS_DIR = os.environ.get("JUDGE_OBS_DIR", os.path.join(BASE_DIR, "observations"))
OUTPUT_PATH = os.environ.get("JUDGE_OUTPUT_PATH", os.path.join(BASE_DIR, "user_queries_judged.json"))

MODEL_NAME = os.environ.get("JUDGE_LLM_MODEL", "claude-haiku-4-5-20251001")
TEST_NUM = int(os.environ.get("JUDGE_TEST_NUM", "0"))

MAX_RETRIES = int(os.environ.get("JUDGE_MAX_RETRIES", "3"))
RETRY_BACKOFF_BASE = float(os.environ.get("JUDGE_RETRY_BACKOFF_BASE", "0.8"))
MAX_OBS_CHARS = int(os.environ.get("JUDGE_MAX_OBS_CHARS", "12000"))
DEBUG_PRINT = os.environ.get("JUDGE_DEBUG_PRINT", "0") not in ("0", "false", "False", "")


def _load_json(path: str) -> Any:
    with open(os.path.abspath(path), "r", encoding="utf-8") as f:
        return json.load(f)


def _dump_json(path: str, obj: Any) -> None:
    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(os.path.abspath(path), "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_observation_result(obs_idx: int) -> Dict[str, Any]:
    obs_path = os.path.join(os.path.abspath(OBS_DIR), f"{obs_idx}.txt")
    try:
        with open(obs_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"error": "Function call result not available", "obs_path": obs_path}


def _truncate_text(s: str, max_chars: int) -> str:
    s = s or ""
    if max_chars <= 0 or len(s) <= max_chars:
        return s
    head = max_chars - 200 if max_chars > 400 else max_chars
    tail = 180 if max_chars > 400 else 0
    if tail <= 0:
        return s[:head] + "\n[TRUNCATED]"
    return s[:head] + "\n...[TRUNCATED]...\n" + s[-tail:]


def flatten_user_queries(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flat: List[Dict[str, Any]] = []
    qidx = 1
    for rec in items:
        obs_idx = rec.get("idx", 0)
        queries = rec.get("queries", [])
        if not isinstance(queries, list):
            queries = []
        for pos, q in enumerate(queries[:2]):
            if not isinstance(q, str):
                continue
            q = q.strip()
            if not q:
                continue
            out = dict(rec)
            out.pop("queries", None)
            out["query_idx"] = qidx
            out["obs_idx"] = obs_idx
            out["query"] = q
            flat.append(out)
            qidx += 1
    return flat


def build_judge_prompts(query: str, observation: Dict[str, Any]) -> Tuple[str, str]:
    sys_prompt = (
        "You are an evaluator for dataset filtering.\n"
        "Goal: decide whether the OBSERVATION is informative (useful) for answering the USER QUERY.\n"
        "IMPORTANT CONTEXT: Observations are POSTPROCESSED SUMMARIES (often partial). This is NOT a strict completeness check.\n"
        "Be concise and deterministic."
    )
    obs_json = json.dumps(observation, ensure_ascii=False, indent=2)
    obs_json = _truncate_text(obs_json, MAX_OBS_CHARS)
    user_prompt = f"""
USER QUERY:
{query}

OBSERVATION (tool output / retrieved data):
{obs_json}

RUBRIC (use this, do not be overly strict):
1) informative=true if the observation contains at least ONE relevant, non-trivial fact that can be used to answer part of the query without inventing details.
   - Examples/partial lists still count (you can answer with examples + mention it's partial).
   - Counts/aggregates/summaries still count (you can answer with summary + mention missing specifics).
   - If the query asks "which X" but the observation only gives a count or a few examples, that is still informative=true (partial answer).
2) informative=false ONLY when:
   - observation is an error / empty / placeholder, OR
   - observation content is clearly unrelated to the query intent, OR
   - observation is too vague to support even a single concrete statement relevant to the query.

When writing the reason:
- Focus on what CAN be answered using the observation (even partially).
- If partial, put the missing parts into limitations, but do NOT flip to false just because it's incomplete.
- Be concise and specific (name the fields/signals you used, e.g., examples, totals, taxonomy counts).

OUTPUT FORMAT (do NOT output JSON; output exactly these lines):
INFORMATIVE: true|false
REASON: <short reason>
LIMITATIONS: <optional; if none, write "none">
""".strip()
    return sys_prompt, user_prompt


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    # Strip fenced blocks if present
    if "```" in text:
        parts = text.split("```")
        # pick the largest middle chunk as likely JSON
        mid = ""
        for p in parts[1:-1]:
            if len(p) > len(mid):
                mid = p
        text = mid.strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    # Try direct JSON parse
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    # Fallback: find first {...} region
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            obj = json.loads(text[start : end + 1])
            return obj if isinstance(obj, dict) else None
        except Exception:
            return None
    return None


def _parse_judge_output(text: str) -> Tuple[Optional[bool], str]:
    """
    Parse model output into (informative, reason).
    We accept either JSON or a simple line-based format and fall back to regex.
    """
    text = (text or "").strip()
    if not text:
        return None, ""

    # 1) Try JSON (backward compatible if model still outputs JSON).
    parsed = _extract_json_object(text)
    if parsed:
        inf_val = parsed.get("informative")
        informative = bool(inf_val) if isinstance(inf_val, (bool, int)) else None
        if isinstance(inf_val, str):
            informative = inf_val.strip().lower() in ("true", "yes", "1")
        reason = parsed.get("reason")
        if not isinstance(reason, str):
            reason = ""
        return informative, reason.strip()

    # 2) Line-based format / regex
    m = re.search(r"(?im)^\s*informative\s*[:=]\s*(true|false|yes|no|1|0)\s*$", text)
    informative: Optional[bool] = None
    if m:
        tok = m.group(1).strip().lower()
        informative = tok in ("true", "yes", "1")
    else:
        # sometimes the model replies with just "true" / "false"
        t0 = text.strip().lower()
        if t0 in ("true", "false", "yes", "no"):
            informative = t0 in ("true", "yes")

    reason = ""
    rm = re.search(r"(?ims)^\s*reason\s*[:=]\s*(.+?)(?:\n\s*limitations\s*[:=]|\Z)", text)
    if rm:
        reason = rm.group(1).strip()
    else:
        # fallback: first non-empty line that isn't INFORMATIVE/LIMITATIONS
        for ln in text.splitlines():
            ln2 = ln.strip()
            if not ln2:
                continue
            if re.match(r"(?i)^(informative|limitations)\s*[:=]", ln2):
                continue
            reason = ln2
            break

    return informative, reason.strip()


def _anthropic_client():
    import anthropic  # type: ignore
    # Prefer Anthropic's default env-based auth (ANTHROPIC_API_KEY)
    return anthropic.Anthropic()


def judge_one(query: str, observation: Dict[str, Any], client) -> Tuple[bool, str]:
    sys_prompt, user_prompt = build_judge_prompts(query, observation)

    for attempt in range(MAX_RETRIES):
        try:
            msg = client.messages.create(
                model=MODEL_NAME,
                max_tokens=200,
                temperature=0,
                system=sys_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            # anthropic SDK returns content blocks; join text
            content_text = ""
            for block in getattr(msg, "content", []) or []:
                if getattr(block, "type", None) == "text":
                    content_text += getattr(block, "text", "") or ""
            content_text = (content_text or "").strip()

            informative_opt, reason = _parse_judge_output(content_text)
            if informative_opt is None:
                raise ValueError("Model output not parseable (no informative field)")
            if not reason:
                reason = "No reason provided."
            return informative_opt, reason
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                return False, f"Judge parse/call error: {type(e).__name__}: {e}"
            sleep_s = min(RETRY_BACKOFF_BASE * (2**attempt) + random.random() * 0.25, 20.0)
            time.sleep(sleep_s)


def main() -> None:
    items = _load_json(INPUT_PATH)
    if not isinstance(items, list):
        raise ValueError(f"Expected list in {INPUT_PATH}, got {type(items).__name__}")

    flat = flatten_user_queries(items)
    if TEST_NUM > 0:
        flat = flat[:TEST_NUM]

    client = _anthropic_client()

    out: List[Dict[str, Any]] = []
    for i, rec in tqdm(enumerate(flat), total=len(flat), desc="Judging user queries"):
        obs_idx = int(rec.get("obs_idx", rec.get("idx", 0)) or 0)
        observation = load_observation_result(obs_idx)
        query = str(rec.get("query") or "").strip()
        informative, reason = judge_one(query, observation, client)

        rec_out = dict(rec)
        rec_out["informative"] = informative
        rec_out["informative_reason"] = reason
        out.append(rec_out)

        if DEBUG_PRINT and i < 3:
            sys_prompt, user_prompt = build_judge_prompts(query, observation)
            print("=" * 80)
            print(f"[debug] query_idx={rec_out.get('query_idx')} obs_idx={obs_idx}")
            print("[debug] system:", sys_prompt)
            print("[debug] user:", user_prompt[:1500])
            print("[debug] result:", {"informative": informative, "reason": reason})

    _dump_json(OUTPUT_PATH, out)
    print(f"Wrote {len(out)} judged queries to {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    main()


