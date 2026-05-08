"""
Prompts for generating user queries - v2 with instruction-based learning.
Addresses underfit (unanswerable) and overfit (too specific) problems.
"""

import json
import re
from typing import Any, Dict, Iterable, List, Tuple


def _iter_str_values(obj: Any) -> Iterable[str]:
    """Recursively yield all string values from nested dict/list structures."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_str_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _iter_str_values(v)


# Keep regex patterns for well-defined identifiers (mechanical extraction only)
_ARTIFACT_PATTERNS = [
    r"\b[A-Z0-9]{6,}\b",             # Longer IDs/accessions
    r"\brs\d+\b",                     # SNP IDs
    r"\bDI-\d+\b",                    # Disease IDs
    r"\bKW-\d+\b",                    # Keyword IDs
    r"\b[A-Z]{1,3}_\d+(?:\.\d+)?\b",  # RefSeq-like
]
_RE_ARTIFACTS = [re.compile(p) for p in _ARTIFACT_PATTERNS]


def _looks_like_sequence(x: str) -> bool:
    x2 = x.strip()
    return x2.startswith(">") or re.fullmatch(r"[ACGTURYKMSWBDHVNX\-]{40,}", x2, flags=re.I) is not None


def _looks_like_coords(x: str) -> bool:
    return re.fullmatch(r"[A-Za-z0-9_]+:\d{3,}(?:-\d{3,})?", x.strip()) is not None


def extract_identifiers(params: Dict[str, Any]) -> List[str]:
    """
    Extract biological identifiers that should appear verbatim.
    Only extracts well-defined patterns - judgment calls left to LLM.
    """
    tokens, seen = [], set()
    for key, val in params.items():
        for s in _iter_str_values(val):
            for r in _RE_ARTIFACTS:
                for m in r.findall(s):
                    if m not in seen:
                        tokens.append(m)
                        seen.add(m)
            if (_looks_like_sequence(s) or _looks_like_coords(s)) and s not in seen:
                tokens.append(s)
                seen.add(s)
    return tokens


def _format_few_shot_examples(few_shot_items: List[Dict[str, Any]]) -> str:
    """Format few-shot examples for the prompt."""
    examples: List[Dict[str, Any]] = []
    for item in few_shot_items:
        queries = item.get("queries", [])
        fn_name = item.get("function")
        params = item.get("params")
        if not (queries and isinstance(fn_name, str) and isinstance(params, dict)):
            continue
        for user_q in queries[:2]:
            user_q = user_q.strip()
            if user_q:
                examples.append({
                    "user_query": user_q,
                    "function_call": {"name": fn_name, "arguments": params}
                })
    return json.dumps(examples[:10], ensure_ascii=False, indent=2)


def _format_function_doc(doc: Dict[str, Any]) -> str:
    """Format function documentation for the prompt."""
    if not doc:
        return "(no documentation available)"
    
    name = doc.get("name", "unknown")
    description = doc.get("description", "")
    
    # Extract parameter descriptions from schema if available
    params_schema = doc.get("parameters", {})
    props = params_schema.get("properties", {})
    
    param_desc_lines = []
    for pname, pinfo in props.items():
        pdesc = pinfo.get("description", "")
        ptype = pinfo.get("type", "")
        param_desc_lines.append(f"  - {pname} ({ptype}): {pdesc[:100]}..." if len(pdesc) > 100 else f"  - {pname} ({ptype}): {pdesc}")
    
    param_block = "\n".join(param_desc_lines[:10]) if param_desc_lines else "  (no parameter descriptions)"
    
    return f"""Function: {name}
Description: {description}
Parameters:
{param_block}"""


def build_prompts(
    doc: Dict[str, Any],
    params: Dict[str, Any],
    few_shot_items: List[Dict[str, Any]],
    observation_result: Dict[str, Any]

) -> Tuple[str, str]:
    """
    Build system and user prompts for query generation.
    Uses chain-of-thought with instruction-based parameter classification.
    """

    identifiers = extract_identifiers(params)
    sys_prompt = """You generate realistic biomedical questions that researchers naturally ask.

TASK OVERVIEW: TWO-PHASE REASONING
---
Phase 1 - ANALYZE: Map technical parameters to natural language concepts (Qualitative Mapping).
Phase 2 - GENERATE: Create TWO questions (one Broad/Implicit, one Specific/Qualitative).

PHASE 1: PARAMETER MAPPING & ABSTRACTION
---
Do not simply list parameters. You must translate *Data* into *Language*.

1. VERBATIM (Keep Exact):
   - Unique identifiers (gene symbols, rsIDs, accessions).
   - Raw sequences (FASTA format).
   - Coordinates (e.g., "chr1:100-200").

2. QUALITATIVE MAPPING (Translate Numbers/Codes):
   - **Thresholds (d_prime, score, e-value, p-value):**
     - Map high/strict numbers to adjectives like "strong", "significant", "conserved", or "best".
     - *Example:* `d_prime=0.8` -> "strong linkage" (Do not say "0.8" unless asking for a specific cutoff).
     - *Example:* `limit=5` -> "top 5" or "primary results".
   - **Complex Codes (Populations/Sources):**
     - Simplify technical strings to common terms.
     - *Example:* `1000GENOMES:phase_3:CDX` -> "CDX population" or "1000 Genomes data".

3. IMPLICIT DEFAULTS (Selectively Omit):
   - Many parameters (e.g., `sort=relevance`, `format=json`, `retmax=20`) represent "good default behavior."
   - **Rule:** If a parameter just ensures the result is usable, OMIT it from the text. The user implies "good results" by asking the question.

