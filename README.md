# ORCID–TAXID Evidence Explorer

The ORCID–TAXID Evidence Explorer is a small biosecurity decision-support project for DNA synthesis screening. It maps a researcher's ORCID identifier to NCBI Taxonomy identifiers (TAXIDs) associated with organisms in their public scientific record.

The MVP searches ORCID-linked PubMed publications, follows relevant NCBI nucleotide-record links, identifies associated organisms, and presents the resulting evidence with citations. It also provides a simple question interface that returns deterministic, source-backed answers without using a generative language model.

The tool is designed to support qualified human reviewers. It does not approve or reject orders, assign trust scores, or determine whether a researcher has legitimate intent.

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

## Responsible-use note

Publication history does not prove identity, authorization, laboratory experience, biosafety approval, benign intent, or legitimate end use. ORCID and PubMed coverage are incomplete, and a missing relationship must not be interpreted as proof that a researcher lacks relevant experience. The system should therefore be treated as one evidence source within a broader screening process.
