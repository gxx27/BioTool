from typing import List, Dict, Any

TAG_SAMPLE_LIMIT = 3
CHILD_SAMPLE_LIMIT = 5
ALT_MATCH_LIMIT = 3

def get_all_nodes(nodes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    all_nodes = []
    def recurse(node: Dict[str, Any]):
        all_nodes.append(node)
        if 'children' in node:
            for child in node['children']:
                # Add parent reference to child as a summary dict
                child['parent'] = {k: v for k, v in node.items() if k in ['id', 'name', 'scientific_name', 'tags']}
                recurse(child)
    for top in nodes:
        recurse(top)
    return all_nodes

def postprocess_get_taxonomy_classification(result: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarizes the taxonomic classification by providing both an overall high-level summary
    (e.g., major taxonomic ranks and key info) and the full linear path from root to leaf.
    This ensures overall information is captured meaningfully, beyond just representative items.
    Focuses on key fields for conciseness.
    """
    if not result:
        return {"summary": "No data available", "path": []}

    all_nodes = get_all_nodes(result)
    node_map = {node['id']: node for node in all_nodes if 'id' in node}

    # Find the leaf node: the one with common_name or genbank_common_name in tags
    leaf = None
    for node in all_nodes:
        if 'tags' in node and ('common_name' in node['tags'] or 'genbank_common_name' in node['tags']):
            leaf = node
            break
    if not leaf:
        return {"summary": "No leaf node found", "path": []}

    # Build the full path from leaf to root
    path = []
    current = leaf
    seen = set()
    while current and 'id' in current and current['id'] not in seen:
        seen.add(current['id'])
        summary = {
            'id': current['id'],
            'name': current['name'],
            'scientific_name': current['scientific_name']
        }
        if 'tags' in current:
            tags = current['tags']
            common_key = 'common_name' if 'common_name' in tags else 'genbank_common_name' if 'genbank_common_name' in tags else None
            if common_key:
                common = tags[common_key]
                summary['common_name'] = common[0] if isinstance(common, list) else common
        path.append(summary)

        if 'parent' in current:
            parent_id = current['parent']['id']
            current = node_map.get(parent_id, current['parent'])
        else:
            current = None

    path.reverse()  # Now root to leaf

    # Create high-level summary: Map to standard ranks where possible, and extract key overall info
    rank_mapping = {
        'Eukaryota': 'Domain',
        'Metazoa': 'Kingdom (Animalia)',
        'Chordata': 'Phylum',
        'Vertebrata': 'Subphylum',
        'Gnathostomata': 'Infraphylum',
        'Teleostomi': 'Superclass',
        'Euteleostomi': 'Clade',
        'Sarcopterygii': 'Clade',
        'Actinopterygii': 'Class (ray-finned fishes)',
        'Aves': 'Class (birds)',
        'Squamata': 'Order (lizards and snakes)',
        'Serpentes': 'Suborder (snakes)',
        'Passeriformes': 'Order (perching birds)',
        'Gadiformes': 'Order (cods)',
        # Add more as needed based on common patterns
    }
    
    high_level_summary = []
    for node in path:
        rank = rank_mapping.get(node['name'], 'Clade')  # Default to 'Clade' if not mapped
        entry = f"{rank}: {node['scientific_name']} (ID: {node['id']})"
        if 'common_name' in node:
            entry += f" - Common: {node['common_name']}"
        high_level_summary.append(entry)
    
    overall_summary = "\n".join(high_level_summary[:10]) + "\n... (full path available below)" if len(high_level_summary) > 10 else "\n".join(high_level_summary)

    return {
        "summary": overall_summary,
        "path": path  # Full path without truncation for detailed info
    }

def postprocess_ontology_ancestors(result: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Summarizes the ontology ancestors by providing an overall high-level summary
    (e.g., total count, categorized groups with counts and examples) and a limited list of representative ancestors.
    This ensures key information is captured concisely without losing essential details, making it suitable for training data.
    Focuses on key fields (accession, name, synonyms) for brevity, omitting lengthy definitions and redundant fields.
    Limits representatives to up to 5 per category to significantly shorten the output.
    """
    if not result:
        return {"summary": "No data available", "representatives": []}

    # Remove duplicates based on accession
    unique_dict = {d['accession']: d for d in result if 'accession' in d}
    unique = list(unique_dict.values())

    # Define categories based on common patterns in GO terms related to ion transport
    categories = {
        "general_ion_transport": [],
        "cation_transport": [],
        "anion_transport": [],
        "specific_ion_transport": [],  # Renamed for accuracy, includes metals and others
        "organelle_specific_transport": [],
        "direction_specific_transport": [],
        "other": []
    }

    # List of specific ions and organelles for categorization
    specific_ions = ["calcium", "sodium", "potassium", "iron", "zinc", "copper", "manganese", "magnesium", "nickel", "cobalt", "lithium", "lead", "aluminum", "mercury", "silver", "vanadium", "cadmium", "chloride", "iodide", "fluoride", "proton"]
    organelles = ["mitochondri", "golgi", "sarcoplasmic", "endoplasmic", "plasma membrane", "synaptic vesicle", "lysosome", "zymogen granule", "ascospore-type prospore", "blood-brain barrier", "blood-cerebrospinal fluid barrier"]

    for term in unique:
        name_lower = term['name'].lower()
        categorized = False

        if "cation" in name_lower:
            categories["cation_transport"].append(term)
            categorized = True
        elif "anion" in name_lower:
            categories["anion_transport"].append(term)
            categorized = True
        elif any(ion in name_lower for ion in specific_ions):
            categories["specific_ion_transport"].append(term)
            categorized = True
        elif any(org in name_lower for org in organelles):
            categories["organelle_specific_transport"].append(term)
            categorized = True
        elif any(dir_word in name_lower for dir_word in ["import", "export", "entry", "uptake", "efflux", "release"]):
            categories["direction_specific_transport"].append(term)
            categorized = True
        elif "transport" in name_lower or "transmembrane" in name_lower:
            categories["general_ion_transport"].append(term)
            categorized = True

        if not categorized:
            categories["other"].append(term)

    # Create high-level summary with counts and examples
    summary_lines = [f"Total unique ancestors: {len(unique)}"]
    for cat, terms in categories.items():
        if terms:
            cat_name = cat.capitalize().replace('_', ' ')
            summary_lines.append(f"{cat_name}: {len(terms)} terms")
            # Provide up to 3 examples per category for illustration
            examples = [t['name'] for t in terms[:3]]
            if examples:
                summary_lines.append(f"Examples: {', '.join(examples)}" + ("..." if len(terms) > 3 else ""))

    summary = "\n".join(summary_lines)

    # Select representatives: up to 5 per category
    representatives = []
    for cat, terms in categories.items():
        for t in terms[:2]:
            representatives.append({
                "accession": t['accession'],
                "name": t['name'],
                "synonyms": t.get('synonyms', [])
            })

    # Sort representatives by accession for consistency
    representatives = sorted(representatives, key=lambda x: x['accession'])

    return {
        "summary": summary,
        "representatives": representatives  # Limited list to reduce length significantly
    }


def _as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _summarize_tags(tags: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(tags, dict):
        return {}

    summary: Dict[str, Any] = {}
    for key in [
        "common_name",
        "genbank_common_name",
        "synonym",
        "equivalent_name",
        "authority",
        "type_material",
        "includes",
        "merged_taxon_id",
    ]:
        values = _as_list(tags.get(key))
        if not values:
            continue
        examples = values[:TAG_SAMPLE_LIMIT]
        if len(values) > TAG_SAMPLE_LIMIT:
            examples.append("…")
        summary[key] = {
            "count": len(values),
            "examples": examples,
        }
    return summary


def _summarize_children(children: Any) -> Dict[str, Any]:
    if not isinstance(children, list):
        return {"total": 0, "leaf": 0, "examples": []}

    total = 0
    leaf_count = 0
    examples: List[Dict[str, Any]] = []

    for child in children:
        if not isinstance(child, dict):
            continue
        total += 1
        if child.get("leaf"):
            leaf_count += 1
        if len(examples) < CHILD_SAMPLE_LIMIT:
            examples.append({
                "id": child.get("id"),
                "name": child.get("name"),
                "scientific_name": child.get("scientific_name"),
                "leaf": bool(child.get("leaf"))
            })

    if total > CHILD_SAMPLE_LIMIT and examples:
        examples.append({"note": f"… {total - CHILD_SAMPLE_LIMIT} more"})

    return {
        "total": total,
        "leaf": leaf_count,
        "non_leaf": max(total - leaf_count, 0),
        "examples": examples,
    }


def postprocess_get_taxonomy_name(response: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize taxonomy name lookup results into concise aggregates."""

    if not isinstance(response, list):
        raise ValueError("Response must be a list of taxonomy entries.")

    if not response:
        return {
            "summary": {},
            "tags": {},
            "children": {"total": 0, "leaf": 0, "examples": []},
            "alternatives": []
        }

    primary = response[0]
    if not isinstance(primary, dict):
        raise ValueError("Primary entry must be a dictionary.")

    parent = primary.get("parent") if isinstance(primary.get("parent"), dict) else {}
    tags_summary = _summarize_tags(primary.get("tags", {}))
    children_summary = _summarize_children(primary.get("children"))

    summary = {
        "id": primary.get("id"),
        "name": primary.get("name"),
        "scientific_name": primary.get("scientific_name"),
        "is_leaf": bool(primary.get("leaf")),
    }

    if parent:
        summary["parent"] = {
            "id": parent.get("id"),
            "name": parent.get("name"),
            "scientific_name": parent.get("scientific_name"),
        }

    alternatives: List[Dict[str, Any]] = []
    for entry in response[1: ALT_MATCH_LIMIT + 1]:
        if not isinstance(entry, dict):
            continue
        alternatives.append({
            "id": entry.get("id"),
            "name": entry.get("name"),
            "scientific_name": entry.get("scientific_name"),
            "is_leaf": bool(entry.get("leaf"))
        })
        if len(alternatives) >= ALT_MATCH_LIMIT:
            break

    result: Dict[str, Any] = {
        "summary": summary,
        "tags": tags_summary,
        "children": children_summary,
    }

    if alternatives:
        result["alternatives"] = alternatives

    return result