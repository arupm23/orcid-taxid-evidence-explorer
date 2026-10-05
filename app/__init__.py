import os
from pathlib import Path

from flask import Flask

from .api import api
from .embeddings import create_embedding_provider
from .ncbi import NcbiClient
from .repository import Repository
from .service import EvidenceService


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parent.parent
    database_path = os.getenv("DATABASE_PATH") or str(
        project_root / "instance" / "evidence.db"
    )
    app = Flask(
        __name__,
        static_folder=str(project_root / "web"),
        static_url_path="",
        instance_path=str(project_root / "instance"),
    )
    app.config.from_mapping(
        DATABASE_PATH=database_path,
        NCBI_API_KEY=os.getenv("NCBI_API_KEY", ""),
        NCBI_TOOL=os.getenv("NCBI_TOOL", "orcid-taxid-evidence-mvp"),
        NCBI_EMAIL=os.getenv("NCBI_EMAIL", ""),
        MAX_PUBLICATIONS=25,
        EMBEDDING_PROVIDER=os.getenv("EMBEDDING_PROVIDER", "local"),
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_EMBEDDING_MODEL=os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    repository = Repository(app.config["DATABASE_PATH"])
    repository.initialize()
    client = app.config.get("NCBI_CLIENT") or NcbiClient(
        api_key=app.config["NCBI_API_KEY"],
        tool=app.config["NCBI_TOOL"],
        email=app.config["NCBI_EMAIL"],
    )
    embedding_provider = app.config.get("EMBEDDING_CLIENT") or create_embedding_provider(
        app.config
    )
    app.extensions["evidence_service"] = EvidenceService(
        repository, client, embedding_provider
    )
    app.register_blueprint(api)
    return app
