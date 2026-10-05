from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Publication:
    pmid: str
    title: str
    abstract: str = ""
    year: Optional[int] = None
    publication_type: str = "unknown"

    @property
    def source_url(self):
        return "https://pubmed.ncbi.nlm.nih.gov/{}/".format(self.pmid)

    def to_dict(self):
        result = asdict(self)
        result["source_url"] = self.source_url
        return result


@dataclass
class Taxon:
    taxid: int
    scientific_name: str
    rank: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Evidence:
    orcid: str
    pmid: str
    taxid: int
    evidence_type: str
    confidence: float
    explanation: str
    directness: str = "direct_author"

    def to_dict(self):
        return asdict(self)

