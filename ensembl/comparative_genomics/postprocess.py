from collections import defaultdict, Counter
from typing import Any, Dict, List, Optional

def summarize_tree(data):
    """
    Summarizes the entire gene tree JSON without depth limits.
    - Extracts root info.
    - Computes global metrics: num_nodes, num_sequences, num_species, event_types.
    - Summarizes top-level children with subtree stats.
    - Aggregates confidence (e.g., average bootstrap).
    """
    tree = data.get('tree', {})
    root_id = data.get('id', 'Unknown')
    tree_type = data.get('type', 'Unknown')
    rooted = data.get('rooted', 0)

    def traverse(node):
        stats = defaultdict(int)
        species_set = set()
        sequences_count = 0
        event_types = Counter()
        bootstraps = []

        # Current node
        stats['nodes'] += 1

        # Taxonomy
        tax = node.get('taxonomy', {})
        species_name = tax.get('scientific_name', '') or tax.get('common_name', '')
        if species_name:
            species_set.add(species_name)

        # Sequence
        if node.get('sequence'):
            sequences_count += 1

        # Events
        events = node.get('events', {})
        if events.get('type'):
            event_types[events['type']] += 1

        # Confidence (bootstrap)
        conf = node.get('confidence', {}).get('bootstrap')
        if conf:
            bootstraps.append(conf)

        # Children
        if 'children' in node:
            for child in node['children']:
                sub_stats, child_species, child_seq_count, child_events, child_boots = traverse(child)
                for k, v in sub_stats.items():
                    stats[k] += v
                species_set.update(child_species)
                sequences_count += child_seq_count
                event_types.update(child_events)
                bootstraps.extend(child_boots)

        return stats, species_set, sequences_count, event_types, bootstraps

    overall_stats, all_species, total_sequences, all_events, all_bootstraps = traverse(tree)

    # Average bootstrap
    avg_bootstrap = sum(all_bootstraps) / len(all_bootstraps) if all_bootstraps else None

    # Top-level children summaries
    top_children = []
    if 'children' in tree:
        for child in tree['children']:
            child_stats, child_species, child_seqs, child_events, child_boots = traverse(child)
            child_tax = child.get('taxonomy', {})
            top_children.append({
                'taxonomy': child_tax.get('scientific_name', '') or child_tax.get('common_name', ''),
                'branch_length': child.get('branch_length', 0),
                'subtree_nodes': child_stats['nodes'],
                'subtree_sequences': child_seqs,
                'num_species': len(child_species),
                'events_summary': dict(child_events)
            })

    # Major branches: Sort species by frequency or something, but since no freq, list top 10
    major_species = list(all_species)[:10]  # Example: top 10 species

    summary = {
        'root': {
            'id': root_id,
            'type': tree_type,
            'rooted': rooted,
            'events': tree.get('events', {}),
            'taxonomy': tree.get('taxonomy', {})
        },
        'metrics': {
            'num_nodes': overall_stats['nodes'],
            'num_sequences': total_sequences,
            'num_species': len(all_species),
        },
        'events_summary': dict(all_events),
        'confidence_summary': {
            'average_bootstrap': avg_bootstrap,
            'num_bootstraps': len(all_bootstraps)
        },
        'summary_children': top_children,
        'major_species_sample': major_species,  # Sample of species
        'original_params': data.get('params', {})  # Include input params for context
    }

    return summary

