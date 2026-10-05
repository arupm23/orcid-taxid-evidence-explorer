import os
import tempfile
import unittest

from app import create_app
from app.embeddings import HashEmbeddingProvider, cosine_similarity
from app.models import Publication, Taxon
from app.ncbi import (
    parse_elink_taxids,
    parse_esearch,
    parse_pubmed,
    parse_sequence_taxids,
    parse_taxonomy_summaries,
)
from app.orcid import normalize_orcid


class FakeNcbiClient:
    def find_pmids_by_orcid(self, orcid, limit=25):
        return ["12345678"]

    def fetch_publications(self, pmids):
        return [
            Publication(
                pmid="12345678",
                title="A study of Vaccinia virus",
                abstract="Experimental vaccine research.",
                year=2024,
                publication_type="research",
            )
        ]

    def linked_taxids(self, pmid):
        return [10245]

    def fetch_taxa(self, taxids):
        return [Taxon(10245, "Vaccinia virus", "species")]


class OrcidTests(unittest.TestCase):
    def test_normalizes_valid_orcid(self):
        self.assertEqual(normalize_orcid("https://orcid.org/0000-0002-1825-0097"), "0000-0002-1825-0097")

    def test_rejects_invalid_checksum(self):
        with self.assertRaises(ValueError):
            normalize_orcid("0000-0002-1825-0098")


class RetrievalTests(unittest.TestCase):
    def test_hash_embeddings_rank_related_text_higher(self):
        provider = HashEmbeddingProvider()
        query, related, unrelated = provider.embed(
            ["vaccinia vaccine study", "experimental vaccinia vaccine", "bacterial plasmid"]
        )
        self.assertGreater(
            cosine_similarity(query, related), cosine_similarity(query, unrelated)
        )

class ParserTests(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(
            parse_esearch("<eSearchResult><IdList><Id>7</Id><Id>8</Id></IdList></eSearchResult>"),
            ["7", "8"],
        )
        publications = parse_pubmed(
            """<PubmedArticleSet><PubmedArticle><MedlineCitation>
            <PMID>7</PMID><Article><ArticleTitle>Example <i>study</i></ArticleTitle>
            <Abstract><AbstractText>Useful abstract.</AbstractText></Abstract>
            <Journal><JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue></Journal>
            <PublicationTypeList><PublicationType>Journal Article</PublicationType></PublicationTypeList>
            </Article></MedlineCitation></PubmedArticle></PubmedArticleSet>"""
        )
        self.assertEqual(publications[0].title, "Example study")
        self.assertEqual(publications[0].year, 2023)
        self.assertEqual(
            parse_elink_taxids(
                "<eLinkResult><LinkSet><LinkSetDb><DbTo>taxonomy</DbTo><Link><Id>10245</Id></Link></LinkSetDb></LinkSet></eLinkResult>"
            ),
            [10245],
        )
        self.assertEqual(
            parse_sequence_taxids(
                """<eSummaryResult><DocSum><Id>1</Id>
                <Item Name="TaxId" Type="Integer">10245</Item></DocSum>
                <DocSum><Id>2</Id><Item Name="TaxId" Type="Integer">10245</Item></DocSum>
                </eSummaryResult>"""
            ),
            [10245],
        )
        taxa = parse_taxonomy_summaries(
            """<eSummaryResult><DocSum><Id>10245</Id>
            <Item Name="ScientificName" Type="String">Vaccinia virus</Item>
            <Item Name="Rank" Type="String">species</Item></DocSum></eSummaryResult>"""
        )
        self.assertEqual(taxa[0].scientific_name, "Vaccinia virus")


class ApiTests(unittest.TestCase):
    def setUp(self):
        handle, self.database_path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": self.database_path,
                "NCBI_CLIENT": FakeNcbiClient(),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        os.unlink(self.database_path)

    def test_end_to_end_ingest_report_and_chat(self):
        response = self.client.post(
            "/api/researchers/ingest", json={"orcid": "0000-0002-1825-0097"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["evidence_records"], 1)

        report = self.client.get(
            "/api/researchers/0000-0002-1825-0097/report?taxid=10245"
        )
        self.assertEqual(report.status_code, 200)
        self.assertEqual(report.json["organisms"][0]["scientific_name"], "Vaccinia virus")
        self.assertIsNone(report.json["decision"])

        chat = self.client.post(
            "/api/chat",
            json={
                "orcid": "0000-0002-1825-0097",
                "question": "Is there evidence for TAXID 10245?",
            },
        )
        self.assertEqual(chat.status_code, 200)
        self.assertIn("Vaccinia virus", chat.json["answer"])
        self.assertEqual(len(chat.json["sources"]), 1)
        self.assertEqual(chat.json["response_mode"], "deterministic_template")
        self.assertEqual(chat.json["evidence_status"], "supported")
        self.assertIn("12345678", chat.json["retrieved_pmids"])


if __name__ == "__main__":
    unittest.main()
