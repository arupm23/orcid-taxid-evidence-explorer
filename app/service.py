import re
import hashlib
from collections import defaultdict

from .models import Evidence
from .orcid import normalize_orcid


TAXID_PATTERN = re.compile(r"\btax(?:onomy\s*)?id\s*[:#]?\s*(\d{2,9})\b", re.I)


class EvidenceService:
    def __init__(self, repository, ncbi_client, embedding_provider):
        self.repository = repository
        self.ncbi = ncbi_client
        self.embeddings = embedding_provider

    def ingest(self, raw_orcid, limit=25):
        orcid = normalize_orcid(raw_orcid)
        pmids = self.ncbi.find_pmids_by_orcid(orcid, limit=limit)
        publications = self.ncbi.fetch_publications(pmids)
        self.repository.begin_ingest(orcid)

        taxids_by_pmid = {}
        all_taxids = set()
        for publication in publications:
            self.repository.save_publication(orcid, publication)
            taxids = self.ncbi.linked_taxids(publication.pmid)
            taxids_by_pmid[publication.pmid] = taxids
            all_taxids.update(taxids)

        taxa = {taxon.taxid: taxon for taxon in self.ncbi.fetch_taxa(sorted(all_taxids))}
        for taxon in taxa.values():
            self.repository.save_taxon(taxon)

        self.index_publications(orcid)

        publication_lookup = {publication.pmid: publication for publication in publications}
        evidence_count = 0
        for pmid, taxids in taxids_by_pmid.items():
            publication = publication_lookup[pmid]
            for taxid in taxids:
                if taxid not in taxa:
                    continue
                confidence = 0.9 if publication.publication_type == "research" else 0.65
                explanation = (
                    "NCBI links this PubMed record to one or more nucleotide records "
                    "assigned to taxonomy record {}. "
                    "The publication is classified as {}; this is evidence of a literature "
                    "relationship, not proof of authorization or hands-on work."
                ).format(taxid, publication.publication_type)
                self.repository.save_evidence(
                    Evidence(
                        orcid=orcid,
                        pmid=pmid,
                        taxid=taxid,
                        evidence_type="ncbi_linked_nucleotide_taxid",
                        confidence=confidence,
                        explanation=explanation,
                    )
                )
                evidence_count += 1

        return {
            "orcid": orcid,
            "status": "complete",
            "publications_found": len(publications),
            "taxa_found": len(taxa),
            "evidence_records": evidence_count,
            "embedding_model": self.embeddings.model_id,
            "limitations": [
                "Only public PubMed records that contain the ORCID are searched.",
                "NCBI links favor precision and may miss organisms mentioned only in text.",
                "A publication relationship is not proof of hands-on experience or authorization.",
            ],
        }

    def index_publications(self, raw_orcid):
        orcid = normalize_orcid(raw_orcid)
        publications = self.repository.publications_for_orcid(orcid)
        if not publications:
            return {"orcid": orcid, "indexed": 0, "model": self.embeddings.model_id}
        texts = [_publication_text(item) for item in publications]
        vectors = self.embeddings.embed(texts)
        for publication, text, vector in zip(publications, texts, vectors):
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            self.repository.save_embedding(
                publication["pmid"], self.embeddings.model_id, content_hash, vector
            )
        return {
            "orcid": orcid,
            "indexed": len(publications),
            "model": self.embeddings.model_id,
        }

    def retrieve(self, raw_orcid, question, limit=5):
        orcid = normalize_orcid(raw_orcid)
        taxid_match = TAXID_PATTERN.search(question or "")
        taxid = int(taxid_match.group(1)) if taxid_match else None
        vector = self.embeddings.embed([question])[0]
        vector_matches = self.repository.vector_search(
            orcid, self.embeddings.model_id, vector, limit=limit
        )
        if not vector_matches and self.repository.publications_for_orcid(orcid):
            self.index_publications(orcid)
            vector_matches = self.repository.vector_search(
                orcid, self.embeddings.model_id, vector, limit=limit
            )
        lexical_matches = self.repository.search_publications(orcid, question, limit=limit)
        combined = {}
        if taxid is not None or _is_list_question(question):
            for row in self.repository.report(orcid, taxid=taxid):
                if row["pmid"] not in combined:
                    combined[row["pmid"]] = {
                        key: row[key]
                        for key in (
                            "pmid",
                            "title",
                            "abstract",
                            "year",
                            "publication_type",
                            "source_url",
                        )
                    }
                    combined[row["pmid"]]["retrieval"] = ["structured"]
                    combined[row["pmid"]]["retrieval_score"] = 5.0
        if _requires_primary_research(question):
            vector_matches = [
                item for item in vector_matches if item["publication_type"] != "review"
            ]
            lexical_matches = [
                item for item in lexical_matches if item["publication_type"] != "review"
            ]
        for rank, item in enumerate(vector_matches):
            if item["pmid"] in combined:
                combined[item["pmid"]]["retrieval"].append("vector")
                combined[item["pmid"]]["retrieval_score"] += item["vector_score"]
            else:
                copy = dict(item)
                copy["retrieval"] = ["vector"]
                copy["retrieval_score"] = item["vector_score"]
                combined[item["pmid"]] = copy
        for rank, item in enumerate(lexical_matches):
            if item["pmid"] in combined:
                combined[item["pmid"]]["retrieval"].append("lexical")
                combined[item["pmid"]]["retrieval_score"] += 1.0 / (rank + 1)
            else:
                copy = dict(item)
                copy["retrieval"] = ["lexical"]
                copy["retrieval_score"] = 1.0 / (rank + 1)
                combined[item["pmid"]] = copy
        results = sorted(
            combined.values(), key=lambda item: item["retrieval_score"], reverse=True
        )[:limit]
        evidence = self.repository.evidence_for_pmids(
            orcid, [item["pmid"] for item in results]
        )
        for item in results:
            item["organism_evidence"] = evidence.get(item["pmid"], [])
            item["abstract"] = (item.get("abstract") or "")[:1800]
        return results

    def report(self, raw_orcid, taxid=None):
        orcid = normalize_orcid(raw_orcid)
        rows = self.repository.report(orcid, taxid=taxid)
        grouped = defaultdict(list)
        for row in rows:
            grouped[(row["taxid"], row["scientific_name"], row["rank"])].append(row)
        organisms = []
        for (organism_taxid, name, rank), evidence_rows in grouped.items():
            organisms.append(
                {
                    "taxid": organism_taxid,
                    "scientific_name": name,
                    "rank": rank,
                    "maximum_confidence": max(row["confidence"] for row in evidence_rows),
                    "evidence": [
                        {
                            key: row[key]
                            for key in (
                                "pmid",
                                "title",
                                "year",
                                "publication_type",
                                "source_url",
                                "evidence_type",
                                "directness",
                                "confidence",
                                "explanation",
                            )
                        }
                        for row in evidence_rows
                    ],
                }
            )
        organisms.sort(key=lambda item: (-item["maximum_confidence"], item["scientific_name"]))
        return {
            "orcid": orcid,
            "stats": self.repository.stats(orcid),
            "organisms": organisms,
            "decision": None,
            "notice": "Decision support only. A human reviewer must verify identity, affiliation, intended use, and institutional authorization.",
        }

    def chat(self, raw_orcid, question):
        orcid = normalize_orcid(raw_orcid)
        question = (question or "").strip()
        if not question:
            raise ValueError("Enter a question")

        taxid_match = TAXID_PATTERN.search(question)
        taxid = int(taxid_match.group(1)) if taxid_match else None
        report = self.report(orcid, taxid=taxid)
        sources = []
        retrieval_contexts = self.retrieve(orcid, question, limit=5)

        organisms = report["organisms"]
        if taxid is None and organisms and not _is_list_question(question):
            named_matches = [
                organism
                for organism in organisms
                if _organism_name_matches(organism["scientific_name"], question)
            ]
            organisms = named_matches

        if organisms:
            lines = []
            for organism in organisms[:8]:
                evidence = organism["evidence"]
                lines.append(
                    "{} (TAXID {}) has {} linked evidence record{}; highest confidence {:.0%}.".format(
                        organism["scientific_name"],
                        organism["taxid"],
                        len(evidence),
                        "s" if len(evidence) != 1 else "",
                        organism["maximum_confidence"],
                    )
                )
                for item in evidence[:3]:
                    sources.append(
                        {
                            "label": "PMID {} — {}".format(item["pmid"], item["title"]),
                            "url": item["source_url"],
                        }
                    )
            answer = " ".join(lines)
        elif taxid is not None:
            answer = (
                "No stored NCBI-linked evidence was found between this ORCID and TAXID {}. "
                "This is an absence-of-evidence result, not evidence that the researcher lacks experience."
            ).format(taxid)
        else:
            matches = [
                item for item in retrieval_contexts if "lexical" in item["retrieval"]
            ]
            if matches:
                answer = (
                    "I found {} publication{} matching the question, but no canonical TAXID "
                    "relationship was established by the stored evidence."
                ).format(len(matches), "s" if len(matches) != 1 else "")
                sources = [
                    {"label": "PMID {} — {}".format(item["pmid"], item["title"]), "url": item["source_url"]}
                    for item in matches
                ]
            else:
                answer = (
                    "No matching evidence was found in the ingested public records. "
                    "Try asking with a TAXID, or ingest the ORCID again to refresh its records."
                )
        evidence_status = "supported" if sources else "insufficient_evidence"

        return {
            "orcid": orcid,
            "question": question,
            "answer": answer,
            "sources": _deduplicate_sources(sources),
            "evidence_status": evidence_status,
            "response_mode": "deterministic_template",
            "retrieved_pmids": [item["pmid"] for item in retrieval_contexts],
            "limitations": [],
            "decision": None,
            "notice": "The response summarizes retrieved evidence and must not be used as an automatic approval or rejection.",
        }


def _deduplicate_sources(sources):
    seen = set()
    result = []
    for source in sources:
        if source["url"] not in seen:
            seen.add(source["url"])
            result.append(source)
    return result


def _is_list_question(question):
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "which organism",
            "what organism",
            "list organism",
            "show organism",
            "all organism",
            "which taxa",
            "what taxa",
            "list taxa",
            "show taxa",
        )
    )


def _organism_name_matches(scientific_name, question):
    lowered_question = question.lower()
    if scientific_name.lower() in lowered_question:
        return True
    meaningful_tokens = [
        token.lower() for token in scientific_name.split() if len(token) > 3
    ]
    return bool(meaningful_tokens) and all(
        token in lowered_question for token in meaningful_tokens
    )


def _requires_primary_research(question):
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in ("experiment", "experimental", "hands-on", "laboratory work", "lab work")
    )


def _publication_text(publication):
    return "Title: {}\nPublication type: {}\nAbstract: {}".format(
        publication.get("title", ""),
        publication.get("publication_type", "unknown"),
        publication.get("abstract", ""),
    )
