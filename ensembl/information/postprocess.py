from collections import Counter


def summarize_species(response):
    """
    Summarizes the species data from the API response.
    
    This function processes the 'species' list in the response and generates a summary including:
    - Total number of species
    - Distribution by common_name (with variant counts, limited to top 10 + others)
    - Unique taxon_ids
    - Groups distribution
    - A sampled list of 5 representative entries (trimmed to essential fields)
    
    Returns a dictionary with the summary data.
    """
    if 'species' not in response:
        raise ValueError("Response must contain 'species' key with a list of dictionaries.")
    
    species_list = response['species']
    total_species = len(species_list)
    
    # Group by common_name and count variants
    common_name_counter = Counter(s['common_name'] for s in species_list if 'common_name' in s)
    common_name_summary = [
        f"{name} ({count} variants)" for name, count in common_name_counter.most_common()
    ]
    
    # Shorten common_name_summary: top 10 + others
    top_n = 10
    shortened_summary = common_name_summary[:top_n]
    if len(common_name_summary) > top_n:
        other_counts = []
        for item in common_name_summary[top_n:]:
            try:
                count_str = item.rsplit('(', 1)[1].split(' ')[0].strip()
                count = int(count_str)
            except (IndexError, ValueError):
                count = 0
            other_counts.append(count)
        other_total = sum(other_counts)
        other_names = len(common_name_summary) - top_n
        shortened_summary.append(f"Others ({other_total} variants total across {other_names} names)")
    common_name_summary = shortened_summary
    
    # Unique taxon_ids
    unique_taxon_ids = len(set(s.get('taxon_id') for s in species_list))
    
    # Groups distribution
    groups_counter = Counter()
    for s in species_list:
        groups = tuple(sorted(s.get('groups', [])))  # Use tuple for hashable key
        groups_counter[groups] += 1
    groups_summary = {', '.join(k): v for k, v in groups_counter.items()}
    
    # Sample 5 entries, trimmed to essential fields
    sampled_entries = []
    sample_size = 3
    if total_species > sample_size:
        # Simple sampling: every nth entry for diversity
        step = total_species // sample_size
        for i in range(0, total_species, step):
            if len(sampled_entries) >= sample_size:
                break
            entry = species_list[i]
            trimmed = {
                'display_name': entry.get('display_name'),
                'common_name': entry.get('common_name'),
                'taxon_id': entry.get('taxon_id'),
                'groups': entry.get('groups'),
                'strain': entry.get('strain'),
                'aliases': entry.get('aliases') if entry.get('aliases') else None
            }
            # Remove None values
            trimmed = {k: v for k, v in trimmed.items() if v is not None}
            sampled_entries.append(trimmed)
    else:
        sampled_entries = species_list  # If small, include all
    
    summary = {
        'total_species': total_species,
        'unique_common_names': len(common_name_counter),
        'common_names_summary': common_name_summary,
        'unique_taxon_ids': unique_taxon_ids,
        'groups_distribution': groups_summary,
        'sampled_entries': sampled_entries,
        'division': species_list[0].get('division') if species_list else None,
        'release': species_list[0].get('release') if species_list else None
    }
    
    return summary

