"""Postprocessing helpers for NCBI EFetch responses."""

from collections import Counter
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple

MAX_REFERENCES = 5
MAX_FEATURES = 5
MAX_XREFS = 5
MAX_LIST_ITEMS = 5
MAX_DOCUMENTS = 10
MAX_ATTRIBUTES = 8
MAX_GENE_PRODUCTS = 3
MAX_PUBMED_IDS = 5
MAX_AUTHORS = 5
MAX_TSEQ = 5
MAX_PUBMED_ARTICLES = 5
MAX_ABSTRACT_SECTIONS = 3
MAX_MESH_TERMS = 8
MAX_PUBLICATION_TYPES = 4
MAX_KEYWORDS = 8
MAX_GRANTS = 4
MAX_CHEMICALS = 5
MAX_ARTICLE_IDS = 4
SEQUENCE_PREVIEW = 80
MAX_PMC_ARTICLES = 3
MAX_PMC_CONTRIBUTORS = 5
MAX_PMC_AFFILIATIONS = 4
MAX_PMC_FUNDERS = 4
MAX_PMC_ABSTRACT_PARAGRAPHS = 3
MAX_PMC_SECTION_TITLES = 4
MAX_EXCHANGE_DOCS = 5
MAX_SNP_MAFS = 5
MAX_SNP_GENES = 5
MAX_SNP_FUNCTION_CLASSES = 6
MAX_SRA_PACKAGES = 3
MAX_SRA_SAMPLE_ATTRIBUTES = 8
MAX_SRA_RUNS = 3
MAX_SRA_FILES = 5
MAX_SRA_CLOUD_FILES = 5
MAX_SRA_POOL_MEMBERS = 5
MAX_TAXA = 5
MAX_TAXON_SYNONYMS = 6
MAX_TAXON_COMMON_NAMES = 6
MAX_TAXON_INCLUDES = 4
MAX_TAXON_AUTHORITY_NAMES = 3
MAX_TAXON_LINEAGE = 12
TEXT_TRUNCATE = 100


def _trim_text(value: Optional[str], limit: int = TEXT_TRUNCATE) -> Optional[str]:
    if not value:
        return None
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def _parse_if_xml(response: str) -> Optional[ET.Element]:
    try:
        return ET.fromstring(response)
    except ET.ParseError:
        return None


def _collect_text(node: Optional[ET.Element], tag: str) -> Optional[str]:
    if node is None:
        return None
    child = node.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return None


def _collect_rich_text(node: Optional[ET.Element]) -> Optional[str]:
    if node is None:
        return None
    text = "".join(node.itertext()).strip()
    return text or None


def _format_date(parts: List[Optional[str]]) -> Optional[str]:
    filtered = [part for part in parts if part]
    if not filtered:
        return None
    return "-".join(filtered)


def _collect_all(node: Optional[ET.Element], tag: str) -> List[str]:
    if node is None:
        return []
    values: List[str] = []
    for child in node.findall(tag):
        if child.text:
            text = child.text.strip()
            if text:
                values.append(text)
    return values


def _collect_first_text(node: Optional[ET.Element], tag: str) -> Optional[str]:
    if node is None:
        return None
    return _collect_rich_text(node.find(tag))


def _local_tag(element: ET.Element) -> str:
    tag = element.tag
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _child_text(node: Optional[ET.Element], name: str) -> Optional[str]:
    if node is None:
        return None
    for child in node:
        if _local_tag(child) == name and child.text:
            text = child.text.strip()
            if text:
                return text
    return None


def _iter_children(node: Optional[ET.Element], name: str) -> List[ET.Element]:
    if node is None:
        return []
    return [child for child in node if _local_tag(child) == name]


def _find_child(node: Optional[ET.Element], name: str) -> Optional[ET.Element]:
    if node is None:
        return None
    for child in node:
        if _local_tag(child) == name:
            return child
    return None


def _collect_child_texts(node: Optional[ET.Element], name: str, limit: Optional[int] = None) -> List[str]:
    if node is None:
        return []
    texts: List[str] = []
    for child in _iter_children(node, name):
        if child.text:
            text = child.text.strip()
            if text:
                texts.append(text)
        if limit is not None and len(texts) >= limit:
            break
    return texts


def _extract_pub_date(article_meta: Optional[ET.Element], preferred_types: Optional[List[str]] = None) -> Optional[str]:
    if article_meta is None:
        return None

    if preferred_types is None:
        preferred_types = ["epub", "ppub", "collection"]

    pub_dates = article_meta.findall("pub-date")
    for pub_type in preferred_types:
        for pub_date in pub_dates:
            if pub_date.get("pub-type") == pub_type:
                date_value = _format_date([
                    _collect_text(pub_date, "year"),
                    _collect_text(pub_date, "month"),
                    _collect_text(pub_date, "day"),
                ])
                if date_value:
                    return date_value

    if pub_dates:
        fallback = pub_dates[0]
        return _format_date([
            _collect_text(fallback, "year"),
            _collect_text(fallback, "month"),
            _collect_text(fallback, "day"),
        ])

    return None


def _summarize_references(gbseq: ET.Element) -> List[Dict[str, Any]]:
    references: List[Dict[str, Any]] = []
    references_node = gbseq.find("GBSeq_references")
    if references_node is None:
        return references

    for reference in references_node.findall("GBReference")[:MAX_REFERENCES]:
        summary: Dict[str, Any] = {}
        ref_id = _collect_text(reference, "GBReference_reference")
        if ref_id:
            summary["reference"] = ref_id
        position = _collect_text(reference, "GBReference_position")
        if position:
            summary["position"] = position
        authors_node = reference.find("GBReference_authors")
        if authors_node is not None:
            authors = [a.text.strip() for a in authors_node.findall("GBAuthor") if a.text]
            if authors:
                summary["authors"] = authors
        title = _collect_text(reference, "GBReference_title")
        if title:
            summary["title"] = _trim_text(title)
        journal = _collect_text(reference, "GBReference_journal")
        if journal:
            summary["journal"] = _trim_text(journal)
        if summary:
            references.append(summary)
    return references


ALLOWED_QUALIFIERS = {
    "gene",
    "locus_tag",
    "old_locus_tag",
    "product",
    "note",
    "EC_number",
    "GO_function",
    "GO_process",
    "GO_component",
    "protein_id",
    "inference",
}


def _summarize_features(gbseq: ET.Element) -> List[Dict[str, Any]]:
    feature_table = gbseq.find("GBSeq_feature-table")
    if feature_table is None:
        return []

    summaries: List[Dict[str, Any]] = []
    for feature in feature_table.findall("GBFeature")[:MAX_FEATURES]:
        summary: Dict[str, Any] = {}
        key = _collect_text(feature, "GBFeature_key")
        if key:
            summary["key"] = key
        location = _collect_text(feature, "GBFeature_location")
        if location:
            summary["location"] = location

        quals_node = feature.find("GBFeature_quals")
        if quals_node is not None:
            qualifiers: Dict[str, Any] = {}
            for qualifier in quals_node.findall("GBQualifier"):
                name = _collect_text(qualifier, "GBQualifier_name")
                value = _collect_text(qualifier, "GBQualifier_value")
                if not name or not value:
                    continue
                if name not in ALLOWED_QUALIFIERS:
                    continue
                qualifiers[name] = _trim_text(value)
            if qualifiers:
                summary["qualifiers"] = qualifiers

        if summary:
            summaries.append(summary)

    total_features = len(feature_table.findall("GBFeature"))
    if total_features > MAX_FEATURES:
        summaries.append({"note": f"{total_features - MAX_FEATURES} additional features truncated"})

    return summaries


def _summarize_xrefs(gbseq: ET.Element) -> List[Dict[str, Any]]:
    xrefs_node = gbseq.find("GBSeq_xrefs")
    if xrefs_node is None:
        return []

    xrefs: List[Dict[str, Any]] = []
    xref_elements = xrefs_node.findall("GBXref")
    for xref in xref_elements[:MAX_XREFS]:
        db = _collect_text(xref, "GBXref_dbname")
        identifier = _collect_text(xref, "GBXref_id")
        if db or identifier:
            xrefs.append({"dbname": db, "id": identifier})

    if len(xref_elements) > MAX_XREFS:
        xrefs.append({"note": f"{len(xref_elements) - MAX_XREFS} additional xrefs truncated"})

    return [xref for xref in xrefs if any(xref.values())]


