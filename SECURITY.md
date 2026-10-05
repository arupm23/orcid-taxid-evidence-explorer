# Security and responsible disclosure

## Intended use

This project is an experimental evidence-retrieval tool for qualified human reviewers. It is not a customer identity service, a pathogen-risk classifier, or an automated order-approval system.

Do not use a public deployment to process private customer records, unpublished nucleotide sequences, order details, access credentials, controlled information, or other sensitive data.

## Reporting a vulnerability

Please open a GitHub issue only when the report contains no exploit details or sensitive information. For a vulnerability that could expose data or enable abuse, contact the repository owner privately through the contact method listed on their GitHub profile. Include:

- the affected component;
- steps to reproduce the issue;
- the likely impact;
- any suggested mitigation; and
- whether the details have been shared elsewhere.

Please allow reasonable time for investigation before public disclosure.

## Deployment guidance

Before operational deployment, add authentication, authorization, rate limiting, audit logging, dependency scanning, transport security, data-retention rules, backups, and organizational review. Confirm that all data sources and downstream uses comply with applicable policies and law.
