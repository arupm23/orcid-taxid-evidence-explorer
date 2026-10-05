# ORCID–TAXID Evidence Explorer

The ORCID–TAXID Evidence Explorer is a small biosecurity decision-support project for DNA synthesis screening. It maps a researcher's ORCID identifier to NCBI Taxonomy identifiers (TAXIDs) associated with organisms in their public scientific record.

The MVP searches ORCID-linked PubMed publications, follows relevant NCBI nucleotide-record links, identifies associated organisms, and presents the resulting evidence with citations. It also provides a simple question interface that returns deterministic, source-backed answers without using a generative language model.

The tool is designed to support qualified human reviewers. It does not approve or reject orders, assign trust scores, or determine whether a researcher has legitimate intent.

[View the static project overview](https://arupm23.github.io/orcid-taxid-evidence-explorer/) · [Read the detailed desktop guide](RUN_FROM_DESKTOP.md)

## Basic details

- Validates ORCID identifiers, including their checksums.
- Retrieves ORCID-linked publications from PubMed.
- Connects publications to relevant NCBI nucleotide records.
- Maps the retrieved evidence to canonical NCBI TAXIDs.
- Displays organisms, publications, evidence strength, and source links.
- Supports structured, citation-backed questions about a researcher's record.
- Distinguishes “no evidence found” from “evidence of no experience.”
- Uses deterministic response templates rather than a generative LLM.
- Includes automated tests and a starter labelled evaluation dataset.

## Motivation

DNA synthesis providers screen customers and sequence orders to reduce the risk that synthetic nucleic acids are misused. When an order involves an organism or biological function of concern, screening teams may need to determine whether the customer has a credible scientific reason for requesting it.

This investigation can require manually searching researcher profiles, publications, and biological databases. Relevant information is distributed across different systems, making the process slow, inconsistent, and difficult to audit. The resulting friction can also delay legitimate work by vaccine researchers, diagnostic developers, public-health scientists, and other responsible customers.

This project explores whether public scholarly identifiers can make that review process more efficient. Given an ORCID iD, the tool creates a traceable map between a researcher's publications and the organisms linked to those publications through NCBI records.

The purpose is not to infer whether a person is trustworthy. It is to help a reviewer find relevant public evidence faster, understand where each relationship came from, and recognize when the available evidence is incomplete.

## Positive impact

If validated with real screening teams, this project could:

- reduce time spent on repetitive literature and database searches;
- provide citations for researcher–organism relationships;
- make screening investigations more consistent and auditable;
- reduce avoidable delays for legitimate scientific work;
- help reviewers focus on genuinely unexplained or concerning requests;
- complement existing customer and sequence-screening systems; and
- improve biosecurity without relying on an opaque automated trust score.

The intended impact is better-informed human review. The tool is deliberately designed to communicate uncertainty and preserve human responsibility for fulfillment decisions.

## Getting started

### Prerequisites

Before running the project, make sure you have:

- Python 3.9 or newer;
- Git;
- an internet connection for ORCID and NCBI data; and
- a valid email address for NCBI API requests.

### 1. Download the project

Open Terminal and run:

```bash
cd ~/Desktop
git clone https://github.com/arupm23/orcid-taxid-evidence-explorer.git
cd orcid-taxid-evidence-explorer
```

If you have already downloaded the project, update it instead:

```bash
cd ~/Desktop/orcid-taxid-evidence-explorer
git pull
```

### 2. Create the Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Configure NCBI access

Create your local configuration file:

```bash
cp .env.example .env
open -e .env
```

In `.env`, replace the example NCBI email address with your own. An NCBI API key is optional, but it can provide a higher request limit.

Load the configuration into the current Terminal session:

```bash
set -a
source .env
set +a
```

### 4. Start the application

```bash
python run.py
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser. Keep the Terminal window open while using the application. Press `Control+C` in Terminal to stop it.

### 5. Use the evidence explorer

1. Enter a valid ORCID iD.
2. Start the evidence retrieval process.
3. Review the organisms, TAXIDs, publications, evidence strength, and source links.
4. Use the question box for deterministic, citation-backed summaries of the retrieved record.

## Run the automated tests

With the virtual environment active, run:

```bash
python -m pytest
```

For more desktop commands and troubleshooting, see [RUN_FROM_DESKTOP.md](RUN_FROM_DESKTOP.md).

## Responsible-use note

Publication history does not prove identity, authorization, laboratory experience, biosafety approval, benign intent, or legitimate end use. ORCID and PubMed coverage are incomplete, and a missing relationship must not be interpreted as proof that a researcher lacks relevant experience. The system should therefore be treated as one evidence source within a broader screening process.
