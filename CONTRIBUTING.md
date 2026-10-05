# Contributing

Thank you for helping improve the ORCID–TAXID Evidence Explorer.

## Priorities

The most useful contributions improve:

- evidence provenance and citation correctness;
- evaluation design and representative datasets;
- explicit uncertainty and abstention behavior;
- accessibility and reviewer usability;
- privacy and responsible deployment; or
- integration with public scholarly and biological databases.

Please do not add automated approval decisions, unsupported researcher-risk scores, or features that imply publication history establishes benign intent.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Copy `.env.example` to `.env` before making live NCBI requests. Never commit `.env`, API keys, private customer data, or unpublished sequence information.

## Pull requests

Keep changes focused, add or update tests, and explain how the change affects evidence quality or reviewer behavior. Changes to confidence rules or evidence interpretation should include labelled evaluation cases and a discussion of likely failure modes.