def _summarize_gbseq(seq_node: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    overview_fields = {
        "locus": "GBSeq_locus",
        "definition": "GBSeq_definition",
        "accession": "GBSeq_primary-accession",
        "accession_version": "GBSeq_accession-version",
        "length": "GBSeq_length",
        "moltype": "GBSeq_moltype",
        "topology": "GBSeq_topology",
        "organism": "GBSeq_organism",
        "taxonomy": "GBSeq_taxonomy",
        "create_date": "GBSeq_create-date",
        "update_date": "GBSeq_update-date",
        "project": "GBSeq_project",
    }

    overview: Dict[str, Any] = {}
    for key, tag in overview_fields.items():
        value = _collect_text(seq_node, tag)
        if value:
            overview[key] = value
    if overview:
        summary["overview"] = overview

    other_ids = _collect_all(seq_node.find("GBSeq_other-seqids") if seq_node is not None else None, "GBSeqid")
    if other_ids:
        summary["other_seqids"] = other_ids[:MAX_XREFS]

    keywords = _collect_all(seq_node.find("GBSeq_keywords"), "GBKeyword")
    if keywords:
        summary["keywords"] = keywords

    references = _summarize_references(seq_node)
    if references:
        summary["references"] = references

    comment = _collect_text(seq_node, "GBSeq_comment")
    if comment:
        summary["comment"] = _trim_text(comment, limit=TEXT_TRUNCATE * 2)

    features = _summarize_features(seq_node)
    if features:
        summary["features"] = features

    xrefs = _summarize_xrefs(seq_node)
    if xrefs:
        summary["xrefs"] = xrefs

    contig = _collect_text(seq_node, "GBSeq_contig")
    if contig:
        summary["contig"] = _trim_text(contig)

    return summary


def _trim_list(values: List[Any], limit: int = MAX_LIST_ITEMS) -> List[Any]:
    if len(values) <= limit:
        return values
    trimmed = values[:limit]
    trimmed.append({"note": f"{len(values) - limit} more"})
    return trimmed


def _summarize_target(target: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if target is None:
        return None

    summary: Dict[str, Any] = {}
    for attr in ("capture", "material", "sample_scope"):
        value = target.get(attr)
        if value:
            summary[attr] = value

    organism = target.find("Organism")
    if organism is not None:
        organism_info: Dict[str, Any] = {}
        for attr in ("species", "taxID"):
            value = organism.get(attr)
            if value:
                organism_info[attr] = value
        for child_tag in ("OrganismName", "Label", "Strain", "IsolateName", "Cultivar", "Supergroup"):
            value = _collect_text(organism, child_tag)
            if value:
                organism_info[child_tag.lower()] = value
        if organism_info:
            summary["organism"] = organism_info

    return summary or None


def _summarize_project_type(project_type: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if project_type is None:
        return None

    submission = project_type.find("ProjectTypeSubmission")
    if submission is None:
        return None

    summary: Dict[str, Any] = {}

    target_summary = _summarize_target(submission.find("Target"))
    if target_summary:
        summary["target"] = target_summary

    method = submission.find("Method")
    if method is not None:
        method_type = method.get("method_type")
        if method_type:
            summary["method_type"] = method_type

    def _collect_datatypes(node_tag: str) -> Optional[List[str]]:
        node = submission.find(node_tag)
        if node is None:
            return None
        values = [child.text.strip() for child in node.findall("DataType") if child.text]
        if values:
            return values
        return None

    for tag, key in (("Objectives", "objectives"), ("ProjectDataTypeSet", "data_types"), ("IntendedDataTypeSet", "intended_data_types")):
        values = _collect_datatypes(tag)
        if values:
            summary[key] = _trim_list(values)

    return summary or None


def _summarize_project_descr(descr: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if descr is None:
        return None

    summary: Dict[str, Any] = {}
    for tag in ("Name", "Title", "Description"):
        value = _collect_text(descr, tag)
        if value:
            summary[tag.lower()] = _trim_text(value)

    release = _collect_text(descr, "ProjectReleaseDate")
    if release:
        summary["release_date"] = release

    relevance = descr.find("Relevance")
    if relevance is not None:
        relevance_info = {child.tag.lower(): child.text.strip() for child in relevance if child.text}
        if relevance_info:
            summary["relevance"] = relevance_info

    external_links = []
    for link in descr.findall("ExternalLink")[:MAX_LIST_ITEMS]:
        link_summary: Dict[str, Any] = {}
        label = link.get("label")
        if label:
            link_summary["label"] = label
        url = _collect_text(link, "URL")
        if url:
            link_summary["url"] = url
        if link_summary:
            external_links.append(link_summary)
    if external_links:
        summary["external_links"] = external_links

    locus_prefix = descr.find("LocusTagPrefix")
    if locus_prefix is not None:
        prefix_summary = {"value": locus_prefix.text.strip() if locus_prefix.text else None}
        biosample_id = locus_prefix.get("biosample_id")
        if biosample_id:
            prefix_summary["biosample_id"] = biosample_id
        prefix_summary = {k: v for k, v in prefix_summary.items() if v}
        if prefix_summary:
            summary["locus_tag_prefix"] = prefix_summary

    return summary or None


def _summarize_project(project: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if project is None:
        return None

    summary: Dict[str, Any] = {}

    project_id = project.find("ProjectID")
    if project_id is not None:
        id_summary: Dict[str, Any] = {}
        archive = project_id.find("ArchiveID")
        if archive is not None:
            for attr in ("accession", "archive", "id"):
                value = archive.get(attr)
                if value:
                    id_summary[attr] = value
        local_ids = [node.text.strip() for node in project_id.findall("LocalID") if node.text]
        if local_ids:
            id_summary["local_ids"] = _trim_list(local_ids)
        if id_summary:
            summary["identifiers"] = id_summary

    descr_summary = _summarize_project_descr(project.find("ProjectDescr"))
    if descr_summary:
        summary["description"] = descr_summary

    type_summary = _summarize_project_type(project.find("ProjectType"))
    if type_summary:
        summary["project_type"] = type_summary

    return summary or None


def _summarize_submission(submission: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if submission is None:
        return None

    summary: Dict[str, Any] = {}
    for attr in ("last_update", "submitted", "submission_id"):
        value = submission.get(attr)
        if value:
            summary[attr] = value

    description = submission.find("Description")
    if description is not None:
        desc_summary: Dict[str, Any] = {}
        access = _collect_text(description, "Access")
        if access:
            desc_summary["access"] = access
        organization = description.find("Organization")
        if organization is not None:
            org_summary: Dict[str, Any] = {}
            for attr in ("role", "type", "url"):
                value = organization.get(attr)
                if value:
                    org_summary[attr] = value
            name = _collect_text(organization, "Name")
            if name:
                org_summary["name"] = name
            if org_summary:
                desc_summary["organization"] = org_summary
        if desc_summary:
            summary["description"] = desc_summary

    actions = [action.get("action_id") for action in submission.findall("Action") if action.get("action_id")]
    if actions:
        summary["actions"] = _trim_list(actions)

    return summary or None


def _summarize_project_links(project_links: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if project_links is None:
        return None

    summaries: List[Dict[str, Any]] = []
    for link in project_links.findall("Link")[:MAX_LIST_ITEMS]:
        link_summary: Dict[str, Any] = {}
        proj_ref = link.find("ProjectIDRef")
        if proj_ref is not None:
            proj_info = {attr: proj_ref.get(attr) for attr in ("archive", "id", "accession") if proj_ref.get(attr)}
            if proj_info:
                link_summary["project"] = proj_info
        hierarchical = link.find("Hierarchical")
        if hierarchical is not None:
            hier_summary: Dict[str, Any] = {}
            hier_type = hierarchical.get("type")
            if hier_type:
                hier_summary["type"] = hier_type
            member = hierarchical.find("MemberID")
            if member is not None:
                member_info = {attr: member.get(attr) for attr in ("archive", "id", "accession") if member.get(attr)}
                if member_info:
                    hier_summary["member"] = member_info
            if hier_summary:
                link_summary["hierarchical"] = hier_summary
        if link_summary:
            summaries.append(link_summary)
    if summaries:
        return summaries
    return None


def _summarize_document_summary(doc: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    uid = doc.get("uid")
    if uid:
        summary["uid"] = uid

    project_summary = _summarize_project(doc.find("Project"))
    if project_summary:
        summary["project"] = project_summary

    submission_summary = _summarize_submission(doc.find("Submission"))
    if submission_summary:
        summary["submission"] = submission_summary

    project_links = _summarize_project_links(doc.find("ProjectLinks"))
    if project_links:
        summary["project_links"] = project_links

    return summary


def _summarize_recordset(root: ET.Element) -> Dict[str, Any]:
    documents = root.findall("DocumentSummary")
    summaries: List[Dict[str, Any]] = []
    for doc in documents[:MAX_DOCUMENTS]:
        summaries.append(_summarize_document_summary(doc))

    if len(documents) > MAX_DOCUMENTS:
        summaries.append({"note": f"{len(documents) - MAX_DOCUMENTS} additional records truncated"})

    return {
        "record_count": len(documents),
        "records": summaries,
    }


def _summarize_biosample_ids(ids_node: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if ids_node is None:
        return None
    summaries: Dict[str, Any] = {}
    for id_node in ids_node.findall("Id")[:MAX_LIST_ITEMS]:
        db = id_node.get("db")
        value = id_node.text.strip() if id_node.text else None
        if db and value:
            summaries.setdefault(db, []).append(value)
    if not summaries:
        return None
    for key in list(summaries.keys()):
        summaries[key] = _trim_list(summaries[key])
    return summaries


def _summarize_biosample_attributes(attrs_node: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if attrs_node is None:
        return None
    attributes: Dict[str, Any] = {}
    for attr in attrs_node.findall("Attribute")[:MAX_ATTRIBUTES]:
        name = attr.get("display_name") or attr.get("attribute_name")
        value = attr.text.strip() if attr.text else None
        if name and value:
            attributes[name] = value
    total_attrs = len(attrs_node.findall("Attribute"))
    if total_attrs > MAX_ATTRIBUTES:
        attributes["note"] = f"{total_attrs - MAX_ATTRIBUTES} more"
    return attributes or None


def _summarize_biosample_links(links_node: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if links_node is None:
        return None
    links: List[Dict[str, Any]] = []
    for link in links_node.findall("Link")[:MAX_LIST_ITEMS]:
        summary: Dict[str, Any] = {
            "type": link.get("type"),
            "target": link.get("target"),
            "label": link.get("label"),
        }
        value = link.text.strip() if link.text else None
        if value:
            summary["value"] = value
        summary = {k: v for k, v in summary.items() if v}
        if summary:
            links.append(summary)
    total_links = len(links_node.findall("Link"))
    if total_links > MAX_LIST_ITEMS:
        links.append({"note": f"{total_links - MAX_LIST_ITEMS} more"})
    return links or None


def _summarize_biosample(biosample: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    for attr in ("access", "publication_date", "last_update", "submission_date", "id", "accession"):
        value = biosample.get(attr)
        if value:
            summary[attr] = value

    ids_summary = _summarize_biosample_ids(biosample.find("Ids"))
    if ids_summary:
        summary["ids"] = ids_summary

    description = biosample.find("Description")
    if description is not None:
        desc_summary: Dict[str, Any] = {}
        title = _collect_text(description, "Title")
        if title:
            desc_summary["title"] = _trim_text(title)
        organism = description.find("Organism")
        if organism is not None:
            organism_summary = {attr: organism.get(attr) for attr in ("taxonomy_id", "taxonomy_name") if organism.get(attr)}
            name = _collect_text(organism, "OrganismName")
            if name:
                organism_summary["name"] = name
            if organism_summary:
                desc_summary["organism"] = organism_summary
        if desc_summary:
            summary["description"] = desc_summary

    owner = biosample.find("Owner")
    if owner is not None:
        name = owner.find("Name")
        owner_summary: Dict[str, Any] = {}
        if name is not None:
            if name.text and name.text.strip():
                owner_summary["name"] = name.text.strip()
            for attr in ("abbreviation", "url"):
                value = name.get(attr)
                if value:
                    owner_summary[attr] = value
        if owner_summary:
            summary["owner"] = owner_summary

    models = [model.text.strip() for model in biosample.findall("Models/Model") if model.text]
    if models:
        summary["models"] = _trim_list(models)

    package = biosample.find("Package")
    if package is not None:
        package_summary = {
            "name": package.text.strip() if package.text else None,
            "display_name": package.get("display_name"),
        }
        summary["package"] = {k: v for k, v in package_summary.items() if v}

    attributes = _summarize_biosample_attributes(biosample.find("Attributes"))
    if attributes:
        summary["attributes"] = attributes

    links = _summarize_biosample_links(biosample.find("Links"))
    if links:
        summary["links"] = links

    status = biosample.find("Status")
    if status is not None:
        status_summary = {attr: status.get(attr) for attr in ("status", "when") if status.get(attr)}
        if status_summary:
            summary["status"] = status_summary

    return summary


def _summarize_biosample_set(root: ET.Element) -> Dict[str, Any]:
    biosamples = root.findall("BioSample")
    summaries: List[Dict[str, Any]] = []
    for biosample in biosamples[:MAX_DOCUMENTS]:
        summaries.append(_summarize_biosample(biosample))
    if len(biosamples) > MAX_DOCUMENTS:
        summaries.append({"note": f"{len(biosamples) - MAX_DOCUMENTS} additional biosamples truncated"})
    return {
        "record_count": len(biosamples),
        "records": summaries,
    }


def _summarize_id_list(root: ET.Element) -> Dict[str, Any]:
    ids = [node.text.strip() for node in root.findall("Id") if node.text]
    return {
        "record_count": len(ids),
        "ids": _trim_list(ids),
    }


def _collect_date_std(date_std: Optional[ET.Element]) -> Optional[str]:
    if date_std is None:
        return None
    year = _collect_text(date_std, "Date-std_year")
    month = _collect_text(date_std, "Date-std_month")
    day = _collect_text(date_std, "Date-std_day")
    if not year:
        return None
    components = [year]
    if month:
        components.append(month.zfill(2) if month.isdigit() else month)
    if day:
        components.append(day.zfill(2) if day.isdigit() else day)
    return "-".join(components)


def _summarize_entrezgene(entrez_gene: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}

    track = entrez_gene.find("Entrezgene_track-info/Gene-track")
    if track is not None:
        geneid = _collect_text(track, "Gene-track_geneid")
        if geneid:
            summary["gene_id"] = geneid
        create_std = track.find("Gene-track_create-date/Date/Date_std/Date-std")
        update_std = track.find("Gene-track_update-date/Date/Date_std/Date-std")
        created = _collect_date_std(create_std)
        updated = _collect_date_std(update_std)
        timeline = {k: v for k, v in {"created": created, "updated": updated}.items() if v}
        if timeline:
            summary["timeline"] = timeline

    gene_type = entrez_gene.find("Entrezgene_type")
    if gene_type is not None:
        type_value = gene_type.get("value")
        if type_value:
            summary["type"] = type_value

    biosource = entrez_gene.find("Entrezgene_source/BioSource")
    if biosource is not None:
        organism = biosource.find("BioSource_org/Org-ref")
        organism_summary: Dict[str, Any] = {}
        if organism is not None:
            taxname = _collect_text(organism, "Org-ref_taxname")
            if taxname:
                organism_summary["taxname"] = taxname
            tax_id = _collect_text(organism.find("Org-ref_db/Dbtag/Dbtag_tag/Object-id"), "Object-id_id")
            if tax_id:
                organism_summary["tax_id"] = tax_id
            lineage = _collect_text(organism.find("Org-ref_orgname/OrgName"), "OrgName_lineage")
            if lineage:
                organism_summary["lineage"] = _trim_text(lineage)
            modifiers = []
            for mod in organism.findall("Org-ref_orgname/OrgName/OrgName_mod/OrgMod")[:MAX_LIST_ITEMS]:
                label = mod.find("OrgMod_subtype")
                name = mod.find("OrgMod_subname")
                modifier = {
                    "label": label.get("value") if label is not None and label.get("value") else None,
                    "value": name.text.strip() if name is not None and name.text else None,
                }
                modifier = {k: v for k, v in modifier.items() if v}
                if modifier:
                    modifiers.append(modifier)
            if modifiers:
                organism_summary["modifiers"] = modifiers
        if organism_summary:
            summary["organism"] = organism_summary

        subtypes = []
        for subtype in biosource.findall("BioSource_subtype/SubSource")[:MAX_LIST_ITEMS]:
            label = subtype.get("value")
            value = _collect_text(subtype, "SubSource_name")
            if label or value:
                subtypes.append({k: v for k, v in {"label": label, "value": value}.items() if v})
        if subtypes:
            summary["source_subtypes"] = subtypes

    locus_tag = _collect_text(entrez_gene.find("Entrezgene_gene/Gene-ref"), "Gene-ref_locus-tag")
    if locus_tag:
        summary["locus_tag"] = locus_tag

    product_desc = _collect_text(entrez_gene.find("Entrezgene_prot/Prot-ref"), "Prot-ref_desc")
    if product_desc:
        summary["product"] = product_desc

    locus = entrez_gene.find("Entrezgene_locus/Gene-commentary")
    if locus is not None:
        coords = locus.find("Gene-commentary_seqs/Seq-loc/Seq-loc_int/Seq-interval")
        if coords is not None:
            coordinate = {
                "accession": _collect_text(locus, "Gene-commentary_accession"),
                "from": _collect_text(coords, "Seq-interval_from"),
                "to": _collect_text(coords, "Seq-interval_to"),
            }
            strand_node = coords.find("Seq-interval_strand/Na-strand")
            if strand_node is not None and strand_node.get("value"):
                coordinate["strand"] = strand_node.get("value")
            coordinate = {k: v for k, v in coordinate.items() if v}
            if coordinate:
                summary["genomic_location"] = coordinate

        products = []
        for product in locus.findall("Gene-commentary_products/Gene-commentary")[:MAX_GENE_PRODUCTS]:
            product_summary = {
                "label": _collect_text(product, "Gene-commentary_label"),
                "accession": _collect_text(product, "Gene-commentary_accession"),
            }
            pubmed_ids = [pub.text.strip() for pub in product.findall("Gene-commentary_refs/Pub/Pub_pmid/PubMedId") if pub.text]
            if pubmed_ids:
                product_summary["pubmed"] = pubmed_ids[:MAX_PUBMED_IDS]
            product_summary = {k: v for k, v in product_summary.items() if v}
            if product_summary:
                products.append(product_summary)
        if products:
            summary["products"] = products

    return summary


def _summarize_entrezgene_set(root: ET.Element) -> Dict[str, Any]:
    genes = root.findall("Entrezgene")
    summaries: List[Dict[str, Any]] = []
    for gene in genes[:MAX_DOCUMENTS]:
        summaries.append(_summarize_entrezgene(gene))
    if len(genes) > MAX_DOCUMENTS:
        summaries.append({"note": f"{len(genes) - MAX_DOCUMENTS} additional genes truncated"})
    return {
        "record_count": len(genes),
        "records": summaries,
    }


def _collect_simple_date(date_node: Optional[ET.Element]) -> Optional[str]:
    if date_node is None:
        return None
    year = _collect_text(date_node, "Year")
    month = _collect_text(date_node, "Month")
    day = _collect_text(date_node, "Day")
    if not year:
        return None
    components = [year]
    if month:
        components.append(month.zfill(2) if month.isdigit() else month)
    if day:
        components.append(day.zfill(2) if day.isdigit() else day)
    return "-".join(components)


def _summarize_author_list(author_list: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if author_list is None:
        return None
    authors: List[Dict[str, Any]] = []
    for author in author_list.findall("Author")[:MAX_AUTHORS]:
        summary = {
            "last": _collect_text(author, "LastName"),
            "first": _collect_text(author, "ForeName"),
            "initials": _collect_text(author, "Initials"),
            "role": _collect_text(author, "Role"),
        }
        summary = {k: v for k, v in summary.items() if v}
        if summary:
            authors.append(summary)
    total_authors = len(author_list.findall("Author"))
    if total_authors > MAX_AUTHORS:
        authors.append({"note": f"{total_authors - MAX_AUTHORS} more"})
    return authors or None


def _summarize_nlm_catalog_record(record: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {
        "owner": record.get("Owner"),
        "status": record.get("Status"),
    }

    nlm_id = _collect_text(record, "NlmUniqueID")
    if nlm_id:
        summary["nlm_id"] = nlm_id

    dates = {}
    for tag in ("DateCreated", "DateRevised", "DateAuthorized", "DateCompleted"):
        date_value = _collect_simple_date(record.find(tag))
        if date_value:
            dates[tag.replace("Date", "").lower()] = date_value
    if dates:
        summary["dates"] = dates

    title_main = record.find("TitleMain")
    if title_main is not None:
        title_summary = {
            "title": _collect_text(title_main, "Title"),
            "info": _trim_text(_collect_text(title_main, "OtherInformation")),
        }
        title_summary = {k: v for k, v in title_summary.items() if v}
        if title_summary:
            summary["title"] = title_summary

    related_titles = []
    for related in record.findall("TitleRelated")[:MAX_LIST_ITEMS]:
        related_summary = {
            "type": related.get("TitleType"),
            "title": _collect_text(related, "Title"),
        }
        related_summary = {k: v for k, v in related_summary.items() if v}
        if related_summary:
            related_titles.append(related_summary)
    if related_titles:
        summary["related_titles"] = related_titles

    authors = _summarize_author_list(record.find("AuthorList"))
    if authors:
        summary["authors"] = authors

    resource_info = record.find("ResourceInfo")
    if resource_info is not None:
        resource_summary: Dict[str, Any] = {
            "type": _collect_text(resource_info, "TypeOfResource"),
            "issuance": _collect_text(resource_info, "Issuance"),
            "unit": _collect_text(resource_info, "ResourceUnit"),
        }
        media = resource_info.find("Resource")
        if media is not None:
            media_summary = {
                "content": _collect_text(media, "ContentType"),
                "media": _collect_text(media, "MediaType"),
                "carrier": _collect_text(media, "CarrierType"),
            }
            media_summary = {k: v for k, v in media_summary.items() if v}
            if media_summary:
                resource_summary["resource"] = media_summary
        resource_summary = {k: v for k, v in resource_summary.items() if v}
        if resource_summary:
            summary["resource"] = resource_summary

    pub_info = record.find("PublicationInfo")
    if pub_info is not None:
        pub_summary: Dict[str, Any] = {
            "country": _collect_text(pub_info, "Country"),
            "edition": _collect_text(pub_info, "Edition"),
            "first_year": _collect_text(pub_info, "PublicationFirstYear"),
        }
        imprint = pub_info.find("Imprint")
        if imprint is not None:
            imprint_summary = {
                "place": _collect_text(imprint, "Place"),
                "entity": _collect_text(imprint, "Entity"),
                "date": _collect_text(imprint, "DateIssued"),
                "full": _collect_text(imprint, "ImprintFull"),
            }
            imprint_summary = {k: v for k, v in imprint_summary.items() if v}
            if imprint_summary:
                pub_summary["imprint"] = imprint_summary
        projected = _collect_text(pub_info, "ProjectedPublicationDate")
        if projected:
            pub_summary["projected"] = projected
        pub_summary = {k: v for k, v in pub_summary.items() if v}
        if pub_summary:
            summary["publication"] = pub_summary

    language = _collect_text(record, "Language")
    if language:
        summary["language"] = language

    physical = record.find("PhysicalDescription")
    if physical is not None:
        extent = _collect_text(physical, "Extent")
        if extent:
            summary["physical"] = extent

    abstract = _collect_text(record.find("OtherAbstract"), "AbstractText")
    if abstract:
        summary["abstract"] = _trim_text(abstract)

    contents = _collect_text(record, "ContentsNote")
    if contents:
        summary["contents"] = _trim_text(contents, limit=TEXT_TRUNCATE * 2)

    notes = record.findall("GeneralNote")
    if notes:
        note_values = [_trim_text(note.text) for note in notes if note.text]
        if note_values:
            summary["notes"] = _trim_list([note for note in note_values if note])

    mesh_headings = [
        _collect_text(mesh, "DescriptorName")
        for mesh in record.findall("MeshHeadingList/MeshHeading")
        if _collect_text(mesh, "DescriptorName")
    ]
    if mesh_headings:
        summary["mesh_headings"] = _trim_list(mesh_headings)

    classification = _collect_text(record, "Classification")
    if classification:
        summary["classification"] = classification

    isbn_values = [isbn.text.strip() for isbn in record.findall("ISBN") if isbn.text]
    if isbn_values:
        summary["isbn"] = _trim_list(isbn_values)

    lccn = _collect_text(record, "LCCN")
    if lccn:
        summary["lccn"] = lccn

    return {k: v for k, v in summary.items() if v}


def _summarize_nlm_catalog(root: ET.Element) -> Dict[str, Any]:
    records = root.findall("NLMCatalogRecord")
    summaries: List[Dict[str, Any]] = []
    for record in records[:MAX_DOCUMENTS]:
        summaries.append(_summarize_nlm_catalog_record(record))
    if len(records) > MAX_DOCUMENTS:
        summaries.append({"note": f"{len(records) - MAX_DOCUMENTS} additional catalog records truncated"})
    return {
        "record_count": len(records),
        "records": summaries,
    }


def _summarize_grant_list(grant_list: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if grant_list is None:
        return None

    grants = grant_list.findall("Grant")
    if not grants:
        return None

    summaries: List[Dict[str, Any]] = []
    for grant in grants[:MAX_GRANTS]:
        summary: Dict[str, Any] = {
            "id": _collect_text(grant, "GrantID"),
            "agency": _collect_text(grant, "Agency"),
            "acronym": _collect_text(grant, "Acronym"),
            "country": _collect_text(grant, "Country"),
        }
        summary = {k: v for k, v in summary.items() if v}
        if summary:
            summaries.append(summary)

    if len(grants) > MAX_GRANTS:
        summaries.append({"note": f"{len(grants) - MAX_GRANTS} additional grants truncated"})

    return summaries or None


def _extract_pub_year(article: ET.Element) -> Optional[str]:
    medline = article.find("MedlineCitation")
    if medline is None:
        return None

    article_node = medline.find("Article")
    if article_node is not None:
        pub_date = article_node.find("Journal/JournalIssue/PubDate")
        if pub_date is not None:
            year = _collect_text(pub_date, "Year")
            if year:
                return year
        for article_date in article_node.findall("ArticleDate"):
            year = _collect_text(article_date, "Year")
            if year:
                return year

    date_completed = medline.find("DateCompleted")
    if date_completed is not None:
        year = _collect_text(date_completed, "Year")
        if year:
            return year

    pubmed_data = article.find("PubmedData")
    if pubmed_data is not None:
        history = pubmed_data.find("History")
        if history is not None:
            for pub_date in history.findall("PubMedPubDate"):
                if pub_date.get("PubStatus") in {"pubmed", "medline", "entrez"}:
                    year = _collect_text(pub_date, "Year")
                    if year:
                        return year

    return None


def _summarize_pubmed_article(article: ET.Element) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    summary: Dict[str, Any] = {}
    contributions: Dict[str, Any] = {
        "publication_types": [],
        "mesh_descriptors": [],
        "languages": [],
    }

    medline = article.find("MedlineCitation")
    if medline is None:
        return summary, contributions

    pmid = _collect_text(medline, "PMID")
    if pmid:
        summary["pmid"] = pmid

    status = medline.get("Status")
    if status:
        summary["status"] = status

    article_node = medline.find("Article")
    pub_year: Optional[str] = None
    journal_title: Optional[str] = None

    if article_node is not None:
        title = _collect_rich_text(article_node.find("ArticleTitle"))
        if title:
            summary["title"] = _trim_text(title, limit=TEXT_TRUNCATE * 2)

        journal_info: Dict[str, Any] = {}
        journal_node = article_node.find("Journal")
        if journal_node is not None:
            full_title = _collect_rich_text(journal_node.find("Title"))
            iso = _collect_text(journal_node, "ISOAbbreviation")
            journal_title = full_title or iso
            if full_title:
                journal_info["title"] = full_title
            if iso and iso != full_title:
                journal_info["iso"] = iso
            issue_node = journal_node.find("JournalIssue")
            if issue_node is not None:
                volume = _collect_text(issue_node, "Volume")
                issue = _collect_text(issue_node, "Issue")
                if volume:
                    journal_info["volume"] = volume
                if issue:
                    journal_info["issue"] = issue
                pub_date = issue_node.find("PubDate")
                if pub_date is not None:
                    date_value = _format_date([
                        _collect_text(pub_date, "Year"),
                        _collect_text(pub_date, "Month"),
                        _collect_text(pub_date, "Day"),
                    ])
                    if date_value:
                        journal_info["publication_date"] = date_value
                    pub_year = pub_year or _collect_text(pub_date, "Year")
        if journal_info:
            summary["journal"] = journal_info

        pagination = article_node.find("Pagination")
        if pagination is not None:
            pages = {
                "start": _collect_text(pagination, "StartPage"),
                "end": _collect_text(pagination, "EndPage"),
                "medline": _collect_text(pagination, "MedlinePgn"),
            }
            pages = {k: v for k, v in pages.items() if v}
            if pages:
                summary["pages"] = pages

        abstract_node = article_node.find("Abstract")
        if abstract_node is not None:
            sections: List[Dict[str, Any]] = []
            abstract_texts = abstract_node.findall("AbstractText")
            for section in abstract_texts[:MAX_ABSTRACT_SECTIONS]:
                text_value = _collect_rich_text(section)
                if not text_value:
                    continue
                section_summary = {
                    "label": section.get("Label") or section.get("NlmCategory"),
                    "text": _trim_text(text_value, limit=TEXT_TRUNCATE * 2),
                }
                section_summary = {k: v for k, v in section_summary.items() if v}
                if section_summary:
                    sections.append(section_summary)
            if sections:
                if len(abstract_texts) > MAX_ABSTRACT_SECTIONS:
                    sections.append({"note": f"{len(abstract_texts) - MAX_ABSTRACT_SECTIONS} additional abstract sections truncated"})
                summary["abstract"] = sections

        languages = _collect_all(article_node, "Language")
        if languages:
            summary["languages"] = languages[:MAX_LIST_ITEMS]
            contributions["languages"].extend(summary["languages"])

        publication_types: List[str] = []
        pub_type_nodes = article_node.findall("PublicationTypeList/PublicationType")
        for pub_type in pub_type_nodes[:MAX_PUBLICATION_TYPES]:
            type_text = _collect_rich_text(pub_type)
            if type_text:
                publication_types.append(type_text)
        if publication_types:
            if len(pub_type_nodes) > MAX_PUBLICATION_TYPES:
                publication_types.append(f"…({len(pub_type_nodes) - MAX_PUBLICATION_TYPES} more)")
            summary["publication_types"] = publication_types
            contributions["publication_types"].extend(publication_types[:MAX_PUBLICATION_TYPES])

        authors = _summarize_author_list(article_node.find("AuthorList"))
        if authors:
            summary["authors"] = authors

        grant_list = _summarize_grant_list(article_node.find("GrantList"))
        if grant_list:
            summary["grants"] = grant_list

    if pub_year is None:
        pub_year = _extract_pub_year(article)
    if pub_year:
        summary["year"] = pub_year

    journal_contribution = journal_title or (summary.get("journal", {}) or {}).get("title")
    if journal_contribution:
        contributions["journal"] = journal_contribution
    if pub_year:
        contributions["year"] = pub_year

    mesh_terms: List[str] = []
    mesh_heading_list = medline.find("MeshHeadingList")
    if mesh_heading_list is not None:
        headings = mesh_heading_list.findall("MeshHeading")
        for heading in headings[:MAX_MESH_TERMS]:
            descriptor_node = heading.find("DescriptorName")
            descriptor = _collect_rich_text(descriptor_node)
            if not descriptor:
                continue
            descriptor_clean = descriptor
            if descriptor_node is not None and descriptor_node.get("MajorTopicYN") == "Y":
                descriptor_display = f"{descriptor}*"
            else:
                descriptor_display = descriptor
            qualifiers: List[str] = []
            for qualifier in heading.findall("QualifierName")[:2]:
                qual_text = _collect_rich_text(qualifier)
                if qual_text:
                    if qualifier.get("MajorTopicYN") == "Y":
                        qual_text = f"{qual_text}*"
                    qualifiers.append(qual_text)
            term = descriptor_display
            if qualifiers:
                term = f"{descriptor_display} ({', '.join(qualifiers)})"
            mesh_terms.append(term)
            contributions["mesh_descriptors"].append(descriptor_clean)
        if mesh_terms:
            if len(headings) > MAX_MESH_TERMS:
                mesh_terms.append(f"…({len(headings) - MAX_MESH_TERMS} more)")
            summary["mesh_terms"] = mesh_terms

    keyword_lists = medline.findall("KeywordList")
    if keyword_lists:
        keywords: List[str] = []
        total_keywords = 0
        for kw_list in keyword_lists:
            keyword_nodes = kw_list.findall("Keyword")
            total_keywords += len(keyword_nodes)
            for keyword in keyword_nodes:
                if len(keywords) >= MAX_KEYWORDS:
                    break
                keyword_text = _collect_rich_text(keyword)
                if keyword_text:
                    keywords.append(keyword_text)
            if len(keywords) >= MAX_KEYWORDS:
                break
        if keywords:
            if total_keywords > len(keywords):
                keywords.append(f"…({total_keywords - len(keywords)} more)")
            summary["keywords"] = keywords

    chemical_list = medline.find("ChemicalList")
    if chemical_list is not None:
        chemicals = []
        chemical_nodes = chemical_list.findall("Chemical")
        for chem in chemical_nodes[:MAX_CHEMICALS]:
            name = _collect_rich_text(chem.find("NameOfSubstance"))
            if name:
                chemicals.append(name)
        if chemicals:
            if len(chemical_nodes) > MAX_CHEMICALS:
                chemicals.append(f"…({len(chemical_nodes) - MAX_CHEMICALS} more)")
            summary["chemicals"] = chemicals

    coi_statement = _collect_rich_text(medline.find("CoiStatement"))
    if coi_statement:
        summary["conflict_of_interest"] = _trim_text(coi_statement, limit=TEXT_TRUNCATE * 2)

    pubmed_data = article.find("PubmedData")
    if pubmed_data is not None:
        article_ids = pubmed_data.find("ArticleIdList")
        if article_ids is not None:
            identifiers: Dict[str, Any] = {}
            id_nodes = article_ids.findall("ArticleId")
            for article_id in id_nodes[:MAX_ARTICLE_IDS]:
                id_type = article_id.get("IdType")
                value = _collect_rich_text(article_id)
                if id_type and value and id_type not in identifiers:
                    identifiers[id_type] = value
            if identifiers:
                if len(id_nodes) > MAX_ARTICLE_IDS:
                    identifiers["note"] = f"{len(id_nodes) - MAX_ARTICLE_IDS} additional ids truncated"
                summary["identifiers"] = identifiers

        publication_status = _collect_text(pubmed_data, "PublicationStatus")
        if publication_status:
            summary["publication_status"] = publication_status

        history = pubmed_data.find("History")
        if history is not None:
            events: List[Dict[str, Any]] = []
            event_nodes = history.findall("PubMedPubDate")
            for event in event_nodes[:MAX_LIST_ITEMS]:
                status_value = event.get("PubStatus")
                date_value = _format_date([
                    _collect_text(event, "Year"),
                    _collect_text(event, "Month"),
                    _collect_text(event, "Day"),
                ])
                hour = _collect_text(event, "Hour")
                minute = _collect_text(event, "Minute")
                time_part = None
                if hour or minute:
                    hour_fmt = hour.zfill(2) if hour and hour.isdigit() else hour
                    minute_fmt = minute.zfill(2) if minute and minute.isdigit() else minute
                    time_components = [comp for comp in (hour_fmt, minute_fmt) if comp]
                    if time_components:
                        time_part = ":".join(time_components)
                if time_part:
                    date_value = f"{date_value} {time_part}" if date_value else time_part
                entry = {k: v for k, v in {"status": status_value, "date": date_value}.items() if v}
                if entry:
                    events.append(entry)
            if events:
                if len(event_nodes) > MAX_LIST_ITEMS:
                    events.append({"note": f"{len(event_nodes) - MAX_LIST_ITEMS} additional history events truncated"})
                summary["history"] = events

    summary = {k: v for k, v in summary.items() if v not in (None, [], {}, "")}
    return summary, contributions


def _summarize_pubmed_article_set(root: ET.Element) -> Dict[str, Any]:
    articles = root.findall("PubmedArticle")

    journal_counter: Counter[str] = Counter()
    year_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    mesh_counter: Counter[str] = Counter()
    language_counter: Counter[str] = Counter()

    summaries: List[Dict[str, Any]] = []
    for article in articles[:MAX_PUBMED_ARTICLES]:
        article_summary, contribution = _summarize_pubmed_article(article)
        if article_summary:
            summaries.append(article_summary)
        journal = contribution.get("journal")
        if journal:
            journal_counter[journal] += 1
        year = contribution.get("year")
        if year:
            year_counter[year] += 1
        for pub_type in contribution.get("publication_types", []):
            if "…(" in pub_type:
                continue
            type_counter[pub_type] += 1
        for mesh in contribution.get("mesh_descriptors", []):
            mesh_counter[mesh] += 1
        for language in contribution.get("languages", []):
            language_counter[language] += 1

    if len(articles) > MAX_PUBMED_ARTICLES:
        summaries.append({"note": f"{len(articles) - MAX_PUBMED_ARTICLES} additional articles truncated"})

    result: Dict[str, Any] = {
        "record_count": len(articles),
        "records": summaries,
    }

    counts: Dict[str, Any] = {"total_articles": len(articles)}
    if journal_counter:
        counts["unique_journals"] = len(journal_counter)
    if type_counter:
        counts["unique_article_types"] = len(type_counter)
    if mesh_counter:
        counts["unique_mesh_descriptors"] = len(mesh_counter)
    if language_counter:
        counts["unique_languages"] = len(language_counter)
    if year_counter:
        counts["years_covered"] = len(year_counter)
    if counts:
        result["counts"] = counts

    if journal_counter:
        result["top_journals"] = [
            {"journal": journal, "count": count}
            for journal, count in journal_counter.most_common(5)
        ]
    if year_counter:
        result["top_years"] = [
            {"year": year, "count": count}
            for year, count in year_counter.most_common(5)
        ]
    if type_counter:
        result["top_article_types"] = [
            {"type": pub_type, "count": count}
            for pub_type, count in type_counter.most_common(5)
        ]
    if mesh_counter:
        result["top_mesh_descriptors"] = [
            {"descriptor": descriptor, "count": count}
            for descriptor, count in mesh_counter.most_common(5)
        ]
    if language_counter:
        result["top_languages"] = [
            {"language": language, "count": count}
            for language, count in language_counter.most_common(5)
        ]

    return result


def _build_affiliation_map(article_meta: Optional[ET.Element]) -> Dict[str, str]:
    aff_map: Dict[str, str] = {}
    if article_meta is None:
        return aff_map

    for aff in article_meta.findall("aff"):
        aff_id = aff.get("id") or f"aff_{len(aff_map) + 1}"
        text = _collect_rich_text(aff)
        if text:
            aff_map[aff_id] = _trim_text(text, limit=TEXT_TRUNCATE * 2)
    return aff_map


def _summarize_pmc_contributors(contrib_group: Optional[ET.Element], aff_map: Dict[str, str]) -> Tuple[List[Dict[str, Any]], int, int]:
    if contrib_group is None:
        return [], 0, 0

    contributors: List[ET.Element] = contrib_group.findall("contrib")
    summaries: List[Dict[str, Any]] = []
    corresponding_count = 0

    for contrib in contributors[:MAX_PMC_CONTRIBUTORS]:
        summary: Dict[str, Any] = {}
        name_node = contrib.find("name")
        if name_node is not None:
            surname = _collect_rich_text(name_node.find("surname"))
            given = _collect_rich_text(name_node.find("given-names"))
            initials = _collect_rich_text(name_node.find("initials"))
            if surname or given:
                name_parts = [part for part in (given, surname) if part]
                summary["name"] = " ".join(name_parts)
            elif initials:
                summary["name"] = initials
        elif contrib.find("string-name") is not None:
            summary["name"] = _collect_rich_text(contrib.find("string-name"))

        role = contrib.get("contrib-type")
        if role:
            summary["role"] = role

        orcid = _collect_rich_text(contrib.find("contrib-id[@contrib-id-type='orcid']"))
        if orcid:
            summary["orcid"] = orcid.replace("https://orcid.org/", "ORCID:")

        email = _collect_rich_text(contrib.find("email"))
        if email:
            summary["email"] = email

        if contrib.get("corresp") == "yes":
            summary["corresponding"] = True
            corresponding_count += 1

        aff_refs: List[str] = []
        for xref in contrib.findall("xref"):
            if xref.get("ref-type") == "aff":
                rid = xref.get("rid")
                if rid:
                    aff_refs.append(rid)
        if aff_refs:
            aff_names: List[str] = []
            for rid in aff_refs:
                text = aff_map.get(rid)
                if text:
                    aff_names.append(text)
                if len(aff_names) >= 2:
                    break
            if aff_names:
                summary["affiliations"] = aff_names

        if summary:
            summaries.append(summary)

    return summaries, len(contributors), corresponding_count


def _summarize_pmc_funding(article_meta: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if article_meta is None:
        return None

    funding_entries: List[Dict[str, Any]] = []
    for funding_group in article_meta.findall("funding-group"):
        for award_group in funding_group.findall("award-group"):
            entry: Dict[str, Any] = {
                "funder": _collect_rich_text(award_group.find("funding-source")),
                "award": _collect_rich_text(award_group.find("award-id")),
            }
            entry = {k: v for k, v in entry.items() if v}
            if entry:
                funding_entries.append(entry)

    if not funding_entries:
        return None

    if len(funding_entries) > MAX_PMC_FUNDERS:
        truncated = funding_entries[:MAX_PMC_FUNDERS]
        truncated.append({"note": f"{len(funding_entries) - MAX_PMC_FUNDERS} additional funders truncated"})
        funding_entries = truncated

    return funding_entries


def _summarize_pmc_history(article_meta: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if article_meta is None:
        return None

    history = article_meta.find("history")
    if history is None:
        return None

    events: List[Dict[str, Any]] = []
    dates = history.findall("date")
    for date_node in dates[:MAX_LIST_ITEMS]:
        event_type = date_node.get("date-type")
        date_value = _format_date([
            _collect_text(date_node, "year"),
            _collect_text(date_node, "month"),
            _collect_text(date_node, "day"),
        ])
        event = {k: v for k, v in {"event": event_type, "date": date_value}.items() if v}
        if event:
            events.append(event)

    if not events:
        return None

    if len(dates) > MAX_LIST_ITEMS:
        events.append({"note": f"{len(dates) - MAX_LIST_ITEMS} additional history entries truncated"})

    return events


def _summarize_pmc_article(article: ET.Element) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    summary: Dict[str, Any] = {}
    contributions: Dict[str, Any] = {
        "keywords": [],
    }

    front = article.find("front")
    if front is None:
        return summary, contributions

    journal_meta = front.find("journal-meta")
    if journal_meta is not None:
        journal_info: Dict[str, Any] = {}
        journal_title = _collect_first_text(journal_meta.find("journal-title-group"), "journal-title")
        iso_abbrev = _collect_text(journal_meta, "journal-id[@journal-id-type='iso-abbrev']")
        if journal_title:
            journal_info["title"] = journal_title
            contributions["journal"] = journal_title
        elif iso_abbrev:
            contributions["journal"] = iso_abbrev
        if iso_abbrev and iso_abbrev != journal_title:
            journal_info["iso"] = iso_abbrev
        publisher = _collect_first_text(journal_meta.find("publisher"), "publisher-name")
        if publisher:
            journal_info["publisher"] = publisher
        issn_ppub = _collect_text(journal_meta, "issn[@pub-type='ppub']")
        issn_epub = _collect_text(journal_meta, "issn[@pub-type='epub']")
        if issn_ppub:
            journal_info["issn_print"] = issn_ppub
        if issn_epub:
            journal_info["issn_electronic"] = issn_epub
        if journal_info:
            summary["journal"] = journal_info

    article_meta = front.find("article-meta")
    if article_meta is None:
        return summary, contributions

    article_type = article.get("article-type")
    if article_type:
        summary["article_type"] = article_type
        contributions["article_type"] = article_type

    language = article.get("{http://www.w3.org/XML/1998/namespace}lang")
    if language:
        summary["language"] = language
        contributions["language"] = language

    identifiers: Dict[str, Any] = {}
    for article_id in article_meta.findall("article-id"):
        id_type = article_id.get("pub-id-type") or article_id.get("id-type")
        value = _collect_rich_text(article_id)
        if id_type and value and id_type not in identifiers:
            identifiers[id_type] = value
    if identifiers:
        summary["identifiers"] = identifiers

    title = _collect_first_text(article_meta.find("title-group"), "article-title")
    if title:
        summary["title"] = _trim_text(title, limit=TEXT_TRUNCATE * 2)

    article_categories = article_meta.find("article-categories")
    if article_categories is not None:
        subjects = [
            _collect_rich_text(subject)
            for subject in article_categories.findall("subj-group/subject")
            if _collect_rich_text(subject)
        ]
        if subjects:
            summary["subjects"] = subjects[:MAX_LIST_ITEMS]

    aff_map = _build_affiliation_map(article_meta)
    if aff_map:
        aff_items = list(aff_map.items())
        aff_summary = [{"id": aff_id, "text": text} for aff_id, text in aff_items[:MAX_PMC_AFFILIATIONS]]
        if len(aff_items) > MAX_PMC_AFFILIATIONS:
            aff_summary.append({"note": f"{len(aff_items) - MAX_PMC_AFFILIATIONS} additional affiliations truncated"})
        summary["affiliations"] = aff_summary

    contributors, total_contributors, corresponding_count = _summarize_pmc_contributors(
        article_meta.find("contrib-group"), aff_map
    )
    if contributors:
        summary["contributors"] = contributors

    keywords: List[str] = []
    for kwd_group in article_meta.findall("kwd-group"):
        for kwd in kwd_group.findall("kwd"):
            if len(keywords) >= MAX_KEYWORDS:
                break
            keyword_text = _collect_rich_text(kwd)
            if keyword_text:
                keywords.append(keyword_text)
        if len(keywords) >= MAX_KEYWORDS:
            break
    if keywords:
        summary["keywords"] = keywords
        contributions["keywords"].extend(keywords)

    abstract_node = article_meta.find("abstract")
    if abstract_node is not None:
        abstract_paragraphs: List[str] = []
        paragraphs = abstract_node.findall("p")
        for paragraph in paragraphs:
            text = _collect_rich_text(paragraph)
            if text:
                abstract_paragraphs.append(_trim_text(text, limit=TEXT_TRUNCATE * 2))
            if len(abstract_paragraphs) >= MAX_PMC_ABSTRACT_PARAGRAPHS:
                break
        if abstract_paragraphs:
            if len(paragraphs) > MAX_PMC_ABSTRACT_PARAGRAPHS:
                abstract_paragraphs.append(
                    f"…({len(paragraphs) - MAX_PMC_ABSTRACT_PARAGRAPHS} additional abstract paragraphs truncated)"
                )
            summary["abstract"] = abstract_paragraphs

    pub_date = _extract_pub_date(article_meta)
    if pub_date:
        summary["publication_date"] = pub_date
        contributions["year"] = pub_date[:4]

    history_summary = _summarize_pmc_history(article_meta)
    if history_summary:
        summary["history"] = history_summary

    funding_summary = _summarize_pmc_funding(article_meta)
    if funding_summary:
        summary["funding"] = funding_summary

    license_info: Dict[str, Any] = {}
    permissions = article_meta.find("permissions")
    if permissions is not None:
        license_node = permissions.find("license")
        if license_node is not None:
            license_text = _collect_rich_text(license_node.find("license-p"))
            if license_text:
                license_info["text"] = _trim_text(license_text, limit=TEXT_TRUNCATE * 2)
            license_url = None
            for child in license_node.findall(".//{*}license_ref"):
                if child.text and child.text.strip():
                    license_url = child.text.strip()
                    break
            if license_url:
                license_info["url"] = license_url
        copyright_statement = _collect_rich_text(permissions.find("copyright-statement"))
        if copyright_statement:
            license_info["copyright"] = _trim_text(copyright_statement)
    if license_info:
        summary["license"] = license_info

    body = article.find("body")
    if body is not None:
        section_titles: List[str] = []
        for sec in body.findall("sec"):
            title_text = _collect_rich_text(sec.find("title"))
            if title_text:
                section_titles.append(_trim_text(title_text))
            if len(section_titles) >= MAX_PMC_SECTION_TITLES:
                break
        if section_titles:
            summary["section_titles"] = section_titles

    counts: Dict[str, Any] = {}
    if total_contributors:
        counts["contributors"] = total_contributors
    if corresponding_count:
        counts["corresponding_authors"] = corresponding_count
    if aff_map:
        counts["affiliations"] = len(aff_map)
    if body is not None:
        section_total = len(body.findall("sec"))
        if section_total:
            counts["sections"] = section_total
    if counts:
        summary["counts"] = counts

    summary = {k: v for k, v in summary.items() if v not in (None, [], {}, "")}
    return summary, contributions


def _summarize_pmc_article_set(root: ET.Element) -> Dict[str, Any]:
    articles = root.findall("article")

    journal_counter: Counter[str] = Counter()
    year_counter: Counter[str] = Counter()
    keyword_counter: Counter[str] = Counter()
    article_type_counter: Counter[str] = Counter()
    language_counter: Counter[str] = Counter()

    summaries: List[Dict[str, Any]] = []
    for article in articles[:MAX_PMC_ARTICLES]:
        article_summary, contribution = _summarize_pmc_article(article)
        if article_summary:
            summaries.append(article_summary)
        journal = contribution.get("journal")
        if journal:
            journal_counter[journal] += 1
        year = contribution.get("year")
        if year:
            year_counter[year] += 1
        for keyword in contribution.get("keywords", []):
            keyword_counter[keyword] += 1
        article_type = contribution.get("article_type")
        if article_type:
            article_type_counter[article_type] += 1
        language = contribution.get("language")
        if language:
            language_counter[language] += 1

    if len(articles) > MAX_PMC_ARTICLES:
        summaries.append({"note": f"{len(articles) - MAX_PMC_ARTICLES} additional articles truncated"})

    result: Dict[str, Any] = {
        "record_count": len(articles),
        "records": summaries,
    }

    counts: Dict[str, Any] = {"total_articles": len(articles)}
    if journal_counter:
        counts["unique_journals"] = len(journal_counter)
    if year_counter:
        counts["years_covered"] = len(year_counter)
    if keyword_counter:
        counts["unique_keywords"] = len(keyword_counter)
    if article_type_counter:
        counts["unique_article_types"] = len(article_type_counter)
    if language_counter:
        counts["languages"] = len(language_counter)
    if counts:
        result["counts"] = counts

    if journal_counter:
        result["top_journals"] = [
            {"journal": journal, "count": count}
            for journal, count in journal_counter.most_common(5)
        ]
    if year_counter:
        result["top_years"] = [
            {"year": year, "count": count}
            for year, count in year_counter.most_common(5)
        ]
    if keyword_counter:
        result["top_keywords"] = [
            {"keyword": keyword, "count": count}
            for keyword, count in keyword_counter.most_common(5)
        ]
    if article_type_counter:
        result["article_types"] = [
            {"type": article_type, "count": count}
            for article_type, count in article_type_counter.most_common(5)
        ]
    if language_counter:
        result["languages"] = [
            {"language": language, "count": count}
            for language, count in language_counter.most_common(5)
        ]

    return result


def _parse_maf_value(freq: Optional[str]) -> Optional[Dict[str, Any]]:
    if not freq:
        return None
    freq = freq.strip()
    if not freq:
        return None
    if "=" not in freq:
        return {"raw": freq}
    allele, value = freq.split("=", 1)
    allele = allele.strip()
    value = value.strip()
    result: Dict[str, Any] = {}
    if allele:
        result["allele"] = allele
    if value:
        if "/" in value:
            parts = value.split("/", 1)
            freq_value = parts[0].strip()
            sample = parts[1].strip()
            if freq_value:
                try:
                    result["frequency"] = float(freq_value)
                except ValueError:
                    result["frequency"] = freq_value
            if sample:
                try:
                    result["observations"] = int(sample)
                except ValueError:
                    result["observations"] = sample
        else:
            try:
                result["frequency"] = float(value)
            except ValueError:
                result["frequency"] = value
    if not result:
        result["raw"] = freq
    return result


def _summarize_exchange_document(doc: ET.Element) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    summary: Dict[str, Any] = {}
    contributions: Dict[str, List[str]] = {
        "chromosomes": [],
        "genes": [],
        "function_classes": [],
        "validated": [],
    }

    uid = doc.get("uid")
    if uid:
        summary["uid"] = uid

    snp_id = _child_text(doc, "SNP_ID")
    if snp_id:
        summary["snp_id"] = snp_id

    acc = _child_text(doc, "ACC")
    if acc:
        summary["accession"] = acc

    chromosome = _child_text(doc, "CHR")
    if chromosome:
        summary["chromosome"] = chromosome
        contributions["chromosomes"].append(chromosome)

    chrpos = _child_text(doc, "CHRPOS")
    if chrpos:
        summary["position"] = chrpos

    chrpos_prev = _child_text(doc, "CHRPOS_PREV_ASSM")
    if chrpos_prev:
        summary["previous_position"] = chrpos_prev

    spdi = _child_text(doc, "SPDI")
    if spdi:
        summary["spdi"] = spdi

    allele = _child_text(doc, "ALLELE")
    if allele:
        summary["allele"] = allele

    snp_class = _child_text(doc, "SNP_CLASS")
    if snp_class:
        summary["class"] = snp_class

    function_classes = _child_text(doc, "FXN_CLASS")
    if function_classes:
        classes = [cls.strip() for cls in function_classes.split(",") if cls.strip()]
        if classes:
            summary["function_classes"] = classes[:MAX_SNP_FUNCTION_CLASSES]
            contributions["function_classes"].extend(classes[:MAX_SNP_FUNCTION_CLASSES])

    validated = _child_text(doc, "VALIDATED")
    if validated:
        summary["validated"] = validated
        contributions["validated"].append(validated)

    docsum = _child_text(doc, "DOCSUM")
    if docsum:
        summary["docsum"] = _trim_text(docsum, limit=TEXT_TRUNCATE * 2)

    created = _child_text(doc, "CREATEDATE")
    if created:
        summary["created"] = created

    updated = _child_text(doc, "UPDATEDATE")
    if updated:
        summary["updated"] = updated

    origin = _child_text(doc, "ALLELE_ORIGIN")
    if origin:
        summary["allele_origin"] = origin

    sample_size = _child_text(doc, "GLOBAL_SAMPLESIZE")
    if sample_size:
        summary["global_sample_size"] = sample_size

    population = _child_text(doc, "GLOBAL_POPULATION")
    if population:
        summary["global_population"] = population

    mafs_node = None
    for child in doc:
        if _local_tag(child) == "GLOBAL_MAFS":
            mafs_node = child
            break
    if mafs_node is not None:
        mafs: List[Dict[str, Any]] = []
        for maf in _iter_children(mafs_node, "MAF")[:MAX_SNP_MAFS]:
            entry: Dict[str, Any] = {}
            study = _child_text(maf, "STUDY")
            if study:
                entry["study"] = study
            freq_value = _child_text(maf, "FREQ")
            parsed = _parse_maf_value(freq_value)
            if parsed:
                entry.update(parsed)
            elif freq_value:
                entry["raw"] = freq_value
            if entry:
                mafs.append(entry)
        if mafs:
            summary["global_mafs"] = mafs

    genes_node = None
    for child in doc:
        if _local_tag(child) == "GENES":
            genes_node = child
            break
    if genes_node is not None:
        gene_entries: List[Dict[str, Any]] = []
        for gene in _iter_children(genes_node, "GENE_E")[:MAX_SNP_GENES]:
            gene_summary: Dict[str, Any] = {}
            name = _child_text(gene, "NAME")
            gene_id = _child_text(gene, "GENE_ID")
            if name:
                gene_summary["name"] = name
                contributions["genes"].append(name)
            if gene_id:
                gene_summary["gene_id"] = gene_id
            if gene_summary:
                gene_entries.append(gene_summary)
        if gene_entries:
            summary["genes"] = gene_entries

    history_fields = {}
    for key in ("HANDLE", "ORIG_BUILD", "UPD_BUILD", "TAX_ID"):
        value = _child_text(doc, key)
        if value:
            history_fields[key.lower()] = value
    if history_fields:
        summary["metadata"] = history_fields

    return {k: v for k, v in summary.items() if v not in (None, [], {}, "")}, contributions


def _summarize_exchange_set(root: ET.Element) -> Dict[str, Any]:
    documents = _iter_children(root, "DocumentSummary")

    chromosome_counter: Counter[str] = Counter()
    gene_counter: Counter[str] = Counter()
    function_counter: Counter[str] = Counter()
    validated_counter: Counter[str] = Counter()

    summaries: List[Dict[str, Any]] = []
    for doc in documents[:MAX_EXCHANGE_DOCS]:
        doc_summary, contribution = _summarize_exchange_document(doc)
        if doc_summary:
            summaries.append(doc_summary)
        for chrom in contribution.get("chromosomes", []):
            chromosome_counter[chrom] += 1
        for gene_name in contribution.get("genes", []):
            gene_counter[gene_name] += 1
        for fxn in contribution.get("function_classes", []):
            function_counter[fxn] += 1
        for flag in contribution.get("validated", []):
            validated_counter[flag] += 1

    if len(documents) > MAX_EXCHANGE_DOCS:
        summaries.append({"note": f"{len(documents) - MAX_EXCHANGE_DOCS} additional records truncated"})

    result: Dict[str, Any] = {
        "record_count": len(documents),
        "records": summaries,
    }

    counts: Dict[str, Any] = {"total_snps": len(documents)}
    if chromosome_counter:
        counts["unique_chromosomes"] = len(chromosome_counter)
    if gene_counter:
        counts["unique_genes"] = len(gene_counter)
    if function_counter:
        counts["unique_function_classes"] = len(function_counter)
    if validated_counter:
        counts["validated_flags"] = len(validated_counter)
    if counts:
        result["counts"] = counts

    if chromosome_counter:
        result["top_chromosomes"] = [
            {"chromosome": chrom, "count": count}
            for chrom, count in chromosome_counter.most_common(5)
        ]
    if gene_counter:
        result["top_genes"] = [
            {"gene": gene, "count": count}
            for gene, count in gene_counter.most_common(5)
        ]
    if function_counter:
        result["function_classes"] = [
            {"class": fxn, "count": count}
            for fxn, count in function_counter.most_common(5)
        ]
    if validated_counter:
        result["validated_flags"] = [
            {"flag": flag, "count": count}
            for flag, count in validated_counter.most_common(5)
        ]

    return result


def _summarize_sample_attributes(attrs_node: Optional[ET.Element], limit: int = MAX_SRA_SAMPLE_ATTRIBUTES) -> Optional[List[Dict[str, Any]]]:
    if attrs_node is None:
        return None
    attributes: List[Dict[str, Any]] = []
    for attribute in _iter_children(attrs_node, "SAMPLE_ATTRIBUTE")[:limit]:
        tag = _child_text(attribute, "TAG")
        value = _child_text(attribute, "VALUE")
        unit = _child_text(attribute, "UNITS")
        attr_summary = {k: v for k, v in {"tag": tag, "value": value, "units": unit}.items() if v}
        if attr_summary:
            attributes.append(attr_summary)
    if not attributes:
        return None
    if len(_iter_children(attrs_node, "SAMPLE_ATTRIBUTE")) > limit:
        attributes.append({"note": f"{len(_iter_children(attrs_node, 'SAMPLE_ATTRIBUTE')) - limit} additional attributes truncated"})
    return attributes


def _summarize_run_files(files_node: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if files_node is None:
        return None
    files: List[Dict[str, Any]] = []
    sra_files = _iter_children(files_node, "SRAFile")
    for sra_file in sra_files[:MAX_SRA_FILES]:
        file_summary: Dict[str, Any] = {}
        for key in ("filename", "semantic_name", "supertype", "cluster"):
            value = sra_file.get(key)
            if value:
                file_summary[key] = value
        size = sra_file.get("size")
        if size:
            file_summary["size"] = size
        date = sra_file.get("date")
        if date:
            file_summary["date"] = date
        url = sra_file.get("url")
        if url:
            file_summary["url"] = url
        if file_summary:
            files.append(file_summary)
    if not files:
        return None
    if len(sra_files) > MAX_SRA_FILES:
        files.append({"note": f"{len(sra_files) - MAX_SRA_FILES} additional files truncated"})
    return files


def _summarize_cloud_files(cloud_node: Optional[ET.Element]) -> Optional[List[Dict[str, Any]]]:
    if cloud_node is None:
        return None
    cloud_files = _iter_children(cloud_node, "CloudFile")
    summaries: List[Dict[str, Any]] = []
    for cloud in cloud_files[:MAX_SRA_CLOUD_FILES]:
        summary = {
            "filetype": cloud.get("filetype"),
            "provider": cloud.get("provider"),
            "location": cloud.get("location"),
        }
        summary = {k: v for k, v in summary.items() if v}
        if summary:
            summaries.append(summary)
    if not summaries:
        return None
    if len(cloud_files) > MAX_SRA_CLOUD_FILES:
        summaries.append({"note": f"{len(cloud_files) - MAX_SRA_CLOUD_FILES} additional cloud entries truncated"})
    return summaries


def _summarize_pool(pool_node: Optional[ET.Element]) -> Optional[Dict[str, Any]]:
    if pool_node is None:
        return None
    members = _iter_children(pool_node, "Member")
    summaries: List[Dict[str, Any]] = []
    for member in members[:MAX_SRA_POOL_MEMBERS]:
        summary = {
            "accession": member.get("accession"),
            "sample_name": member.get("sample_name"),
            "spots": member.get("spots"),
            "bases": member.get("bases"),
        }
        organism = member.get("organism")
        if organism:
            summary["organism"] = organism
        summary = {k: v for k, v in summary.items() if v}
        if summary:
            summaries.append(summary)
    if not summaries:
        return None
    pool_summary: Dict[str, Any] = {"members": summaries}
    if len(members) > MAX_SRA_POOL_MEMBERS:
        pool_summary["note"] = f"{len(members) - MAX_SRA_POOL_MEMBERS} additional pool members truncated"
    return pool_summary


def _summarize_run_set(run_set: Optional[ET.Element]) -> Tuple[Optional[List[Dict[str, Any]]], int]:
    if run_set is None:
        return None, 0
    runs = _iter_children(run_set, "RUN")
    summaries: List[Dict[str, Any]] = []
    total_runs = 0
    for run in runs[:MAX_SRA_RUNS]:
        run_summary: Dict[str, Any] = {
            "accession": run.get("accession"),
            "alias": run.get("alias"),
            "spots": run.get("total_spots"),
            "bases": run.get("total_bases"),
            "size": run.get("size"),
            "published": run.get("published"),
        }
        experiment_ref = _find_child(run, "EXPERIMENT_REF")
        if experiment_ref is not None:
            run_summary["experiment_ref"] = experiment_ref.get("accession")
        statistics = _find_child(run, "Statistics")
        if statistics is not None:
            stats_summary = {
                "nreads": statistics.get("nreads"),
                "nspots": statistics.get("nspots"),
            }
            stats_summary = {k: v for k, v in stats_summary.items() if v}
            if stats_summary:
                run_summary["statistics"] = stats_summary
        bases_node = _find_child(run, "Bases")
        if bases_node is not None:
            base_entries = []
            for base in bases_node.findall("Base")[:4]:
                value = base.get("value")
                count = base.get("count")
                if value and count:
                    base_entries.append({"base": value, "count": count})
            if base_entries:
                run_summary["base_counts"] = base_entries
        files_node = _find_child(run, "SRAFiles")
        files_summary = _summarize_run_files(files_node)
        if files_summary:
            run_summary["files"] = files_summary
        cloud_node = _find_child(run, "CloudFiles")
        cloud_summary = _summarize_cloud_files(cloud_node)
        if cloud_summary:
            run_summary["cloud"] = cloud_summary
        run_summary = {k: v for k, v in run_summary.items() if v not in (None, [], {}, "")}
        if run_summary:
            summaries.append(run_summary)
            total_runs += 1
    if not summaries:
        return None, 0
    if len(runs) > MAX_SRA_RUNS:
        summaries.append({"note": f"{len(runs) - MAX_SRA_RUNS} additional runs truncated"})
    return summaries, total_runs


def _summarize_experiment_package(pkg: ET.Element) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    summary: Dict[str, Any] = {}
    contributions: Dict[str, Any] = {
        "species": [],
        "library_strategies": [],
        "platforms": [],
        "runs": 0,
    }

    experiment = _find_child(pkg, "EXPERIMENT")
    if experiment is not None:
        experiment_summary: Dict[str, Any] = {
            "accession": experiment.get("accession"),
            "alias": experiment.get("alias"),
        }
        title = _child_text(experiment, "TITLE")
        if title:
            experiment_summary["title"] = _trim_text(title, limit=TEXT_TRUNCATE * 2)

        design = _find_child(experiment, "DESIGN")
        if design is not None:
            design_summary: Dict[str, Any] = {}
            description = _child_text(design, "DESIGN_DESCRIPTION")
            if description:
                design_summary["description"] = _trim_text(description, limit=TEXT_TRUNCATE * 2)
            sample_descriptor = _find_child(design, "SAMPLE_DESCRIPTOR")
            if sample_descriptor is not None:
                descriptor_summary = {
                    "accession": sample_descriptor.get("accession"),
                    "alias": sample_descriptor.get("alias"),
                }
                descriptor_summary = {k: v for k, v in descriptor_summary.items() if v}
                if descriptor_summary:
                    design_summary["sample_descriptor"] = descriptor_summary
            library_descriptor = _find_child(design, "LIBRARY_DESCRIPTOR")
            if library_descriptor is not None:
                library_summary: Dict[str, Any] = {}
                for key, field in (
                    ("name", "LIBRARY_NAME"),
                    ("strategy", "LIBRARY_STRATEGY"),
                    ("source", "LIBRARY_SOURCE"),
                    ("selection", "LIBRARY_SELECTION"),
                ):
                    value = _child_text(library_descriptor, field)
                    if value:
                        library_summary[key] = value
                        if field == "LIBRARY_STRATEGY":
                            contributions["library_strategies"].append(value)
                layout = _find_child(library_descriptor, "LIBRARY_LAYOUT")
                if layout is not None:
                    for child in layout:
                        layout_type = _local_tag(child)
                        if layout_type:
                            library_summary["layout"] = layout_type
                            break
                if library_summary:
                    design_summary["library"] = library_summary
            if design_summary:
                experiment_summary["design"] = design_summary

        platform = _find_child(experiment, "PLATFORM")
        if platform is not None:
            platform_summary: Dict[str, Any] = {}
            for platform_child in platform:
                platform_type = _local_tag(platform_child)
                instrument = _child_text(platform_child, "INSTRUMENT_MODEL") or _child_text(platform_child, "INSTRUMENT")
                if platform_type:
                    platform_summary["type"] = platform_type
                    contributions["platforms"].append(platform_type)
                if instrument:
                    platform_summary["instrument_model"] = instrument
                break
            if platform_summary:
                experiment_summary["platform"] = platform_summary

        experiment_summary = {k: v for k, v in experiment_summary.items() if v not in (None, [], {}, "")}
        if experiment_summary:
            summary["experiment"] = experiment_summary

    submission = _find_child(pkg, "SUBMISSION")
    if submission is not None:
        submission_summary = {
            "accession": submission.get("accession"),
            "alias": submission.get("alias"),
            "center": submission.get("center_name"),
            "lab": submission.get("lab_name"),
        }
        submission_summary = {k: v for k, v in submission_summary.items() if v}
        if submission_summary:
            summary["submission"] = submission_summary

    organization = _find_child(pkg, "Organization")
    if organization is not None:
        org_summary: Dict[str, Any] = {
            "name": _child_text(organization, "Name"),
            "type": organization.get("type"),
        }
        address = _find_child(organization, "Address")
        if address is not None:
            address_summary = {
                "city": _child_text(address, "City"),
                "country": _child_text(address, "Country"),
            }
            postal = address.get("postal_code")
            if postal:
                address_summary["postal_code"] = postal
            address_summary = {k: v for k, v in address_summary.items() if v}
            if address_summary:
                org_summary["address"] = address_summary
        if org_summary:
            summary["organization"] = org_summary

    study = _find_child(pkg, "STUDY")
    if study is not None:
        study_summary: Dict[str, Any] = {
            "accession": study.get("accession"),
            "alias": study.get("alias"),
            "center": study.get("center_name"),
        }
        descriptor = _find_child(study, "DESCRIPTOR")
        if descriptor is not None:
            title = _child_text(descriptor, "STUDY_TITLE")
            if title:
                study_summary["title"] = _trim_text(title, limit=TEXT_TRUNCATE * 2)
            sabstract = _child_text(descriptor, "STUDY_ABSTRACT")
            if sabstract:
                study_summary["abstract"] = _trim_text(sabstract, limit=TEXT_TRUNCATE * 2)
        study_summary = {k: v for k, v in study_summary.items() if v}
        if study_summary:
            summary["study"] = study_summary

    sample = _find_child(pkg, "SAMPLE")
    if sample is not None:
        sample_summary: Dict[str, Any] = {
            "accession": sample.get("accession"),
            "alias": sample.get("alias"),
            "title": _child_text(sample, "TITLE"),
        }
        identifiers = _find_child(sample, "IDENTIFIERS")
        if identifiers is not None:
            primary_id = _child_text(identifiers, "PRIMARY_ID")
            if primary_id:
                sample_summary["primary_id"] = primary_id
            external_id = _find_child(identifiers, "EXTERNAL_ID")
            if external_id is not None:
                sample_summary["external_id"] = {
                    "namespace": external_id.get("namespace"),
                    "value": external_id.text.strip() if external_id.text else None,
                }
        sample_name = _find_child(sample, "SAMPLE_NAME")
        if sample_name is not None:
            taxon_id = _child_text(sample_name, "TAXON_ID")
            scientific_name = _child_text(sample_name, "SCIENTIFIC_NAME")
            sample_summary["taxon"] = {k: v for k, v in {
                "taxon_id": taxon_id,
                "scientific_name": scientific_name,
            }.items() if v}
            if scientific_name or taxon_id:
                label = scientific_name or "Unknown"
                if taxon_id:
                    label = f"{label} ({taxon_id})"
                contributions["species"].append(label)
        attrs = _summarize_sample_attributes(_find_child(sample, "SAMPLE_ATTRIBUTES"))
        if attrs:
            sample_summary["attributes"] = attrs
        sample_summary = {k: v for k, v in sample_summary.items() if v not in (None, [], {}, "")}
        if sample_summary:
            summary["sample"] = sample_summary

    pool_summary = _summarize_pool(_find_child(pkg, "Pool"))
    if pool_summary:
        summary["pool"] = pool_summary

    run_summaries, run_count = _summarize_run_set(_find_child(pkg, "RUN_SET"))
    if run_summaries:
        summary["runs"] = run_summaries
    contributions["runs"] = run_count

    summary = {k: v for k, v in summary.items() if v not in (None, [], {}, "")}
    return summary, contributions


def _summarize_experiment_package_set(root: ET.Element) -> Dict[str, Any]:
    packages = _iter_children(root, "EXPERIMENT_PACKAGE")

    species_counter: Counter[str] = Counter()
    library_counter: Counter[str] = Counter()
    platform_counter: Counter[str] = Counter()
    total_runs = 0

    summaries: List[Dict[str, Any]] = []
    for package in packages[:MAX_SRA_PACKAGES]:
        package_summary, contribution = _summarize_experiment_package(package)
        if package_summary:
            summaries.append(package_summary)
        for species in contribution.get("species", []):
            species_counter[species] += 1
        for strategy in contribution.get("library_strategies", []):
            library_counter[strategy] += 1
        for platform in contribution.get("platforms", []):
            platform_counter[platform] += 1
        total_runs += contribution.get("runs", 0)

    if len(packages) > MAX_SRA_PACKAGES:
        summaries.append({"note": f"{len(packages) - MAX_SRA_PACKAGES} additional experiment packages truncated"})

    result: Dict[str, Any] = {
        "record_count": len(packages),
        "records": summaries,
    }

    counts: Dict[str, Any] = {"total_packages": len(packages)}
    if total_runs:
        counts["total_runs"] = total_runs
    if species_counter:
        counts["unique_species"] = len(species_counter)
    if library_counter:
        counts["unique_library_strategies"] = len(library_counter)
    if platform_counter:
        counts["unique_platforms"] = len(platform_counter)
    if counts:
        result["counts"] = counts

    if species_counter:
        result["top_species"] = [
            {"species": species, "count": count}
            for species, count in species_counter.most_common(5)
        ]
    if library_counter:
        result["top_library_strategies"] = [
            {"strategy": strategy, "count": count}
            for strategy, count in library_counter.most_common(5)
        ]
    if platform_counter:
        result["platforms"] = [
            {"platform": platform, "count": count}
            for platform, count in platform_counter.most_common(5)
        ]

    return result


def _summarize_taxon(taxon: ET.Element) -> Tuple[Dict[str, Any], Dict[str, List[str]]]:
    summary: Dict[str, Any] = {}
    contributions: Dict[str, List[str]] = {
        "divisions": [],
        "ranks": [],
        "genetic_codes": [],
    }

    tax_id = _child_text(taxon, "TaxId")
    if tax_id:
        summary["tax_id"] = tax_id

    scientific_name = _child_text(taxon, "ScientificName")
    if scientific_name:
        summary["scientific_name"] = scientific_name

    common_other = _find_child(taxon, "OtherNames")
    if common_other is not None:
        other_summary: Dict[str, Any] = {}
        genbank_common = _collect_child_texts(common_other, "GenbankCommonName", 1)
        if genbank_common:
            other_summary["genbank_common_name"] = genbank_common[0]
        synonyms = _collect_child_texts(common_other, "Synonym", MAX_TAXON_SYNONYMS)
        if synonyms:
            other_summary["synonyms"] = synonyms
        commons = _collect_child_texts(common_other, "CommonName", MAX_TAXON_COMMON_NAMES)
        if commons:
            other_summary["common_names"] = commons
        includes = _collect_child_texts(common_other, "Includes", MAX_TAXON_INCLUDES)
        if includes:
            other_summary["includes"] = includes
        name_entries = []
        for name_node in _iter_children(common_other, "Name"):
            entry = {
                "class": _child_text(name_node, "ClassCDE"),
                "name": _child_text(name_node, "DispName"),
            }
            entry = {k: v for k, v in entry.items() if v}
            if entry:
                name_entries.append(entry)
        if name_entries:
            other_summary["named_entries"] = name_entries[:MAX_TAXON_AUTHORITY_NAMES]
            if len(name_entries) > MAX_TAXON_AUTHORITY_NAMES:
                other_summary.setdefault("notes", []).append(
                    f"{len(name_entries) - MAX_TAXON_AUTHORITY_NAMES} additional name entries truncated"
                )
        if other_summary:
            summary["other_names"] = other_summary

    parent = _child_text(taxon, "ParentTaxId")
    if parent:
        summary["parent_tax_id"] = parent

    rank = _child_text(taxon, "Rank")
    if rank:
        summary["rank"] = rank
        contributions["ranks"].append(rank)

    division = _child_text(taxon, "Division")
    if division:
        summary["division"] = division
        contributions["divisions"].append(division)

    genetic_code_node = _find_child(taxon, "GeneticCode")
    if genetic_code_node is not None:
        gc_summary = {
            "id": _child_text(genetic_code_node, "GCId"),
            "name": _child_text(genetic_code_node, "GCName"),
        }
        gc_summary = {k: v for k, v in gc_summary.items() if v}
        if gc_summary:
            summary["genetic_code"] = gc_summary
            if gc_summary.get("name"):
                contributions["genetic_codes"].append(gc_summary["name"])

    mito_code_node = _find_child(taxon, "MitoGeneticCode")
    if mito_code_node is not None:
        mgc_summary = {
            "id": _child_text(mito_code_node, "MGCId"),
            "name": _child_text(mito_code_node, "MGCName"),
        }
        mgc_summary = {k: v for k, v in mgc_summary.items() if v}
        if mgc_summary:
            summary["mitochondrial_code"] = mgc_summary

    lineage = _child_text(taxon, "Lineage")
    if lineage:
        summary["lineage"] = _trim_text(lineage, limit=TEXT_TRUNCATE * 2)

    lineage_ex = _find_child(taxon, "LineageEx")
    if lineage_ex is not None:
        lineage_entries: List[Dict[str, Any]] = []
        for lineage_taxon in _iter_children(lineage_ex, "Taxon")[:MAX_TAXON_LINEAGE]:
            entry = {
                "tax_id": _child_text(lineage_taxon, "TaxId"),
                "name": _child_text(lineage_taxon, "ScientificName"),
                "rank": _child_text(lineage_taxon, "Rank"),
            }
            entry = {k: v for k, v in entry.items() if v}
            if entry:
                lineage_entries.append(entry)
        if lineage_entries:
            summary["lineage_list"] = lineage_entries
            if len(_iter_children(lineage_ex, "Taxon")) > MAX_TAXON_LINEAGE:
                summary.setdefault("notes", []).append(
                    f"lineage truncated after {MAX_TAXON_LINEAGE} entries"
                )

    for date_field in ("CreateDate", "UpdateDate", "PubDate"):
        value = _child_text(taxon, date_field)
        if value:
            summary[date_field.lower()] = value

    summary = {k: v for k, v in summary.items() if v not in (None, [], {}, "")}
    return summary, contributions


def _summarize_taxa_set(root: ET.Element) -> Dict[str, Any]:
    taxa = _iter_children(root, "Taxon")

    division_counter: Counter[str] = Counter()
    rank_counter: Counter[str] = Counter()
    genetic_counter: Counter[str] = Counter()

    summaries: List[Dict[str, Any]] = []
    for taxon in taxa[:MAX_TAXA]:
        tax_summary, contribution = _summarize_taxon(taxon)
        if tax_summary:
            summaries.append(tax_summary)
        for division in contribution.get("divisions", []):
            division_counter[division] += 1
        for rank in contribution.get("ranks", []):
            rank_counter[rank] += 1
        for code in contribution.get("genetic_codes", []):
            genetic_counter[code] += 1

    if len(taxa) > MAX_TAXA:
        summaries.append({"note": f"{len(taxa) - MAX_TAXA} additional taxa truncated"})

    result: Dict[str, Any] = {
        "record_count": len(taxa),
        "records": summaries,
    }

    counts: Dict[str, Any] = {"total_taxa": len(taxa)}
    if division_counter:
        counts["unique_divisions"] = len(division_counter)
    if rank_counter:
        counts["unique_ranks"] = len(rank_counter)
    if genetic_counter:
        counts["unique_genetic_codes"] = len(genetic_counter)
    if counts:
        result["counts"] = counts

    if division_counter:
        result["top_divisions"] = [
            {"division": division, "count": count}
            for division, count in division_counter.most_common(5)
        ]
    if rank_counter:
        result["top_ranks"] = [
            {"rank": rank, "count": count}
            for rank, count in rank_counter.most_common(5)
        ]
    if genetic_counter:
        result["top_genetic_codes"] = [
            {"code": code, "count": count}
            for code, count in genetic_counter.most_common(5)
        ]

    return result


def _summarize_tseq(tseq: ET.Element) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    seqtype = tseq.find("TSeq_seqtype")
    if seqtype is not None and seqtype.get("value"):
        summary["type"] = seqtype.get("value")
    for tag, key in (
        ("TSeq_accver", "accession"),
        ("TSeq_taxid", "tax_id"),
        ("TSeq_orgname", "organism"),
        ("TSeq_defline", "definition"),
        ("TSeq_length", "length"),
    ):
        value = _collect_text(tseq, tag)
        if value:
            summary[key] = value if tag != "TSeq_defline" else _trim_text(value)
    sequence = _collect_text(tseq, "TSeq_sequence")
    if sequence:
        preview = sequence[:SEQUENCE_PREVIEW] + ("…" if len(sequence) > SEQUENCE_PREVIEW else "")
        summary["sequence_preview"] = preview
    return summary


def _summarize_tseq_set(root: ET.Element) -> Dict[str, Any]:
    entries = root.findall("TSeq")
    summaries: List[Dict[str, Any]] = []
    for tseq in entries[:MAX_TSEQ]:
        summaries.append(_summarize_tseq(tseq))
    if len(entries) > MAX_TSEQ:
        summaries.append({"note": f"{len(entries) - MAX_TSEQ} additional sequences truncated"})
    return {
        "record_count": len(entries),
        "records": summaries,
    }


def postprocess_efetch(response: Any) -> Any:
    """Postprocess NCBI EFetch responses.

    If the response is a GBSet XML string, parse and summarize it. Otherwise, return
    the response unchanged (e.g., raw FASTA or plain text outputs).
    """

    if not isinstance(response, str):
        return response

    root = _parse_if_xml(response)
    if root is None:
        return response

    root_tag = _local_tag(root)

    if root_tag == "GBSet":
        seq_summaries: List[Dict[str, Any]] = []
        for gbseq in root.findall("GBSeq"):
            seq_summary = _summarize_gbseq(gbseq)
            if seq_summary:
                seq_summaries.append(seq_summary)

        return {
            "record_count": len(seq_summaries),
            "records": seq_summaries,
        }

    if root_tag == "RecordSet":
        return _summarize_recordset(root)

    if root_tag == "BioSampleSet":
        return _summarize_biosample_set(root)

    if root_tag == "IdList":
        return _summarize_id_list(root)

    if root_tag == "Entrezgene-Set":
        return _summarize_entrezgene_set(root)

    if root_tag == "NLMCatalogRecordSet":
        return _summarize_nlm_catalog(root)

    if root_tag == "PubmedArticleSet":
        return _summarize_pubmed_article_set(root)

    if root_tag == "pmc-articleset":
        return _summarize_pmc_article_set(root)

    if root_tag == "ExchangeSet":
        return _summarize_exchange_set(root)

    if root_tag == "EXPERIMENT_PACKAGE_SET":
        return _summarize_experiment_package_set(root)

    if root_tag == "TaxaSet":
        return _summarize_taxa_set(root)

    if root_tag == "TSeqSet":
        return _summarize_tseq_set(root)

    return response

