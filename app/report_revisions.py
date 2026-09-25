"""Immutable PDF report revisions bound to the exact source state used to render them."""
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .acceptance import report_scope as acceptance_report_scope, rows as acceptance_rows, serialise as acceptance_json
from .audit import log as audit_log
from .citations import citation_records
from .db import Base, get_db
from .models import AuditEvent, Job, Photo, User, now
from .outcomes import history as outcome_rows, serialise as outcome_json
from .pdf_report import build_report


class ReportRevision(Base):
    __tablename__ = "report_revisions"
    __table_args__ = (UniqueConstraint("job_id", "version", name="uq_report_revision_version"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source_sha256: Mapped[str] = mapped_column(String(64))
    pdf_sha256: Mapped[str] = mapped_column(String(64))
    byte_count: Mapped[int] = mapped_column(Integer)
    pdf_bytes: Mapped[bytes] = mapped_column(LargeBinary)


class ReportRevisionIn(BaseModel):
    expected_version: int = Field(ge=0)


def history(db: Session, job: Job):
    return db.scalars(
        select(ReportRevision)
        .where(ReportRevision.job_id == job.id, ReportRevision.company_id == job.company_id)
        .order_by(ReportRevision.version)
    ).all()


def _file_sha256(path: Path):
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_report(db: Session, job: Job, upload_dir: Path):
    photos = db.scalars(select(Photo).where(Photo.job_id == job.id).order_by(Photo.created_at, Photo.id)).all()
    citations = citation_records(db, job)
    outcomes = outcome_rows(db, job)
    outcome = outcome_json(outcomes[-1]) if outcomes else None
    acceptances = acceptance_rows(db, job)
    acceptance = acceptance_json(acceptances[-1], acceptance_report_scope(db, job)) if acceptances else None
    source = {
        "company_branding": {
            "report_name": job.engineer.company.report_name or job.engineer.company.name,
            "report_contact": job.engineer.company.report_contact,
            "report_accent": job.engineer.company.report_accent or "#163E31",
        },
        "job": {
            key: getattr(job, key)
            for key in (
                "customer", "reference", "product", "system_name", "fault", "diagnosis",
                "confidence", "evidence_json", "recommendation", "work_done", "parts_required",
                "outcome", "engineer_notes", "signature", "approved_by_engineer", "citation_version",
            )
        },
        "inspection_created_at": job.created_at.isoformat(),
        "engineer": {"id": job.engineer_id, "name": job.engineer.name},
        "photos": [
            {
                "id": photo.id,
                "filename": photo.filename,
                "original_name": photo.original_name,
                "phase": photo.phase,
                "created_at": photo.created_at.isoformat(),
                "content_sha256": _file_sha256(upload_dir / photo.filename),
            }
            for photo in photos
        ],
        "citations": [
            {
                key: row.get(key)
                for key in (
                    "id", "review_id", "document_sha256", "title", "manufacturer", "revision",
                    "page", "excerpt", "relevance", "applicability", "current", "status",
                )
            }
            for row in citations
        ],
        "outcome": {"version": outcomes[-1].version, "sha256": outcomes[-1].sha256} if outcomes else None,
        "acceptance": {
            "version": acceptances[-1].version,
            "created_at": acceptances[-1].created_at.isoformat(),
            "actor_id": acceptances[-1].actor_id,
            "report_sha256": acceptances[-1].report_sha256,
            "sha256": acceptances[-1].sha256,
        } if acceptances else None,
    }
    encoded = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    source_sha256 = hashlib.sha256(encoded.encode()).hexdigest()
    report = build_report(job, job.engineer.name, photos, upload_dir, citations, outcome, acceptance,
                          job.engineer.company).getvalue()
    return report, source_sha256


def serialise(row: ReportRevision, current_source_sha256: str):
    return {
        "version": row.version,
        "created_at": row.created_at,
        "actor_id": row.actor_id,
        "source_sha256": row.source_sha256,
        "source_current": row.source_sha256 == current_source_sha256,
        "pdf_sha256": row.pdf_sha256,
        "byte_count": row.byte_count,
        "integrity_valid": row.byte_count == len(row.pdf_bytes)
        and row.pdf_sha256 == hashlib.sha256(row.pdf_bytes).hexdigest(),
    }


def access_history(db: Session, job: Job):
    events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.company_id == job.company_id,
            AuditEvent.entity_type == "job",
            AuditEvent.entity_id == job.id,
            AuditEvent.action.in_(("inspection.report_downloaded", "inspection.report_revision_downloaded")),
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(250)
    ).all()
    actor_ids = {row.user_id for row in events if row.user_id is not None}
    actors = {row.id: row.name for row in db.scalars(select(User).where(User.id.in_(actor_ids))).all()} if actor_ids else {}
    result = []
    for row in events:
        try:
            detail = json.loads(row.detail_json or "{}")
        except (TypeError, ValueError):
            detail = {}
        result.append({
            "id": row.id,
            "created_at": row.created_at,
            "actor_id": row.user_id,
            "actor_name": actors.get(row.user_id, "Former user" if row.user_id else "System"),
            "kind": "retained_revision" if row.action == "inspection.report_revision_downloaded" else "current_report",
            "version": detail.get("version"),
            "pdf_sha256": detail.get("pdf_sha256"),
        })
    return result


def register(app, user_dep, upload_dir: Path):
    router = APIRouter()

    def job_for(db: Session, job_id: str, user: User):
        job = db.get(Job, job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        if job.company_id != user.company_id:
            raise HTTPException(403, "Wrong company")
        if user.role != "admin" and job.engineer_id != user.id:
            raise HTTPException(403, "Not your job")
        return job

    @router.get("/api/jobs/{job_id}/report-revisions")
    def list_revisions(job_id: str, response: Response, user: User = Depends(user_dep), db: Session = Depends(get_db)):
        job = job_for(db, job_id, user)
        response.headers["Cache-Control"] = "private, no-store"
        _, current_source_sha256 = current_report(db, job, upload_dir)
        return [serialise(row, current_source_sha256) for row in history(db, job)]

    @router.get("/api/jobs/{job_id}/report-access-history")
    def list_access_history(job_id: str, response: Response, user: User = Depends(user_dep), db: Session = Depends(get_db)):
        job = job_for(db, job_id, user)
        response.headers["Cache-Control"] = "private, no-store"
        return access_history(db, job)

    @router.post("/api/jobs/{job_id}/report-revisions")
    def retain(job_id: str, data: ReportRevisionIn, user: User = Depends(user_dep), db: Session = Depends(get_db)):
        job = job_for(db, job_id, user)
        if not job.approved_by_engineer:
            raise HTTPException(409, "Engineer review is required before retaining a report revision")
        revisions = history(db, job)
        if data.expected_version != len(revisions):
            raise HTTPException(409, "Report history changed; reload the inspection")
        report, source_sha256 = current_report(db, job, upload_dir)
        if revisions and revisions[-1].source_sha256 == source_sha256:
            raise HTTPException(409, "The current report state is already retained")
        row = ReportRevision(
            id=str(uuid.uuid4()),
            job_id=job.id,
            company_id=job.company_id,
            version=len(revisions) + 1,
            actor_id=user.id,
            source_sha256=source_sha256,
            pdf_sha256=hashlib.sha256(report).hexdigest(),
            byte_count=len(report),
            pdf_bytes=report,
        )
        db.add(row)
        audit_log(db, user.company_id, user.id, "inspection.report_revision_retained", "job", job.id,
                  {"version": row.version, "source_sha256": source_sha256, "pdf_sha256": row.pdf_sha256})
        db.commit()
        db.refresh(row)
        return serialise(row, source_sha256)

    @router.get("/api/jobs/{job_id}/report-revisions/{version}/pdf")
    def retained_pdf(job_id: str, version: int, user: User = Depends(user_dep), db: Session = Depends(get_db)):
        job = job_for(db, job_id, user)
        row = db.scalar(select(ReportRevision).where(
            ReportRevision.job_id == job.id,
            ReportRevision.company_id == job.company_id,
            ReportRevision.version == version,
        ))
        if not row:
            raise HTTPException(404, "Report revision not found")
        audit_log(db, user.company_id, user.id, "inspection.report_revision_downloaded", "job", job.id,
                  {"version": row.version, "pdf_sha256": row.pdf_sha256})
        db.commit()
        return Response(
            content=row.pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="FenIQ-{job.id[:8]}-r{row.version}.pdf"',
                "Cache-Control": "private, no-store",
                "ETag": f'"{row.pdf_sha256}"',
            },
        )

    app.include_router(router)
