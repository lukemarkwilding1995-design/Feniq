"""Run an isolated PostgreSQL migration smoke test against a disposable schema.

Set FENIQ_TEST_POSTGRES_URL to a database where the caller may create schemas.
The script creates and drops only a randomly named feniq_validation_* schema.
"""
import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.migrations import REVISIONS, require_current, upgrade


def main():
    raw_url = os.getenv("FENIQ_TEST_POSTGRES_URL")
    if not raw_url:
        raise SystemExit("Set FENIQ_TEST_POSTGRES_URL to a disposable PostgreSQL database")
    url = make_url(raw_url)
    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise SystemExit("FENIQ_TEST_POSTGRES_URL must use the psycopg PostgreSQL driver")
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")

    schema = "feniq_validation_" + uuid.uuid4().hex
    administrator = create_engine(url, future=True, pool_pre_ping=True)
    isolated = None
    created = False
    try:
        with administrator.begin() as connection:
            connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
            created = True
        isolated = create_engine(url, future=True, pool_pre_ping=True,
                                 connect_args={"options": f"-csearch_path={schema}"})
        with isolated.connect() as connection:
            actual = connection.execute(text("SELECT current_schema()")).scalar_one()
            if actual != schema:
                raise RuntimeError("PostgreSQL search path did not select the test schema")

        if upgrade(isolated) != REVISIONS[-1] or upgrade(isolated) != REVISIONS[-1]:
            raise RuntimeError("Migration did not reach the current revision")
        require_current(isolated)

        with isolated.begin() as connection:
            count = connection.execute(text("SELECT count(*) FROM feniq_schema_revisions")).scalar_one()
            if count != len(REVISIONS):
                raise RuntimeError("Migration ledger has an unexpected revision count")
            company_id = connection.execute(text(
                "INSERT INTO companies (name, invite_code, created_at) "
                "VALUES ('PostgreSQL validation', :code, now()) RETURNING id"
            ), {"code": schema}).scalar_one()
            user_id = connection.execute(text(
                "INSERT INTO users (company_id, email, name, password_hash, role, active, created_at) "
                "VALUES (:company, :email, 'Validation admin', 'test-only', 'admin', true, now()) RETURNING id"
            ), {"company": company_id, "email": f"{schema}@example.test"}).scalar_one()
            connection.execute(text(
                "INSERT INTO customers (id, company_id, name, contact_name, email, phone, address, created_at) "
                "VALUES ('validation-customer', :company, 'Fictional customer', '', '', '', '', now())"
            ), {"company": company_id})
            connection.execute(text(
                "INSERT INTO privacy_requests (id, company_id, customer_id, kind, summary, status, "
                "resolution, version, created_by_id, created_at) "
                "VALUES ('validation-request', :company, 'validation-customer', 'Access', "
                "'Fictional request', 'Open', '', 1, :user, now())"
            ), {"company": company_id, "user": user_id})
            connection.execute(text(
                "INSERT INTO privacy_request_events (id, request_id, actor_id, status, note, created_at) "
                "VALUES ('validation-event', 'validation-request', :user, 'Open', 'Fictional', now())"
            ), {"user": user_id})
            try:
                with connection.begin_nested():
                    connection.execute(text(
                        "UPDATE privacy_request_events SET note='tampered' WHERE id='validation-event'"
                    ))
            except DBAPIError:
                pass
            else:
                raise RuntimeError("PostgreSQL allowed immutable request history to change")
            note = connection.execute(text(
                "SELECT note FROM privacy_request_events WHERE id='validation-event'"
            )).scalar_one()
            if note != "Fictional":
                raise RuntimeError("Request history changed despite its trigger")
        print(f"PostgreSQL validation passed: {len(REVISIONS)} migrations, repeat upgrade, "
              "ledger, writes and immutable request history")
    finally:
        if isolated is not None:
            isolated.dispose()
        if created:
            with administrator.begin() as connection:
                connection.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        administrator.dispose()


if __name__ == "__main__":
    main()
