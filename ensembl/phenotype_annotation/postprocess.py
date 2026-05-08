import pandas as pd
import random
import re
from typing import List, Dict, Any

def post_process_accession(results: List[Dict[str, Any]], target_count: int = 10) -> List[Dict[str, Any]]:
    """
    Post-processes results from get_phenotype_by_accession.
    Categorizes by source (e.g., ClinVar, NHGRI-EBI), sorts by significance (p_value or clinical_significance), selects proportionally.
    """
    if not results:
        return []

    df = pd.DataFrame(results)
    # Drop rows based on available columns
    subset_cols = ['description']
    if 'mapped_to_accession' in df.columns:
        subset_cols.append('mapped_to_accession')
    df = df.dropna(subset=subset_cols)

    # Helper for significance: p_value float or clinical rank (benign=high, pathogenic=low)
    def get_significance(attrs: dict) -> float:
        if isinstance(attrs, dict):
            if 'p_value' in attrs:
                try:
                    return float(attrs['p_value'])
                except ValueError:
                    pass
            if 'clinical_significance' in attrs:
                sig_map = {'pathogenic': 0.1, 'likely pathogenic': 0.2, 'uncertain significance': 0.5, 'likely benign': 0.8, 'benign': 1.0}
                return sig_map.get(attrs['clinical_significance'].lower(), float('inf'))
        return float('inf')

    # Categorize by source
    df['category'] = df['source'].fillna('Unknown')
    if 'attributes' in df.columns:
        df['significance'] = df['attributes'].apply(get_significance)
    else:
        df['significance'] = float('inf')  # Default when no attributes available

    # Sort by category, then significance ascending (lower=more significant)
    df = df.sort_values(by=['category', 'significance'], ascending=[True, True])

    # Select proportionally
    category_counts = df['category'].value_counts()
    total_items = len(df)
    selected = []

    for cat, count in category_counts.items():
        prop = count / total_items
        num_to_select = max(1, round(prop * target_count))
        cat_df = df[df['category'] == cat].head(num_to_select)
        selected.extend(cat_df.to_dict(orient='records'))

    if len(selected) > target_count:
        selected = random.sample(selected, target_count)

    if len(selected) < target_count // 2:
        selected = random.sample(results, min(target_count, len(results)))

    for item in selected:
        item.pop('category', None)
        item.pop('significance', None)

    return selected

def post_process_gene(results: List[Dict[str, Any]], target_count: int = 20) -> List[Dict[str, Any]]:
    """
    Post-processes results from get_phenotype_by_gene.
    Categorizes by description keywords (e.g., Neurological, Behavioral), sorts by description length.
    """
    if not results:
        return []

    df = pd.DataFrame(results)
    # Drop rows based on available columns
    subset_cols = ['description']
    if 'ontology_accessions' in df.columns:
        subset_cols.append('ontology_accessions')
    df = df.dropna(subset=subset_cols)

    def categorize_description(desc: str) -> str:
        desc_lower = desc.lower()
        if any(word in desc_lower for word in ['brain', 'neuron', 'cereb', 'neuro', 'cortex']):
            return 'Neurological'
        elif any(word in desc_lower for word in ['behavior', 'anxiety', 'fear', 'social', 'stereotypic', 'hyperactivity']):
            return 'Behavioral'
        elif any(word in desc_lower for word in ['digest', 'intest', 'gastro', 'enteric']):
            return 'Digestive'
        elif any(word in desc_lower for word in ['lethal', 'mortal', 'surviv', 'death']):
            return 'Lethality/Survival'
        elif any(word in desc_lower for word in ['tumour', 'cancer', 'tumor']):
            return 'Tumour-Related'
        else:
            return 'Other'

    df['category'] = df['description'].apply(categorize_description)
    df['desc_length'] = df['description'].str.len()
    df = df.sort_values(by=['category', 'desc_length'], ascending=[True, False])

    category_counts = df['category'].value_counts()
    total_items = len(df)
    selected = []

    for cat, count in category_counts.items():
        prop = count / total_items
        num_to_select = max(1, round(prop * target_count))
        cat_df = df[df['category'] == cat].head(num_to_select)
        selected.extend(cat_df.to_dict(orient='records'))

    if len(selected) > target_count:
        selected = random.sample(selected, target_count)

    if len(selected) < target_count // 2:
        selected = random.sample(results, min(target_count, len(results)))

    for item in selected:
        item.pop('category', None)
        item.pop('desc_length', None)

    return selected