def summarize_cafe_tree(data):
    """
    Summarizes the CAFE gene tree JSON.
    - Extracts root info including type, rooted, pvalue_avg.
    - Computes global metrics: num_nodes, num_leaves, total_n_members (sum at leaves), avg_lambda, num_significant_nodes, num_contractions, num_expansions.
    - Summarizes top-level children with subtree stats.
    - Aggregates p-values, lambdas, and timetree_mya for averages.
    - Samples major species/clades.
    """
    tree = data.get('tree', {})
    tree_type = data.get('type', 'Unknown')
    rooted = data.get('rooted', 0)
    pvalue_avg = data.get('pvalue_avg', None)

    def traverse(node):
        stats = defaultdict(int)
        species_set = set()
        n_members_sum = 0  # Sum of n_members at leaves
        lambdas = []
        pvalues = []
        timetree_myas = []
        contractions = 0
        expansions = 0
        significant = 0

        # Current node
        stats['nodes'] += 1

        # Lambda
        if 'lambda' in node:
            lambdas.append(node['lambda'])

        # P-value
        if 'pvalue' in node:
            pvalues.append(node['pvalue'])

        # Events/Significance
        if node.get('is_contraction', 0) == 1:
            contractions += 1
        if node.get('is_expansion', 0) == 1:  # Assuming it exists; from data, is_expansion is present in some
            expansions += 1
        if node.get('is_node_significant', 0) == 1:
            significant += 1

        # Taxonomy and timetree
        tax = node.get('tax', {})
        species_name = tax.get('scientific_name', '') or tax.get('common_name', '')
        if species_name:
            species_set.add(species_name)
        if 'timetree_mya' in tax:
            mya = tax['timetree_mya']
            try:
                mya_float = float(mya)
                if mya_float != 0:
                    timetree_myas.append(mya_float)
            except ValueError:
                pass  # ignore if can't convert

        # Leaf check: if no children, it's a leaf
        if 'children' not in node or not node['children']:
            stats['leaves'] += 1
            n_members_sum += node.get('n_members', 0)

        # Children
        if 'children' in node:
            for child in node['children']:
                sub_stats, child_species, child_n_members, child_lambdas, child_pvalues, child_timetrees, child_contr, child_exp, child_sig = traverse(child)
                for k, v in sub_stats.items():
                    stats[k] += v
                species_set.update(child_species)
                n_members_sum += child_n_members
                lambdas.extend(child_lambdas)
                pvalues.extend(child_pvalues)
                timetree_myas.extend(child_timetrees)
                contractions += child_contr
                expansions += child_exp
                significant += child_sig

        return stats, species_set, n_members_sum, lambdas, pvalues, timetree_myas, contractions, expansions, significant

    overall_stats, all_species, total_n_members, all_lambdas, all_pvalues, all_timetrees, total_contractions, total_expansions, total_significant = traverse(tree)

    # Averages
    avg_lambda = sum(all_lambdas) / len(all_lambdas) if all_lambdas else None
    avg_pvalue = sum(all_pvalues) / len(all_pvalues) if all_pvalues else None
    avg_timetree_mya = sum(all_timetrees) / len(all_timetrees) if all_timetrees else None

    # Top-level children summaries
    top_children = []
    if 'children' in tree:
        for child in tree['children']:
            child_stats, child_species, child_n_members, child_lambdas, child_pvalues, child_timetrees, child_contr, child_exp, child_sig = traverse(child)
            child_tax = child.get('tax', {})
            top_children.append({
                'taxonomy': child_tax.get('scientific_name', '') or child_tax.get('common_name', ''),
                'n_members': child.get('n_members', 0),
                'lambda': child.get('lambda', None),
                'subtree_nodes': child_stats['nodes'],
                'subtree_leaves': child_stats['leaves'],
                'subtree_n_members_sum': child_n_members,
                'num_species': len(child_species),
                'contractions': child_contr,
                'expansions': child_exp,
                'significant_nodes': child_sig
            })

    # Major species: list top 10
    major_species = list(all_species)[:10]

    summary = {
        'root': {
            'name': tree.get('name', 'Unknown'),
            'type': tree_type,
            'rooted': rooted,
            'pvalue_avg': pvalue_avg,
            'lambda': tree.get('lambda', None),
            'taxonomy': tree.get('tax', {})
        },
        'metrics': {
            'num_nodes': overall_stats['nodes'],
            'num_leaves': overall_stats['leaves'],
            'num_species': len(all_species),
            'total_n_members_at_leaves': total_n_members,
            'num_contractions': total_contractions,
            'num_expansions': total_expansions,
            'num_significant_nodes': total_significant
        },
        'averages': {
            'avg_lambda': avg_lambda,
            'avg_pvalue': avg_pvalue,
            'avg_timetree_mya': avg_timetree_mya
        },
        'summary_children': top_children,
        'major_species_sample': major_species  # Sample of species/clades
    }

    return summary

