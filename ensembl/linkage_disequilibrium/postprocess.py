from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional
import random

@dataclass
class LDPostprocessConfig:
    # Keep perfect LD pairs (r2==1.0 or D'==1.0) – these are the most informative.
    keep_perfect: bool = True

    # Keep top-K edges per anchor variant (variation1) by r2 then d'
    topk_per_anchor: int = 2

    # r2 bins for diversity; tiny per_bin since overall budget is small
    r2_bins: Tuple[Tuple[float, float], ...] = (
        (0.0, 0.1),
        (0.1, 0.3),
        (0.3, 0.6),
        (0.6, 0.9),
        (0.9, 1.01),
    )
    per_bin: int = 2  # very small to fit into 10–20 total

    # Total cap for returned edges (designed for LLM training context size)
    budget: int = 20

    # Reproducibility
    seed: int = 1337

    # Cleanup options
    dedupe_symmetric: bool = True
    cast_numeric: bool = True
    round_decimals: Optional[int] = 3  # shrink size but keep enough precision

def _to_float_maybe(x: Any) -> Any:
    try:
        return float(x)
    except Exception:
        return x

def _cast_numeric(edge: Dict[str, Any], decimals: Optional[int]) -> Dict[str, Any]:
    e = dict(edge)
    if "r2" in e:
        e["r2"] = _to_float_maybe(e["r2"])
        if isinstance(e["r2"], float) and decimals is not None:
            e["r2"] = round(e["r2"], decimals)
    if "d_prime" in e:
        e["d_prime"] = _to_float_maybe(e["d_prime"])
        if isinstance(e["d_prime"], float) and decimals is not None:
            e["d_prime"] = round(e["d_prime"], decimals)
    return e

def _canonicalize(edge: Dict[str, Any]) -> Dict[str, Any]:
    """Order (variation1, variation2) lexicographically so (A,B)==(B,A)."""
    e = dict(edge)
    v1, v2 = e.get("variation1"), e.get("variation2")
    if v1 is not None and v2 is not None and v2 < v1:
        e["variation1"], e["variation2"] = v2, v1
    return e

def _dedupe(edges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for e in edges:
        key = (
            e.get("variation1"),
            e.get("variation2"),
            e.get("population_name"),
            e.get("r2"),
            e.get("d_prime"),
        )
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out

def _topk_per_anchor(edges: List[Dict[str, Any]], k: int) -> List[Dict[str, Any]]:
    if k <= 0:
        return []
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for e in edges:
        a = e.get("variation1")
        if a:
            buckets.setdefault(a, []).append(e)
    kept: List[Dict[str, Any]] = []
    for a, lst in buckets.items():
        lst.sort(key=lambda x: (x.get("r2", -1.0), x.get("d_prime", -1.0)), reverse=True)
        kept.extend(lst[:k])
    return kept

def _stratified_r2_sample(
    edges: List[Dict[str, Any]],
    bins: Tuple[Tuple[float, float], ...],
    per_bin: int,
    seed: int,
) -> List[Dict[str, Any]]:
    rnd = random.Random(seed)
    bmap: Dict[Tuple[float, float], List[Dict[str, Any]]] = {b: [] for b in bins}
    for e in edges:
        r2 = e.get("r2")
        if not isinstance(r2, (int, float)):
            continue
        for lo, hi in bins:
            if lo <= r2 < hi:
                bmap[(lo, hi)].append(e)
                break
    out: List[Dict[str, Any]] = []
    for b in bins:
        pool = bmap[b]
        if pool:
            n = min(per_bin, len(pool))
            out.extend(rnd.sample(pool, n))
    return out

def _score_key(e: Dict[str, Any]) -> Tuple[int, float, float]:
    """Sort helper: perfect first, then higher r2, then higher D'."""
    r2 = e.get("r2", -1.0)
    dp = e.get("d_prime", -1.0)
    is_perfect = int((isinstance(r2, float) and r2 == 1.0) or (isinstance(dp, float) and dp == 1.0))
    return (is_perfect, float(r2) if isinstance(r2, (int, float)) else -1.0, float(dp) if isinstance(dp, (int, float)) else -1.0)

def ld_region_postprocess(edges: List[Dict[str, Any]], cfg: Optional[LDPostprocessConfig] = None) -> List[Dict[str, Any]]:
    """
    Reduce a large LD edge list to ~10–20 highly informative examples:
      - keep all perfect LD,
      - keep top-K per anchor,
      - fill remaining with stratified r2 sampling,
      - finalize by strongest edges if still over budget.
    Deterministic with cfg.seed.
    """
    if not isinstance(edges, list) or not edges:
        return edges

    cfg = cfg or LDPostprocessConfig()

    # 1) Clean + canonicalize
    cleaned = []
    for e in edges:
        x = _canonicalize(e) if cfg.dedupe_symmetric else dict(e)
        x = _cast_numeric(x, cfg.round_decimals) if cfg.cast_numeric else x
        cleaned.append(x)

    # 2) Dedupe
    if cfg.dedupe_symmetric:
        cleaned = _dedupe(cleaned)

    # Early exit if tiny
    if len(cleaned) <= cfg.budget:
        # Still sort for stability / quality
        cleaned.sort(key=_score_key, reverse=True)
        return cleaned

    # 3) Always keep perfect LD
    perfect: List[Dict[str, Any]] = []
    if cfg.keep_perfect:
        for e in cleaned:
            r2 = e.get("r2")
            dp = e.get("d_prime")
            if (isinstance(r2, float) and r2 == 1.0) or (isinstance(dp, float) and dp == 1.0):
                perfect.append(e)

    # 4) Top-K per anchor
    topk = _topk_per_anchor(cleaned, cfg.topk_per_anchor)

    # Build a set of already kept (by pair) to avoid duplicates
    kept_keys = set()
    def _k(e): return (e.get("variation1"), e.get("variation2"))
    result: List[Dict[str, Any]] = []
    for chunk in (perfect, topk):
        for e in chunk:
            key = _k(e)
            if key not in kept_keys:
                kept_keys.add(key)
                result.append(e)

    # 5) Fill up to budget with stratified r2 sampling
    remaining = [e for e in cleaned if _k(e) not in kept_keys]
    if len(result) < cfg.budget:
        fill = _stratified_r2_sample(remaining, cfg.r2_bins, cfg.per_bin, cfg.seed)
        for e in fill:
            key = _k(e)
            if key not in kept_keys and len(result) < cfg.budget:
                kept_keys.add(key)
                result.append(e)

    # 6) If still short (e.g., bins sparse), fill by strongest remaining edges
    if len(result) < cfg.budget:
        remaining.sort(key=_score_key, reverse=True)
        for e in remaining:
            key = _k(e)
            if key not in kept_keys:
                result.append(e)
                kept_keys.add(key)
                if len(result) >= cfg.budget:
                    break

    # 7) If we somehow exceeded (e.g., many perfect), trim to budget by score
    if len(result) > cfg.budget:
        result.sort(key=_score_key, reverse=True)
        result = result[:cfg.budget]

    # Stable, high-signal output
    result.sort(key=_score_key, reverse=True)
    return result