def post_process_term(results: List[Dict[str, Any]], target_count: int = 20) -> List[Dict[str, Any]]:
    """
    Post-processes results from get_phenotype_by_term.
    Categorizes by chromosome from location, fallback to p-value buckets, sorts by p_value.
    """
    if not results:
        return []

    df = pd.DataFrame(results)
    # Drop rows based on available columns
    subset_cols = ['description']
    if 'mapped_to_accession' in df.columns:
        subset_cols.append('mapped_to_accession')
    df = df.dropna(subset=subset_cols)

    def parse_chromosome(loc: str) -> str:
        if pd.isna(loc):
            return 'Unknown'
        match = re.match(r'^(HSCHR)?(\d+|X|Y|MT)?', loc, re.IGNORECASE)
        return match.group(2) if match and match.group(2) else 'Unknown'

    def get_p_value(attrs: dict) -> float:
        if isinstance(attrs, dict) and 'p_value' in attrs:
            try:
                return float(attrs['p_value'])
            except ValueError:
                return float('inf')
        return float('inf')

    def categorize_by_p_value(p_val: float) -> str:
        if p_val < 1e-10:
            return 'Very Significant (<1e-10)'
        elif p_val < 1e-5:
            return 'Significant (1e-10 to 1e-5)'
        elif p_val < 0.05:
            return 'Marginally Significant (<0.05)'
        else:
            return 'Not Significant'

    df['chromosome'] = df['location'].apply(parse_chromosome)
    if 'attributes' in df.columns:
        df['p_val'] = df['attributes'].apply(get_p_value)
    else:
        df['p_val'] = float('inf')  # Default when no attributes available
    df['category'] = df.apply(lambda row: row['chromosome'] if row['chromosome'] != 'Unknown' else categorize_by_p_value(row['p_val']), axis=1)
    df = df.sort_values(by=['category', 'p_val'], ascending=[True, True])

    category_counts = df['category'].value_counts()
    total_items = len(df)
    selected = []

    for cat, count in category_counts.items():
        prop = count / total_items
        num_to_select = max(1, round(prop * target_count))
        cat_df = df[df['category'] == cat].head(num_to_select)
        selected.extend(cat_df.to_dict(orient='records'))

    if len(selected) > target_count:
        selected = random.sample(selected, target_count)

    if len(selected) < target_count // 2:
        selected = random.sample(results, min(target_count, len(results)))

    for item in selected:
        item.pop('category', None)
        item.pop('p_val', None)
        item.pop('chromosome', None)

    return selected

def post_process_region(results: List[Dict[str, Any]], target_count: int = 20) -> List[Dict[str, Any]]:
    """
    Post-processes results from get_phenotype_by_region.
    Flattens phenotype_associations, categorizes by source or ontology, sorts by p_value if present, selects diverse IDs.
    """
    # Handle case where results might not be a list
    if not results:
        return []

    # Flatten: Explode phenotype_associations into separate rows
    flattened = []
    for item in results:
        if 'phenotype_associations' in item and isinstance(item['phenotype_associations'], list):
            for assoc in item['phenotype_associations']:
                flat_item = assoc.copy()
                flat_item['id'] = item.get('id')
                flattened.append(flat_item)
        else:
            flattened.append(item)

    df = pd.DataFrame(flattened)
    df = df.dropna(subset=['description'])

    def get_p_value(attrs: dict) -> float:
        if isinstance(attrs, dict) and 'p_value' in attrs:
            try:
                return float(attrs['p_value'])
            except ValueError:
                return float('inf')
        return float('inf')

    # Categorize by source or first ontology if available
    def get_category(row):
        if 'source' in row:
            return row['source']
        elif 'ontology_accessions' in row and row['ontology_accessions']:
            ont_acc = row['ontology_accessions']
            if isinstance(ont_acc, list) and ont_acc:
                return ont_acc[0].split(':')[0]  # e.g., 'EFO', 'HP'
            elif isinstance(ont_acc, str):
                return ont_acc.split(':')[0]
        return 'Unknown'

    df['category'] = df.apply(get_category, axis=1)
    if 'attributes' in df.columns:
        df['p_val'] = df['attributes'].apply(get_p_value)
    else:
        df['p_val'] = float('inf')  # Default when no attributes available
    df = df.sort_values(by=['category', 'p_val'], ascending=[True, True])

    category_counts = df['category'].value_counts()
    total_items = len(df)
    selected = []

    for cat, count in category_counts.items():
        prop = count / total_items
        num_to_select = max(1, round(prop * target_count))
        cat_df = df[df['category'] == cat].head(num_to_select)
        selected.extend(cat_df.to_dict(orient='records'))

    if len(selected) > target_count:
        selected = random.sample(selected, target_count)

    if len(selected) < target_count // 2:
        selected = random.sample(results, min(target_count, len(results)))  # Fallback to original if flattened is small

    for item in selected:
        item.pop('category', None)
        item.pop('p_val', None)

    return selected