def summarize_geno_division(response):
    """
    Summarizes the genomes data from the API response.
    
    This function processes the list of genome dictionaries and generates a summary including:
    - Total number of genomes
    - Distribution by scientific_name (with variant counts, limited to top 10 + others)
    - Unique taxonomy_ids
    - Flags distribution (counts where each flag is True)
    - A sampled list of 5 representative entries (trimmed to essential fields)
    
    Returns a dictionary with the summary data.
    """
    if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
        raise ValueError("Response must be a list of dictionaries.")
    
    genomes_list = response
    total_genomes = len(genomes_list)
    
    # Group by scientific_name and count variants
    scientific_name_counter = Counter(g.get('scientific_name') for g in genomes_list if 'scientific_name' in g)
    scientific_name_summary = [
        f"{name} ({count} variants)" for name, count in scientific_name_counter.most_common()
    ]
    
    # Shorten scientific_name_summary: top 10 + others
    top_n = 10
    shortened_summary = scientific_name_summary[:top_n]
    if len(scientific_name_summary) > top_n:
        other_counts = []
        for item in scientific_name_summary[top_n:]:
            try:
                count_str = item.rsplit('(', 1)[1].split(' ')[0].strip()
                count = int(count_str)
            except (IndexError, ValueError):
                count = 0
            other_counts.append(count)
        other_total = sum(other_counts)
        other_names = len(scientific_name_summary) - top_n
        shortened_summary.append(f"Others ({other_total} variants total across {other_names} names)")
    scientific_name_summary = shortened_summary
    
    # Unique taxonomy_ids
    unique_taxonomy_ids = len(set(g.get('taxonomy_id') for g in genomes_list))
    
    # Flags distribution: count True for key flags
    key_flags = [
        'has_variations', 'has_other_alignments', 'has_microarray',
        'has_pan_compara', 'has_synteny', 'has_peptide_compara',
        'has_genome_alignments'
    ]
    flags_summary = {
        flag: sum(1 for g in genomes_list if g.get(flag, 0) == 1)
        for flag in key_flags
    }
    
    # Assembly level distribution
    assembly_level_counter = Counter(g.get('assembly_level') for g in genomes_list if 'assembly_level' in g)
    assembly_level_summary = {level: count for level, count in assembly_level_counter.items()}
    
    # Sample 3 entries, trimmed to essential fields
    sampled_entries = []
    sample_size = 3
    if total_genomes > sample_size:
        # Simple sampling: every nth entry for diversity
        step = total_genomes // sample_size
        for i in range(0, total_genomes, step):
            if len(sampled_entries) >= sample_size:
                break
            entry = genomes_list[i]
            trimmed = {
                'display_name': entry.get('display_name'),
                'scientific_name': entry.get('scientific_name'),
                'taxonomy_id': entry.get('taxonomy_id'),
                'assembly_name': entry.get('assembly_name'),
                'assembly_level': entry.get('assembly_level'),
                'strain': entry.get('strain'),
                'base_count': entry.get('base_count'),
                'genebuild': entry.get('genebuild')
            }
            # Remove None values
            trimmed = {k: v for k, v in trimmed.items() if v is not None}
            sampled_entries.append(trimmed)
    else:
        sampled_entries = genomes_list  # If small, include all
    
    summary = {
        'total_genomes': total_genomes,
        'unique_scientific_names': len(scientific_name_counter),
        'scientific_names_summary': scientific_name_summary,
        'unique_taxonomy_ids': unique_taxonomy_ids,
        'flags_distribution': flags_summary,
        'assembly_level_distribution': assembly_level_summary,
        'sampled_entries': sampled_entries,
        'division': genomes_list[0].get('division') if genomes_list else None,
        'data_release_id': genomes_list[0].get('data_release_id') if genomes_list else None
    }
    
    return summary


