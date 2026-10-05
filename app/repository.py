import re
import sqlite3
from contextlib import contextmanager

from .embeddings import cosine_similarity, decode_vector, encode_vector


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS researchers (
    orcid TEXT PRIMARY KEY,
    retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS publications (
    pmid TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT NOT NULL DEFAULT '',
    year INTEGER,
    publication_type TEXT NOT NULL DEFAULT 'unknown',
    source_url TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS researcher_publications (
    orcid TEXT NOT NULL REFERENCES researchers(orcid) ON DELETE CASCADE,
    pmid TEXT NOT NULL REFERENCES publications(pmid) ON DELETE CASCADE,
    PRIMARY KEY (orcid, pmid)
);

CREATE TABLE IF NOT EXISTS taxa (
    taxid INTEGER PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    rank TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcid TEXT NOT NULL REFERENCES researchers(orcid) ON DELETE CASCADE,
    pmid TEXT NOT NULL REFERENCES publications(pmid) ON DELETE CASCADE,
    taxid INTEGER NOT NULL REFERENCES taxa(taxid),
    evidence_type TEXT NOT NULL,
    directness TEXT NOT NULL,
    confidence REAL NOT NULL,
    explanation TEXT NOT NULL,
    retrieved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (orcid, pmid, taxid, evidence_type)
);

CREATE VIRTUAL TABLE IF NOT EXISTS publication_search USING fts5(
    pmid UNINDEXED,
    title,
    abstract
);

CREATE TABLE IF NOT EXISTS publication_embeddings (
    pmid TEXT NOT NULL REFERENCES publications(pmid) ON DELETE CASCADE,
    model_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    vector_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (pmid, model_id)
);
"""


class Repository:
    def __init__(self, path):
        self.path = path

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self):
        with self.connect() as connection:
            connection.executescript(SCHEMA)

    def begin_ingest(self, orcid):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO researchers(orcid, retrieved_at) VALUES (?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(orcid) DO UPDATE SET retrieved_at=CURRENT_TIMESTAMP",
                (orcid,),
            )
            connection.execute("DELETE FROM evidence WHERE orcid = ?", (orcid,))
            connection.execute("DELETE FROM researcher_publications WHERE orcid = ?", (orcid,))

    def save_publication(self, orcid, publication):
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO publications
                   (pmid, title, abstract, year, publication_type, source_url)
                   VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(pmid) DO UPDATE SET
                     title=excluded.title, abstract=excluded.abstract,
                     year=excluded.year, publication_type=excluded.publication_type,
                     source_url=excluded.source_url""",
                (
                    publication.pmid,
                    publication.title,
                    publication.abstract,
                    publication.year,
                    publication.publication_type,
                    publication.source_url,
                ),
            )
            connection.execute(
                "INSERT OR IGNORE INTO researcher_publications(orcid, pmid) VALUES (?, ?)",
                (orcid, publication.pmid),
            )
            connection.execute("DELETE FROM publication_search WHERE pmid = ?", (publication.pmid,))
            connection.execute(
                "INSERT INTO publication_search(pmid, title, abstract) VALUES (?, ?, ?)",
                (publication.pmid, publication.title, publication.abstract),
            )

    def save_taxon(self, taxon):
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO taxa(taxid, scientific_name, rank) VALUES (?, ?, ?)
                   ON CONFLICT(taxid) DO UPDATE SET
                     scientific_name=excluded.scientific_name, rank=excluded.rank""",
                (taxon.taxid, taxon.scientific_name, taxon.rank),
            )

    def save_evidence(self, evidence):
        with self.connect() as connection:
            connection.execute(
                """INSERT OR REPLACE INTO evidence
                   (orcid, pmid, taxid, evidence_type, directness, confidence, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    evidence.orcid,
                    evidence.pmid,
                    evidence.taxid,
                    evidence.evidence_type,
                    evidence.directness,
                    evidence.confidence,
                    evidence.explanation,
                ),
            )

    def report(self, orcid, taxid=None):
        query = """
            SELECT e.taxid, t.scientific_name, t.rank, e.confidence,
                   e.evidence_type, e.directness, e.explanation,
                   p.pmid, p.title, p.abstract, p.year, p.publication_type,
                   p.source_url, e.retrieved_at
            FROM evidence e
            JOIN taxa t ON t.taxid = e.taxid
            JOIN publications p ON p.pmid = e.pmid
            WHERE e.orcid = ?
        """
        parameters = [orcid]
        if taxid is not None:
            query += " AND e.taxid = ?"
            parameters.append(taxid)
        query += " ORDER BY e.confidence DESC, p.year DESC, p.pmid"
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(query, parameters)]

    def stats(self, orcid):
        with self.connect() as connection:
            publications = connection.execute(
                "SELECT COUNT(*) FROM researcher_publications WHERE orcid = ?", (orcid,)
            ).fetchone()[0]
            taxa = connection.execute(
                "SELECT COUNT(DISTINCT taxid) FROM evidence WHERE orcid = ?", (orcid,)
            ).fetchone()[0]
            evidence = connection.execute(
                "SELECT COUNT(*) FROM evidence WHERE orcid = ?", (orcid,)
            ).fetchone()[0]
        return {"publications": publications, "taxa": taxa, "evidence_records": evidence}

    def search_publications(self, orcid, query, limit=5):
        if not query.strip():
            return []
        tokens = [token for token in re.findall(r"[A-Za-z0-9]+", query) if len(token) > 2]
        if not tokens:
            return []
        fts_query = " OR ".join('"{}"'.format(token) for token in tokens[:10])
        sql = """
            SELECT p.pmid, p.title, p.abstract, p.year, p.publication_type, p.source_url
            FROM publication_search s
            JOIN publications p ON p.pmid = s.pmid
            JOIN researcher_publications rp ON rp.pmid = p.pmid
            WHERE rp.orcid = ? AND publication_search MATCH ?
            ORDER BY bm25(publication_search)
            LIMIT ?
        """
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, (orcid, fts_query, limit))]

    def publications_for_orcid(self, orcid):
        sql = """
            SELECT p.pmid, p.title, p.abstract, p.year, p.publication_type, p.source_url
            FROM publications p
            JOIN researcher_publications rp ON rp.pmid = p.pmid
            WHERE rp.orcid = ?
            ORDER BY p.year DESC, p.pmid
        """
        with self.connect() as connection:
            return [dict(row) for row in connection.execute(sql, (orcid,))]

    def save_embedding(self, pmid, model_id, content_hash, vector):
        with self.connect() as connection:
            connection.execute(
                """INSERT INTO publication_embeddings
                   (pmid, model_id, content_hash, vector_json)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(pmid, model_id) DO UPDATE SET
                     content_hash=excluded.content_hash,
                     vector_json=excluded.vector_json,
                     created_at=CURRENT_TIMESTAMP""",
                (pmid, model_id, content_hash, encode_vector(vector)),
            )

    def vector_search(self, orcid, model_id, query_vector, limit=5):
        sql = """
            SELECT p.pmid, p.title, p.abstract, p.year, p.publication_type,
                   p.source_url, pe.vector_json
            FROM publication_embeddings pe
            JOIN publications p ON p.pmid = pe.pmid
            JOIN researcher_publications rp ON rp.pmid = p.pmid
            WHERE rp.orcid = ? AND pe.model_id = ?
        """
        with self.connect() as connection:
            rows = [dict(row) for row in connection.execute(sql, (orcid, model_id))]
        for row in rows:
            row["vector_score"] = cosine_similarity(
                query_vector, decode_vector(row.pop("vector_json"))
            )
        rows.sort(key=lambda item: item["vector_score"], reverse=True)
        return rows[:limit]

    def evidence_for_pmids(self, orcid, pmids):
        if not pmids:
            return {}
        placeholders = ",".join("?" for _ in pmids)
        sql = """
            SELECT e.pmid, e.taxid, t.scientific_name, e.evidence_type,
                   e.confidence, e.explanation
            FROM evidence e
            JOIN taxa t ON t.taxid = e.taxid
            WHERE e.orcid = ? AND e.pmid IN ({})
            ORDER BY e.confidence DESC
        """.format(placeholders)
        grouped = {}
        with self.connect() as connection:
            for row in connection.execute(sql, [orcid] + list(pmids)):
                grouped.setdefault(row["pmid"], []).append(dict(row))
        return grouped
