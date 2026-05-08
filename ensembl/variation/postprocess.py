from collections import Counter
from typing import List, Dict, Any

def postprocess_variants(variants: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Postprocess the list of variants to summarize stats and select examples.
    This reduces length for training data while preserving key insights.
    """
    total = len(variants)
    var_classes = set(d.get('var_class', 'Unknown') for d in variants)
    consequences = Counter(d.get('most_severe_consequence', 'Unknown') for d in variants)
    top_consequences = consequences.most_common(5)
    mafs = [d['MAF'] for d in variants if d.get('MAF') is not None]
    avg_maf = sum(mafs) / len(mafs) if mafs else None
    clin_sig_count = sum(1 for d in variants if 'clinical_significance' in d and d['clinical_significance'])

    # Select representative examples (e.g., first 5; customize for diversity if needed)
    examples = variants[:3]
    # Shorten verbose fields in examples to further reduce size
    for ex in examples:
        if 'synonyms' in ex:
            ex['synonyms'] = ex['synonyms'][:5] + ['...'] if len(ex['synonyms']) > 5 else ex['synonyms']
        if 'evidence' in ex:
            ex['evidence'] = ex['evidence'][:3] + ['...'] if len(ex['evidence']) > 3 else ex['evidence']
        if 'mappings' in ex:
            ex['mappings'] = ex['mappings'][:1]  # Keep only the first mapping

    maf_str = f"{avg_maf:.4f}" if avg_maf is not None else 'N/A'
    summary = (
        f"There are {total} variants found. "
        f"Unique variant classes: {', '.join(var_classes)}. "
        f"Top consequences: {top_consequences}. "
        f"Average MAF (where available): {maf_str}. "
        f"Number with clinical significance: {clin_sig_count}."
    )

    return {
        'summary': summary,
        'stats': {
            'total': total,
            'var_classes': list(var_classes),
            'top_consequences': top_consequences,
            'avg_maf': avg_maf,
            'clin_sig_count': clin_sig_count
        },
        'examples': examples
    }