PHASE 2: QUESTION GENERATION STRATEGY
---
Your goal is **Tool Bias**: The question should be specific enough that *this tool* is the logical choice to answer it, without explicitly naming the tool.

**Question 1: The "Implicit" Question (Natural & Broad)**
   - **Goal:** A question a biologist asks a colleague.
   - **Technique:** Hide the strict parameters. Assume the tool's filters are the "correct" way to answer the broad intent.
   - *Example:* `d_prime=0.8` is hidden. 
   - *Draft:* "Which variants are linked to rs568 in the CDX population?" (The tool uses 0.8 to filter, but the user just asks for "linked variants").

**Question 2: The "Qualitative" Question (Specific Demand)**
   - **Goal:** A researcher asking for a specific *quality* of result.
   - **Technique:** Use adjectives to reflect the parameter values.
   - *Example:* `d_prime=0.8` becomes "strong LD".
   - *Draft:* "Identify variants with **strong linkage disequilibrium** with rs568."

**RULES:**
   - You can only ask **one** question at a time.
   - Do not ask for multiple questions and multiple aspects in one sentence. like ... and ...
   - You need to keep the question concise and to the point.
   - Do not use (...) to provide supportive information.

PRINCIPLES OF "PLAIN TEXT" ANSWERABILITY
---
1. THE "HALLWAY TEST"
   - Could you ask this question to a professor in a hallway? 
   - *Fail:* "What is the return type for query X?" (Too technical)
   - *Pass:* "What are the clinical consequences of variant X?" (Natural)

2. NO "DATA LEAKAGE"
   - Do not include the answer in the question.
   - *Fail:* "Since protein X is a kinase, what is it?"
   - *Pass:* "What is the function of protein X?"

3. NO ARTIFACTS
   - Never include file headers (e.g., `>id_123`) or internal database keys (e.g., `taxonomy_id`) in the natural text.

So, the question should be answerable by plain text, withouth the need of running the tool. But using this tool can provide more accurate and detailed information.

OUTPUT FORMAT
---
Return JSON only:
{
  "param_analysis": {
    "<param_name>": "<KEEP|MAP|OMIT>: <Reasoning>"
  },
  "observation_check": {
    "available": "<list specific fields that HAVE data>",
    "missing": "<list specific fields that are empty or null>"
  },
  "questions": [
    "<QUESTION 1>",
    "<QUESTION 2>"
  ]
}
"""

    identifiers_block = "\n".join(f"  - {v}" for v in identifiers) if identifiers else "(none detected)"
    few_shots_text = _format_few_shot_examples(few_shot_items)
    func_doc_text = _format_function_doc(doc)
    params_json = json.dumps(params, ensure_ascii=False, indent=2)
    observation_json = json.dumps(observation_result, ensure_ascii=False, indent=2)

    user_prompt = f"""
GENERATE TWO NATURAL BIOMEDICAL QUESTIONS
---

FUNCTION DOCUMENTATION (Understand the tool's specific bias/domain):
{func_doc_text}

STEP 1 - Classify params (VERBATIM/PARAPHRASE/OMIT):

PARAMS:
{params_json}

STEP 2 - Check observation (Distinguish between AVAILABLE data and MISSING/EMPTY data):

OBSERVATION:
{observation_json}

STEP 3 - Write TWO questions:
  - Question 1: Broad intent (Natural tone, implies need for this specific tool)
  - Question 2: Specific feature (Focus on a field that HAS data)
  - MUST include these identifiers:
{identifiers_block}

REFERENCE EXAMPLES:
{few_shots_text}

Output JSON with param_analysis, observation_check, and questions.
"""

    return sys_prompt, user_prompt


def parse_cot_response(content: str) -> List[str]:
    """
    Parse the CoT JSON response and extract questions.
    Handles both the new CoT format and fallback to old format.
    """
    content = (content or "").strip()
    if not content:
        return []

    def _strip_comments(txt: str) -> str:
        # Remove C-style /* ... */ comment blocks that break strict JSON parsing.
        return re.sub(r"/\*.*?\*/", "", txt, flags=re.DOTALL)

    def _load_json_safe(txt: str):
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            return None
    
    cleaned = _strip_comments(content)

    # Try strict JSON first
    data = _load_json_safe(cleaned)
    if isinstance(data, dict) and "questions" in data:
        questions = data.get("questions", [])
        if isinstance(questions, list):
            result = [str(q).strip() for q in questions if isinstance(q, str) and q.strip()]
            if len(result) >= 2 and result[0] != result[1]:
                return result[:2]
    if isinstance(data, list):
        result = [str(q).strip() for q in data if isinstance(q, str) and q.strip()]
        if len(result) >= 2 and result[0] != result[1]:
            return result[:2]

    # Regex extract questions array even if JSON is slightly invalid
    m = re.search(r'"questions"\s*:\s*\[(.*?)\]', cleaned, flags=re.DOTALL | re.IGNORECASE)
    if m:
        block = m.group(1)
        qs = re.findall(r'"([^"]+)"', block)
        qs = [q.strip() for q in qs if q.strip()]
        if len(qs) >= 2 and qs[0] != qs[1]:
            return qs[:2]
    
    # Fallback: extract lines that look like questions
    lines = [ln.strip("- \t \"'") for ln in content.splitlines() if ln.strip()]
    questions = [ln for ln in lines if ln.endswith("?")]
    if len(questions) >= 2:
        return questions[:2]
    
    # Last resort: any two distinct non-empty lines
    uniq: List[str] = []
    for ln in lines:
        if ln and ln not in uniq:
            uniq.append(ln)
        if len(uniq) == 2:
            break
    return uniq[:2]
