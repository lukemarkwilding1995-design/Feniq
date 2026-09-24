"""Explicit, forward-only migrations with frozen DDL and revision checksums.

Run one migration process per deployment; stop application writers first.
"""
import hashlib
import json
from pathlib import Path
from sqlalchemy import inspect, text

DIRECTORY = Path(__file__).resolve().parents[1] / "migrations"
REVISIONS = ("0001_baseline", "0002_snapshots", "0003_approval_scope", "0004_passports", "0005_cases", "0006_source_reviews", "0007_citations", "0008_outcomes", "0009_learning_reviews", "0010_learning_dataset", "0011_privacy_requests", "0012_job_customer_link", "0013_customer_link_review", "0014_inspection_drafts")

def fingerprint(source):
    return hashlib.sha256(json.dumps(json.loads(source), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def upgrade(engine):
    dialect = engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("Migrations support SQLite and PostgreSQL only")
    with engine.begin() as connection:
        if dialect == "sqlite":
            connection.exec_driver_sql("BEGIN IMMEDIATE")
        else:
            connection.exec_driver_sql("SELECT pg_advisory_xact_lock(624191)")
        connection.exec_driver_sql("CREATE TABLE IF NOT EXISTS feniq_schema_revisions (revision VARCHAR(40) PRIMARY KEY, checksum VARCHAR(64) NOT NULL)")
        applied = dict(connection.execute(text("SELECT revision, checksum FROM feniq_schema_revisions")).all())
        if set(applied) - set(REVISIONS):
            raise RuntimeError("Database is newer than this application")
        for revision in REVISIONS:
            source = (DIRECTORY / f"{revision}_{dialect}.json").read_bytes()
            checksum = fingerprint(source)
            if revision in applied:
                if applied[revision] != checksum:
                    raise RuntimeError(f"Applied migration changed: {revision}")
                continue
            instructions = json.loads(source)
            if revision == "0001_baseline":
                inspector = inspect(connection)
                existing = set(inspector.get_table_names())
                for table in instructions:
                    if table["name"] in existing:
                        columns = {c["name"] for c in inspector.get_columns(table["name"])}
                        if columns != set(table["columns"]):
                            raise RuntimeError(f"Unexpected legacy schema for {table['name']}; migration stopped")
                        continue
                    for statement in table["sql"]:
                        connection.exec_driver_sql(statement)
            else:
                for statement in instructions:
                    connection.exec_driver_sql(statement)
            connection.execute(text("INSERT INTO feniq_schema_revisions (revision, checksum) VALUES (:revision, :checksum)"), {"revision": revision, "checksum": checksum})
    return REVISIONS[-1]


def require_current(engine):
    with engine.connect() as connection:
        if not inspect(connection).has_table("feniq_schema_revisions"):
            raise RuntimeError("Database migration required: python scripts/migrate.py")
        applied = dict(connection.execute(text("SELECT revision, checksum FROM feniq_schema_revisions")).all())
        expected = {r: fingerprint((DIRECTORY / f"{r}_{engine.dialect.name}.json").read_bytes()) for r in REVISIONS}
        if applied != expected:
            raise RuntimeError("Database revision mismatch; run python scripts/migrate.py with application writers stopped")
