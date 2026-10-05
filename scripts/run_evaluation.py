import json
import os
import re
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.embeddings import HashEmbeddingProvider  # noqa: E402
from app.models import Evidence, Publication, Taxon  # noqa: E402
from app.repository import Repository  # noqa: E402
from app.service import EvidenceService  # noqa: E402


class UnusedNcbiClient:
    pass


def load_jsonl(path):
    with open(path, "r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def seed_fixture(repository, fixture):
    orcid = fixture["researcher"]["orcid"]
    repository.begin_ingest(orcid)
    for item in fixture["publications"]:
        repository.save_publication(orcid, Publication(**item))
    for item in fixture["taxa"]:
        repository.save_taxon(Taxon(**item))
    for item in fixture["evidence"]:
        repository.save_evidence(Evidence(orcid=orcid, **item))
    return orcid


def cited_pmids(chat_result):
    values = []
    for source in chat_result["sources"]:
        match = re.search(r"PMID\s+(\d+)", source["label"])
        if match:
            values.append(match.group(1))
    return set(values)


def evaluate(dataset_path, fixture_path):
    dataset = load_jsonl(dataset_path)
    with open(fixture_path, "r", encoding="utf-8") as handle:
        fixture = json.load(handle)
    descriptor, database_path = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    try:
        repository = Repository(database_path)
        repository.initialize()
        orcid = seed_fixture(repository, fixture)
        service = EvidenceService(
            repository, UnusedNcbiClient(), HashEmbeddingProvider()
        )
        service.index_publications(orcid)

        rows = []
        for case in dataset:
            result = service.chat(case["orcid"], case["question"])
            gold_pmids = set(case["gold"]["pmids"])
            ranked = [
                item["pmid"]
                for item in service.retrieve(case["orcid"], case["question"], limit=3)
            ]
            retrieved = set(ranked)
            cited = cited_pmids(result)
            retrieval_hit = not gold_pmids or gold_pmids.issubset(retrieved)
            first_gold_rank = next(
                (index + 1 for index, pmid in enumerate(ranked) if pmid in gold_pmids),
                None,
            )
            reciprocal_rank = (
                1.0 if not gold_pmids else (1.0 / first_gold_rank if first_gold_rank else 0.0)
            )
            top_one_correct = (
                1.0 if not gold_pmids else float(bool(ranked) and ranked[0] in gold_pmids)
            )
            citation_precision = 1.0 if not cited else len(cited & gold_pmids) / len(cited)
            status_correct = result["evidence_status"] == case["gold"]["evidence_status"]
            rows.append(
                {
                    "id": case["id"],
                    "retrieval_recall_at_3": float(retrieval_hit),
                    "citation_precision": citation_precision,
                    "evidence_status_correct": float(status_correct),
                    "reciprocal_rank": reciprocal_rank,
                    "top_one_correct": top_one_correct,
                    "retrieved_pmids_at_3": ranked,
                    "cited_pmids": sorted(cited),
                }
            )
        metrics = {
            "dataset": Path(dataset_path).name,
            "cases": len(rows),
            "retrieval_recall_at_3": sum(row["retrieval_recall_at_3"] for row in rows) / len(rows),
            "citation_precision": sum(row["citation_precision"] for row in rows) / len(rows),
            "evidence_status_accuracy": sum(row["evidence_status_correct"] for row in rows) / len(rows),
            "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in rows) / len(rows),
            "top_one_accuracy": sum(row["top_one_correct"] for row in rows) / len(rows),
            "rows": rows,
        }
        return metrics
    finally:
        os.unlink(database_path)


if __name__ == "__main__":
    results = evaluate(
        PROJECT_ROOT / "evals" / "dataset-v1.jsonl",
        PROJECT_ROOT / "evals" / "fixture-record.json",
    )
    print(json.dumps(results, indent=2))