def summarize_homology(
    response: Dict[str, Any],
    max_examples: int = 3,
    truncate_seq_length: int = 100,
    include_full_examples: bool = False  # If True, don't truncate sequences (for debugging)
) -> Dict[str, Any]:
    """
    Summarizes the homology API response.
    
    - Extracts the gene ID.
    - Computes stats: total homologies, count by type, count by taxonomy_level.
    - Selects up to `max_examples` homologies (first ones for simplicity; could randomize if needed).
    - Truncates long sequence/cigar fields in examples to `truncate_seq_length` chars.
    
    Args:
        response: Raw API response dict.
        max_examples: Max number of example homologies to include.
        truncate_seq_length: Max length for sequence/cigar strings before truncating.
        include_full_examples: If True, skip truncation for examples.
    
    Returns:
        Summarized dict with stats and truncated examples.
    """
    if 'data' not in response or not isinstance(response['data'], list) or not response['data']:
        return {
            'summary': {
                'total_homologies': 0,
                'type_counts': {},
                'taxonomy_level_counts': {}
            },
            'gene_id': None,
            'examples': []
        }
    
    data_item = response['data'][0]  # Assuming single item as in your example
    gene_id = data_item.get('id')
    homologies: List[Dict[str, Any]] = data_item.get('homologies', [])
    
    # Compute summary stats
    total_homologies = len(homologies)
    type_counts = Counter(h['type'] for h in homologies if 'type' in h)
    taxonomy_level_counts = Counter(h['taxonomy_level'] for h in homologies if 'taxonomy_level' in h)
    
    # Select examples (first max_examples)
    examples = homologies[:max_examples]
    
    # Truncate long fields in examples (deep copy to avoid modifying original)
    def truncate_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        truncated = d.copy()
        for key, value in truncated.items():
            if isinstance(value, str) and len(value) > truncate_seq_length and not include_full_examples:
                truncated[key] = value[:truncate_seq_length] + '...[truncated]'
            elif isinstance(value, dict):
                truncated[key] = truncate_dict(value)  # Recurse for nested dicts like 'source', 'target'
        return truncated
    
    truncated_examples = [truncate_dict(ex) for ex in examples]
    
    return {
        'summary': {
            'total_homologies': total_homologies,
            'type_counts': dict(type_counts),
            'taxonomy_level_counts': dict(taxonomy_level_counts)
        },
        'gene_id': gene_id,
        'examples': truncated_examples
    }

def summarize_alignment_region(data):
    """
    Summarizes the alignment region API response.
    Expected data format: List of dicts, each containing 'tree' and 'alignments'.
    """
    if not data:
        return []

    if not isinstance(data, list):
        # Handle single dict case if API returns that sometimes, though example showed list
        data = [data]

    summarized_results = []

    for entry in data:
        # Extract tree
        tree = entry.get('tree', '')

        # Process alignments
        alignments = entry.get('alignments', [])
        num_alignments = len(alignments)

        # Species stats
        species_counts = Counter(a.get('species', 'Unknown') for a in alignments)
        unique_species = list(species_counts.keys())

        # Sequence length stats
        seq_lengths = [len(a.get('seq', '')) for a in alignments]
        avg_seq_len = sum(seq_lengths) / len(seq_lengths) if seq_lengths else 0

        # Determine number of examples based on length
        # If sequences are short (<500), show 3. If medium (<2000), show 2. If long, show 1.
        if avg_seq_len < 500:
            num_examples = 3
        elif avg_seq_len < 1000:
            num_examples = 2
        else:
            num_examples = 1
            
        # Create examples with FULL sequences
        examples = []
        for i, align in enumerate(alignments[:num_examples]):
            examples.append({
                "index": i,
                "species": align.get('species'),
                "region": f"{align.get('seq_region')}:{align.get('start')}-{align.get('end')}",
                "strand": align.get('strand'),
                "sequence_length": len(align.get('seq', '')),
                "full_sequence": align.get('seq', '')
            })

        summary = {
            "tree_newick": tree,
            "metrics": {
                "total_alignments": num_alignments,
                "unique_species_count": len(unique_species),
                "average_sequence_length": avg_seq_len
            },
            "alignment_examples": examples
        }
        
        # Reduce summary content: only show top species if many
        if len(species_counts) <= 5:
            summary["species_distribution"] = dict(species_counts)
        else:
            summary["top_5_species"] = dict(species_counts.most_common(5))

        summarized_results.append(summary)

    return summarized_results
