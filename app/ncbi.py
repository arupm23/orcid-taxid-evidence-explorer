import time
import xml.etree.ElementTree as ET

import requests

from .models import Publication, Taxon


class NcbiError(RuntimeError):
    pass


class NcbiClient:
    """Small NCBI E-utilities client with conservative, provenance-first retrieval."""

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, api_key="", tool="orcid-taxid-evidence-mvp", email="", session=None):
        self.api_key = api_key
        self.tool = tool
        self.email = email
        self.session = session or requests.Session()
        self._last_request = 0.0

    def _request(self, endpoint, params):
        # Stay under NCBI's unauthenticated request guidance.
        minimum_interval = 0.11 if self.api_key else 0.34
        elapsed = time.monotonic() - self._last_request
        if elapsed < minimum_interval:
            time.sleep(minimum_interval - elapsed)
        common = {"tool": self.tool}
        if self.email:
            common["email"] = self.email
        if self.api_key:
            common["api_key"] = self.api_key
        common.update(params)
        try:
            response = self.session.get(
                "{}/{}".format(self.BASE_URL, endpoint), params=common, timeout=30
            )
            self._last_request = time.monotonic()
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            raise NcbiError("NCBI request failed: {}".format(exc)) from exc

    def find_pmids_by_orcid(self, orcid, limit=25):
        xml_text = self._request(
            "esearch.fcgi",
            {
                "db": "pubmed",
                "term": '"{}"[auid]'.format(orcid),
                "retmax": str(limit),
                "retmode": "xml",
                "sort": "pub date",
            },
        )
        return parse_esearch(xml_text)

    def fetch_publications(self, pmids):
        if not pmids:
            return []
        xml_text = self._request(
            "efetch.fcgi",
            {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        )
        return parse_pubmed(xml_text)

    def linked_taxids(self, pmid):
        """Return TaxIDs carried by nucleotide records linked to a PubMed record.

        NCBI does not consistently expose a direct PubMed-to-Taxonomy edge. The
        defensible path is PubMed -> Nucleotide -> TaxId. Sequence links are
        capped to keep a single highly connected paper from dominating a run.
        """
        xml_text = self._request(
            "elink.fcgi",
            {
                "dbfrom": "pubmed",
                "db": "nuccore",
                "id": pmid,
                "retmode": "xml",
            },
        )
        sequence_ids = parse_elink_ids(xml_text, expected_database="nuccore")[:100]
        if not sequence_ids:
            return []
        summary_xml = self._request(
            "esummary.fcgi",
            {
                "db": "nuccore",
                "id": ",".join(sequence_ids),
                "retmode": "xml",
            },
        )
        return parse_sequence_taxids(summary_xml)

    def fetch_taxa(self, taxids):
        if not taxids:
            return []
        xml_text = self._request(
            "esummary.fcgi",
            {"db": "taxonomy", "id": ",".join(map(str, taxids)), "retmode": "xml"},
        )
        return parse_taxonomy_summaries(xml_text)


def parse_esearch(xml_text):
    root = ET.fromstring(xml_text)
    return [node.text for node in root.findall("./IdList/Id") if node.text]


def _text(node):
    return "".join(node.itertext()).strip() if node is not None else ""


def parse_pubmed(xml_text):
    root = ET.fromstring(xml_text)
    publications = []
    for article in root.findall(".//PubmedArticle"):
        citation = article.find("./MedlineCitation")
        pmid = _text(citation.find("./PMID"))
        title = _text(citation.find("./Article/ArticleTitle"))
        abstract_parts = [
            _text(node) for node in citation.findall("./Article/Abstract/AbstractText")
        ]
        year_text = _text(citation.find("./Article/Journal/JournalIssue/PubDate/Year"))
        if not year_text:
            medline_date = _text(
                citation.find("./Article/Journal/JournalIssue/PubDate/MedlineDate")
            )
            year_text = medline_date[:4]
        types = [
            _text(node).lower()
            for node in citation.findall("./Article/PublicationTypeList/PublicationType")
        ]
        publication_type = "review" if any("review" in value for value in types) else "research"
        publications.append(
            Publication(
                pmid=pmid,
                title=title or "Untitled publication",
                abstract=" ".join(part for part in abstract_parts if part),
                year=int(year_text) if year_text.isdigit() else None,
                publication_type=publication_type,
            )
        )
    return publications


def parse_elink_ids(xml_text, expected_database=None):
    root = ET.fromstring(xml_text)
    identifiers = []
    for linksetdb in root.findall(".//LinkSetDb"):
        database = _text(linksetdb.find("./DbTo"))
        if expected_database and database and database != expected_database:
            continue
        for identifier in linksetdb.findall("./Link/Id"):
            if identifier.text and identifier.text.isdigit():
                identifiers.append(identifier.text)
    return list(dict.fromkeys(identifiers))


def parse_elink_taxids(xml_text):
    """Backward-compatible helper for direct taxonomy-link fixtures."""
    return sorted(int(value) for value in parse_elink_ids(xml_text, "taxonomy"))


def parse_sequence_taxids(xml_text):
    root = ET.fromstring(xml_text)
    taxids = set()
    for docsum in root.findall(".//DocSum"):
        for item in docsum.findall("./Item"):
            if item.attrib.get("Name") == "TaxId":
                value = _text(item)
                if value.isdigit():
                    taxids.add(int(value))
    return sorted(taxids)


def parse_taxonomy_summaries(xml_text):
    root = ET.fromstring(xml_text)
    taxa = []
    for docsum in root.findall(".//DocSum"):
        taxid_text = _text(docsum.find("./Id"))
        values = {
            item.attrib.get("Name", ""): _text(item) for item in docsum.findall("./Item")
        }
        if taxid_text.isdigit():
            taxa.append(
                Taxon(
                    taxid=int(taxid_text),
                    scientific_name=values.get("ScientificName", "Unknown taxon"),
                    rank=values.get("Rank", ""),
                )
            )
    return taxa