def summarize_geno_accession(response):
    """Summarize `info/genomes/accession` results into a compact structure.

    The raw payload for this endpoint can be very large when `expand=True` is
    used. This helper extracts high–value insights while keeping the footprint
    small enough for downstream training data.
    """

    if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
        raise ValueError("Response must be a list of dictionaries.")

    if not response:
        return {
            'total_records': 0,
            'scientific_names': [],
            'assembly_levels': {},
            'base_count_stats': {},
            'flags_summary': {},
            'compara_methods': {},
            'features_highlights': {},
            'variation_highlights': {},
            'sampled_entries': []
        }

    def _top_items(mapping, top_n=5):
        """Return top-N items with an aggregated 'Others' bucket."""
        if not isinstance(mapping, dict):
            return []
        items = sorted(
            ((k, v) for k, v in mapping.items() if isinstance(v, (int, float))),
            key=lambda kv: kv[1],
            reverse=True
        )
        top = items[:top_n]
        if len(items) > top_n:
            remainder = sum(v for _, v in items[top_n:])
            top.append(('Others', remainder))
        return [{ 'label': k, 'value': v } for k, v in top]

    records = response
    total_records = len(records)

    scientific_names = sorted({rec.get('scientific_name') for rec in records if rec.get('scientific_name')})
    scientific_names = scientific_names[:5] + (["Others"] if len(scientific_names) > 5 else [])

    assembly_levels = Counter(rec.get('assembly_level') for rec in records if rec.get('assembly_level'))
    assembly_levels = dict(assembly_levels)

    base_counts = [rec.get('base_count') for rec in records if isinstance(rec.get('base_count'), (int, float))]
    base_count_stats = {}
    if base_counts:
        base_count_stats = {
            'total': sum(base_counts),
            'average': sum(base_counts) / len(base_counts),
            'min': min(base_counts),
            'max': max(base_counts)
        }

    key_flags = [
        'has_variations', 'has_other_alignments', 'has_microarray',
        'has_pan_compara', 'has_genome_alignments', 'has_peptide_compara'
    ]
    flags_summary = {
        flag: sum(1 for rec in records if rec.get(flag, 0) == 1)
        for flag in key_flags
    }

    compara_methods_counter = Counter()
    compara_divisions_counter = Counter()
    for rec in records:
        for entry in rec.get('compara', []) or []:
            method = entry.get('method')
            division = entry.get('division')
            if method:
                compara_methods_counter[method] += 1
            if division:
                compara_divisions_counter[division] += 1
    compara_methods = {
        'by_method': dict(compara_methods_counter.most_common(5)),
        'by_division': dict(compara_divisions_counter.most_common(5))
    }

    features_highlights = {}
    for rec in records:
        features = rec.get('features')
        if not isinstance(features, dict):
            continue
        for group_name, group_values in features.items():
            if group_name not in features_highlights:
                features_highlights[group_name] = _top_items(group_values)

    variation_highlights = {}
    for rec in records:
        variations = rec.get('variations')
        if not isinstance(variations, dict):
            continue
        for group_name, group_values in variations.items():
            if isinstance(group_values, dict) and group_name not in variation_highlights:
                variation_highlights[group_name] = _top_items(group_values)

    sample_size = 3
    sampled_entries = []
    if total_records <= sample_size:
        iterator = records
    else:
        step = max(total_records // sample_size, 1)
        iterator = [records[i] for i in range(0, total_records, step)][:sample_size]
    for rec in iterator:
        trimmed = {
            'display_name': rec.get('display_name'),
            'scientific_name': rec.get('scientific_name'),
            'assembly_name': rec.get('assembly_name'),
            'assembly_accession': rec.get('assembly_accession'),
            'assembly_level': rec.get('assembly_level'),
            'taxonomy_id': rec.get('taxonomy_id'),
            'base_count': rec.get('base_count')
        }
        sampled_entries.append({k: v for k, v in trimmed.items() if v is not None})

    summary = {
        'total_records': total_records,
        'scientific_names': scientific_names,
        'assembly_levels': assembly_levels,
        'base_count_stats': base_count_stats,
        'flags_summary': flags_summary,
        'compara_methods': compara_methods,
        'features_highlights': features_highlights,
        'variation_highlights': variation_highlights,
        'division': records[0].get('division'),
        'data_release_id': records[0].get('data_release_id'),
        'sampled_entries': sampled_entries
    }

    return summary


def summarize_assembly(response):
    """Compact summary for `info/assembly` responses."""

    if not isinstance(response, dict):
        raise ValueError("Response must be a dictionary.")

    top_regions = response.get('top_level_region') or []
    if not isinstance(top_regions, list):
        top_regions = []
    top_regions = [r for r in top_regions if isinstance(r, dict)]

    def _safe_int(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _truncate_list(values, max_items=5):
        if not isinstance(values, list):
            return []
        cleaned = [v for v in values if v is not None]
        truncated = cleaned[:max_items]
        if len(cleaned) > max_items:
            truncated.append(f"Others ({len(cleaned) - max_items} more)")
        return truncated

    region_lengths = [_safe_int(r.get('length')) for r in top_regions]
    region_lengths = [length for length in region_lengths if length is not None]
    total_regions = len(top_regions)
    total_region_length = sum(region_lengths)

    sorted_regions = sorted(
        (r for r in top_regions if _safe_int(r.get('length')) is not None),
        key=lambda r: _safe_int(r.get('length')),
        reverse=True
    )

    top_regions_summary = []
    for region in sorted_regions[:5]:
        length = _safe_int(region.get('length'))
        entry = {
            'name': region.get('name'),
            'length': length,
            'coord_system': region.get('coord_system')
        }
        synonyms = region.get('synonyms')
        if isinstance(synonyms, list) and synonyms:
            synonym = synonyms[0]
            if isinstance(synonym, dict):
                entry['synonym'] = synonym.get('name')
        top_regions_summary.append({k: v for k, v in entry.items() if v is not None})

    captured_length = sum(item.get('length', 0) for item in top_regions_summary)
    remaining_length = total_region_length - captured_length if total_region_length else 0

    coord_system_counts = Counter(
        region.get('coord_system') for region in top_regions if region.get('coord_system')
    )

    regions_with_synonyms = sum(
        1 for region in top_regions if isinstance(region.get('synonyms'), list) and region['synonyms']
    )

    genebuild_fields = {
        key: response.get(key)
        for key in (
            'genebuild_method',
            'genebuild_start_date',
            'genebuild_initial_release_date',
            'genebuild_last_geneset_update'
        )
        if response.get(key) is not None
    }

    summary = {
        'assembly': {
            'name': response.get('assembly_name'),
            'accession': response.get('assembly_accession'),
            'date': response.get('assembly_date'),
            'golden_path_length': response.get('golden_path'),
            'default_coord_system_version': response.get('default_coord_system_version')
        },
        'coord_system_versions': _truncate_list(response.get('coord_system_versions'), max_items=5),
        'region_overview': {
            'total_regions': total_regions,
            'total_length': total_region_length,
            'coord_system_counts': dict(coord_system_counts),
            'regions_with_synonyms': regions_with_synonyms,
            'top_regions': top_regions_summary,
            'remaining_length': remaining_length
        },
        'karyotype': _truncate_list(response.get('karyotype'), max_items=12),
        'genebuild_timeline': genebuild_fields
    }

    return summary


def summarize_geno_taxonomy(response):
    """Summarize `info/genomes/taxonomy` payloads into compact aggregates."""

    if isinstance(response, str):
        # Handle case where API returns HTML/error instead of JSON
        return {
            'total_genomes': 0,
            'unique_scientific_names': 0,
            'unique_taxonomy_ids': 0,
            'divisions': [],
            'assembly_levels': {},
            'base_count_stats': {},
            'flags_summary': {},
            'compara_methods': {},
            'features_highlights': {},
            'variation_highlights': {},
            'sampled_entries': [],
            'error': 'API returned non-JSON response'
        }

    if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
        raise ValueError("Response must be a list of dictionaries.")

    if not response:
        return {
            'total_genomes': 0,
            'unique_scientific_names': 0,
            'unique_taxonomy_ids': 0,
            'divisions': [],
            'assembly_levels': {},
            'base_count_stats': {},
            'flags_summary': {},
            'compara_methods': {},
            'features_highlights': {},
            'variation_highlights': {},
            'sampled_entries': []
        }

    def _top_from_counter(counter: Counter, top_n: int = 5):
        if not isinstance(counter, Counter) or not counter:
            return []
        top_items = counter.most_common(top_n)
        top_sum = sum(v for _, v in top_items)
        total_sum = sum(counter.values())
        result = [{'label': label, 'value': value} for label, value in top_items]
        if len(counter) > top_n and total_sum > top_sum:
            result.append({'label': 'Others', 'value': total_sum - top_sum})
        return result

    def _safe_number(value):
        if isinstance(value, (int, float)):
            return value
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    records = response
    total_genomes = len(records)

    scientific_name_counter = Counter(
        rec.get('scientific_name') for rec in records if rec.get('scientific_name')
    )
    taxonomy_counter = Counter(
        rec.get('taxonomy_id') for rec in records if rec.get('taxonomy_id')
    )
    division_counter = Counter(
        rec.get('division') for rec in records if rec.get('division')
    )
    assembly_levels_counter = Counter(
        rec.get('assembly_level') for rec in records if rec.get('assembly_level')
    )

    base_counts = [_safe_number(rec.get('base_count')) for rec in records]
    base_counts = [value for value in base_counts if value is not None]
    base_count_stats = {}
    if base_counts:
        base_count_stats = {
            'total': sum(base_counts),
            'average': sum(base_counts) / len(base_counts),
            'min': min(base_counts),
            'max': max(base_counts)
        }

    key_flags = [
        'has_variations',
        'has_other_alignments',
        'has_microarray',
        'has_pan_compara',
        'has_peptide_compara',
        'has_genome_alignments',
        'has_synteny'
    ]
    flags_summary = {
        flag: sum(1 for rec in records if rec.get(flag, 0) in (1, True))
        for flag in key_flags
    }

    compara_method_counter = Counter()
    compara_division_counter = Counter()
    for rec in records:
        for entry in rec.get('compara', []) or []:
            method = entry.get('method')
            division = entry.get('division')
            if method:
                compara_method_counter[method] += 1
            if division:
                compara_division_counter[division] += 1

    def _aggregate_nested_counts(records_iterable, key):
        grouped = {}
        for rec in records_iterable:
            container = rec.get(key)
            if not isinstance(container, dict):
                continue
            for group_name, values in container.items():
                if not isinstance(values, dict):
                    continue
                group_counter = grouped.setdefault(group_name, Counter())
                for label, value in values.items():
                    number = _safe_number(value)
                    if number is not None:
                        group_counter[label] += number
        return grouped

    features_grouped = _aggregate_nested_counts(records, 'features')
    variation_grouped = _aggregate_nested_counts(records, 'variations')

    features_highlights = {
        group: _top_from_counter(counter, top_n=3)
        for group, counter in features_grouped.items()
    }
    variation_highlights = {
        group: _top_from_counter(counter, top_n=3)
        for group, counter in variation_grouped.items()
    }

    sample_size = 3
    if total_genomes <= sample_size:
        sample_records = records
    else:
        step = max(total_genomes // sample_size, 1)
        sample_records = [records[i] for i in range(0, total_genomes, step)][:sample_size]

    sampled_entries = []
    for rec in sample_records:
        trimmed = {
            'scientific_name': rec.get('scientific_name'),
            'display_name': rec.get('display_name'),
            'division': rec.get('division'),
            'assembly_name': rec.get('assembly_name'),
            'assembly_level': rec.get('assembly_level'),
            'base_count': rec.get('base_count'),
            'flags': {
                flag: rec.get(flag, 0)
                for flag in key_flags
                if rec.get(flag, 0)
            }
        }
        sampled_entries.append({k: v for k, v in trimmed.items() if v})

    summary = {
        'total_genomes': total_genomes,
        'unique_scientific_names': len(scientific_name_counter),
        'unique_taxonomy_ids': len(taxonomy_counter),
        'divisions': _top_from_counter(division_counter, top_n=5),
        'assembly_levels': dict(assembly_levels_counter),
        'scientific_names_summary': _top_from_counter(scientific_name_counter, top_n=10),
        'taxonomy_summary': _top_from_counter(taxonomy_counter, top_n=10),
        'base_count_stats': base_count_stats,
        'flags_summary': flags_summary,
        'compara_methods': {
            'by_method': _top_from_counter(compara_method_counter, top_n=5),
            'by_division': _top_from_counter(compara_division_counter, top_n=5)
        },
        'features_highlights': features_highlights,
        'variation_highlights': variation_highlights,
        'sampled_entries': sampled_entries
    }

    return summary


def summarize_compara_sets(response):
    """Summarize `info/compara/species_sets` collections into compact stats."""

    if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
        raise ValueError("Response must be a list of dictionaries.")

    if not response:
        return {
            'total_sets': 0,
            'methods': {},
            'species_set_group_summary': [],
            'species_frequency': [],
            'set_size_stats': {},
            'sampled_sets': []
        }

    sets = response
    total_sets = len(sets)

    method_counter = Counter(item.get('method') for item in sets if item.get('method'))
    group_counter = Counter(item.get('species_set_group') for item in sets if item.get('species_set_group'))

    def _top_list(counter: Counter, top_n: int = 10):
        if not counter:
            return []
        most_common = counter.most_common(top_n)
        total = sum(counter.values())
        top_total = sum(value for _, value in most_common)
        result = [{'label': label, 'value': value} for label, value in most_common]
        if len(counter) > top_n and total > top_total:
            result.append({'label': 'Others', 'value': total - top_total})
        return result

    set_sizes = []
    species_counter = Counter()
    for item in sets:
        members = item.get('species_set') or []
        if not isinstance(members, list):
            continue
        size = len(members)
        set_sizes.append(size)
        species_counter.update(members)

    set_size_stats = {}
    if set_sizes:
        set_size_stats = {
            'min': min(set_sizes),
            'max': max(set_sizes),
            'average': sum(set_sizes) / len(set_sizes),
            'total_species_links': sum(set_sizes)
        }

    sample_size = 3
    if total_sets <= sample_size:
        sampled = sets
    else:
        step = max(total_sets // sample_size, 1)
        sampled = [sets[i] for i in range(0, total_sets, step)][:sample_size]

    sampled_sets = []
    for item in sampled:
        entry = {
            'name': item.get('name'),
            'method': item.get('method'),
            'species_set_group': item.get('species_set_group'),
            'size': len(item.get('species_set') or []),
            'representative_species': (item.get('species_set') or [])[:3]
        }
        sampled_sets.append({k: v for k, v in entry.items() if v})

    summary = {
        'total_sets': total_sets,
        'methods': dict(method_counter),
        'species_set_group_summary': _top_list(group_counter, top_n=10),
        'species_frequency': _top_list(species_counter, top_n=20),
        'set_size_stats': set_size_stats,
        'sampled_sets': sampled_sets
    }

    return summary