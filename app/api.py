from flask import Blueprint, current_app, jsonify, request, send_from_directory

from .ncbi import NcbiError


api = Blueprint("api", __name__)


def _service():
    return current_app.extensions["evidence_service"]


@api.get("/")
def index():
    return send_from_directory(current_app.static_folder, "index.html")


@api.get("/api/health")
def health():
    return jsonify({"status": "ok"})


@api.post("/api/researchers/ingest")
def ingest():
    payload = request.get_json(silent=True) or {}
    limit = min(max(int(payload.get("limit", 25)), 1), 100)
    return jsonify(_service().ingest(payload.get("orcid", ""), limit=limit))


@api.get("/api/researchers/<path:orcid>/report")
def report(orcid):
    raw_taxid = request.args.get("taxid")
    taxid = int(raw_taxid) if raw_taxid else None
    return jsonify(_service().report(orcid, taxid=taxid))


@api.post("/api/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    return jsonify(_service().chat(payload.get("orcid", ""), payload.get("question", "")))


@api.post("/api/researchers/<path:orcid>/index")
def index_publications(orcid):
    return jsonify(_service().index_publications(orcid))


@api.app_errorhandler(ValueError)
def invalid_input(error):
    return jsonify({"error": str(error)}), 400


@api.app_errorhandler(NcbiError)
def upstream_error(error):
    return jsonify({"error": str(error), "upstream": "NCBI"}), 502


@api.app_errorhandler(Exception)
def unexpected_error(error):
    current_app.logger.exception("Unhandled error")
    return jsonify({"error": "Unexpected server error"}), 500
