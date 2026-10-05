# Evaluation labelling guide

`dataset-v1.jsonl` is a small **synthetic smoke-test set**. It validates the evaluation machinery but is not evidence that the system is ready for operational screening.

## Unit of evaluation

Each row represents one question about one already-ingested ORCID record. The gold label contains:

- `evidence_status`: `supported`, `mixed`, or `insufficient_evidence`
- `pmids`: every publication required to answer the question
- `taxids`: every organism identifier required to answer the question
- `provenance`: how the label was established
- `notes`: adjudication rationale

## Labelling rules

1. Label only what the cited source establishes.
2. A linked sequence record establishes a publication–organism relationship, not authorization or hands-on competence.
3. Reviews, perspectives, methods papers, and experimental articles must remain distinguishable.
4. Collaborator-only evidence must not be labelled as direct-author evidence.
5. Use `insufficient_evidence` whenever the available sources cannot answer the question.
6. Never interpret absence of evidence as evidence that a researcher lacks experience.
7. Have two reviewers independently label operational examples; adjudicate disagreements and retain the rationale.

## Recommended real benchmark

Create at least 100 questions across 30–50 consenting or public test profiles, balanced across:

- exact TAXID positives and negatives;
- species names, synonyms, strains, and parent taxa;
- experimental papers versus reviews;
- sparse and incomplete ORCID records;
- lab managers or core-facility personnel;
- organism mentions without linked sequence records;
- direct-author versus collaborator-only relationships;
- questions that must be refused or marked insufficient.

Keep development and held-out test profiles separate. Do not tune prompts or thresholds using the held-out set.

## Metrics

- Retrieval recall@5
- Citation precision
- Evidence-status accuracy
- Unsupported-claim rate
- TAXID exact-match accuracy
- Abstention accuracy on insufficient-evidence cases
- Performance slices by publication type, evidence type, and profile sparsity

