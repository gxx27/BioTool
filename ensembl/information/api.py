import requests
from typing import Any, Dict, Optional

# Import postprocess from the same directory
from .postprocess import summarize_species, summarize_geno_division, summarize_geno_accession, summarize_assembly, summarize_geno_taxonomy, summarize_compara_sets

BASE_URL = "https://rest.ensembl.org"


def _to_bool01(value: Optional[bool]) -> Optional[str]:
    if value is None:
        return None
    return "1" if value else "0"


def _get_json(url: str, params: Dict[str, Any], return_response: bool = False) -> Any:
    headers = {"Accept": "application/json"}
    response = requests.get(url, headers=headers, params=params)
    if return_response:
        return response
    else:
        try:
            return response.json()
        except Exception:
            return response.text


def get_info_analysis(species: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/analysis/{species}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_assembly(
    species: str,
    bands: Optional[bool] = None,
    callback: Optional[str] = None,
    synonyms: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/assembly/{species}"
    params: Dict[str, Any] = {}
    if bands is not None:
        params["bands"] = _to_bool01(bands)
    if callback:
        params["callback"] = callback
    if synonyms is not None:
        params["synonyms"] = _to_bool01(synonyms)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_assembly(result)
    return result


def get_info_assembly_region(
    region_name: str,
    species: str,
    bands: Optional[bool] = None,
    callback: Optional[str] = None,
    synonyms: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/assembly/{species}/{region_name}"
    params: Dict[str, Any] = {}
    if bands is not None:
        params["bands"] = _to_bool01(bands)
    if callback:
        params["callback"] = callback
    if synonyms is not None:
        params["synonyms"] = _to_bool01(synonyms)
    return _get_json(url, params, return_response=return_response)


def get_info_biotypes(species: str, callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/biotypes/{species}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_biotypes_groups(
    group: Optional[str] = None,
    object_type: Optional[str] = None,
    callback: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    # Without group provided: /info/biotypes/groups/
    if group:
        url = f"{BASE_URL}/info/biotypes/groups/{group}"
        if object_type:
            url = f"{url}/{object_type}"
    else:
        url = f"{BASE_URL}/info/biotypes/groups/"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_biotypes_name(
    name: str,
    object_type: Optional[str] = None,
    callback: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/biotypes/name/{name}"
    if object_type:
        url = f"{url}/{object_type}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_compara_methods(
    callback: Optional[str] = None,
    klass: Optional[str] = None,
    compara: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/compara/methods"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if klass:
        params["class"] = klass
    if compara:
        params["compara"] = compara
    return _get_json(url, params, return_response=return_response)


def get_info_compara_species_sets(
    method: str,
    callback: Optional[str] = None,
    compara: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/compara/species_sets/{method}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if compara:
        params["compara"] = compara
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_compara_sets(result)
    return result


def get_info_data(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/data/"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_eg_version(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/eg_version"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_external_dbs(
    species: str,
    callback: Optional[str] = None,
    feature: Optional[str] = None,
    filter_like: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/external_dbs/{species}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if feature:
        params["feature"] = feature
    if filter_like:
        params["filter"] = filter_like
    return _get_json(url, params, return_response=return_response)


def get_info_divisions(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/divisions"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_genomes(
    name: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/genomes/{name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    return _get_json(url, params, return_response=return_response)


def get_info_genomes_accession(
    accession: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/genomes/accession/{accession}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_geno_accession(result)
    return result


def get_info_genomes_assembly(
    assembly_id: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/genomes/assembly/{assembly_id}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    return _get_json(url, params, return_response=return_response)


def get_info_genomes_division(
    division: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/genomes/division/{division}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_geno_division(result)
    return result


def get_info_genomes_taxonomy(
    taxon_name: str,
    callback: Optional[str] = None,
    expand: Optional[bool] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/genomes/taxonomy/{taxon_name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if expand is not None:
        params["expand"] = _to_bool01(expand)
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_geno_taxonomy(result)
    return result


def get_info_ping(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/ping"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_rest(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/rest"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_software(callback: Optional[str] = None, return_response: bool = False) -> Any:
    url = f"{BASE_URL}/info/software"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_species(
    callback: Optional[str] = None,
    division: Optional[str] = None,
    hide_strain_info: Optional[bool] = None,
    strain_collection: Optional[str] = None,
    return_response: bool = False,
    postprocess: bool = True,
) -> Any:
    url = f"{BASE_URL}/info/species"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if division:
        params["division"] = division
    if hide_strain_info is not None:
        params["hide_strain_info"] = _to_bool01(hide_strain_info)
    if strain_collection:
        params["strain_collection"] = strain_collection
    result = _get_json(url, params, return_response=return_response)
    if postprocess:
        result = summarize_species(result)
    return result


def get_info_variation_sources(
    species: str,
    callback: Optional[str] = None,
    filter: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/variation/{species}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if filter:
        params["filter"] = filter
    return _get_json(url, params, return_response=return_response)


def get_info_variation_consequence_types(
    callback: Optional[str] = None,
    rank: Optional[bool] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/variation/consequence_types"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if rank is not None:
        params["rank"] = _to_bool01(rank)
    return _get_json(url, params, return_response=return_response)


def get_info_variation_population_name(
    population_name: str,
    species: str,
    callback: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/variation/populations/{species}/{population_name}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    return _get_json(url, params, return_response=return_response)


def get_info_variation_populations(
    species: str,
    callback: Optional[str] = None,
    filter: Optional[str] = None,
    return_response: bool = False,
) -> Any:
    url = f"{BASE_URL}/info/variation/populations/{species}"
    params: Dict[str, Any] = {}
    if callback:
        params["callback"] = callback
    if filter:
        params["filter"] = filter
    return _get_json(url, params, return_response=return_response)
