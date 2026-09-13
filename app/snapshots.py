"""Original saved diagnosis evidence, never reconstructed from later repairs."""
import hashlib
import json
import uuid
from pathlib import Path
from sqlalchemy import select
from .models import DiagnosticSnapshot


def original(db, job_id):
    return db.scalar(select(DiagnosticSnapshot).where(DiagnosticSnapshot.job_id == job_id))


def capture(db, job, actor_id, answers=None, origin="legacy_capture"):
    existing = original(db, job.id)
    if existing:
        return existing
    from .diagnostics import MODULES
    module = MODULES.get(job.module, {})
    payload = {
        "schema_version": 1,
        "job_id": job.id,
        "company_id": job.company_id,
        "engineer_id": job.engineer_id,
        "customer": job.customer,
        "reference": job.reference,
        "product": job.product,
        "system_name": job.system_name,
        "fault": job.fault,
        "module": job.module,
        "diagnosis": job.diagnosis,
        "confidence": job.confidence,
        "evidence": json.loads(job.evidence_json or "[]"),
        "recommendation": job.recommendation,
        "answers": answers,
        "checks": module.get("checks", []) if answers is not None else [],
        "rules_sha256": hashlib.sha256(Path(__file__).with_name("diagnostics.py").read_bytes()).hexdigest() if answers is not None else None,
        "source_status": "Field Guidance; manufacturer specifications require verified evidence",
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    record = DiagnosticSnapshot(id=str(uuid.uuid4()), job_id=job.id, company_id=job.company_id,
                                captured_by_id=actor_id, origin=origin, payload_json=encoded,
                                sha256=hashlib.sha256(encoded.encode()).hexdigest())
    db.add(record)
    db.flush()
    return record


def serialise(record):
    if record is None:
        return None
    return {"id": record.id, "origin": record.origin, "captured_at": record.captured_at,
            "sha256": record.sha256, "payload": json.loads(record.payload_json),
            "integrity_valid": hashlib.sha256(record.payload_json.encode()).hexdigest() == record.sha256}
