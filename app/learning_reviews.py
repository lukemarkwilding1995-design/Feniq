"""Company-admin decisions on consented outcome revisions.

These decisions do not anonymise records or promote them to a model/rule set.
"""
import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, and_, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .models import now
from .outcomes import OutcomeRevision


class LearningReview(Base):
    __tablename__ = "learning_reviews"
    __table_args__ = (UniqueConstraint("outcome_revision_id", name="uq_learning_review_revision"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    outcome_revision_id: Mapped[str] = mapped_column(ForeignKey("outcome_revisions.id"))
    outcome_sha256: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    reviewed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def integrity_valid(revision):
    return hashlib.sha256(revision.payload_json.encode()).hexdigest() == revision.sha256


def current_candidates(db, company_id):
    latest_version = select(
        OutcomeRevision.job_id, func.max(OutcomeRevision.version).label("version")
    ).where(OutcomeRevision.company_id == company_id).group_by(
        OutcomeRevision.job_id
    ).subquery()
    latest = db.scalars(select(OutcomeRevision).join(latest_version, and_(
        OutcomeRevision.job_id == latest_version.c.job_id,
        OutcomeRevision.version == latest_version.c.version,
    )).where(OutcomeRevision.company_id == company_id)).all()
    eligible = []
    for revision in latest:
        if not integrity_valid(revision):
            continue
        payload = json.loads(revision.payload_json)
        if payload.get("anonymised_for_learning") is True:
            eligible.append((revision, payload))
    return eligible


def queue(db, company_id):
    candidates = current_candidates(db, company_id)
    candidate_ids = [revision.id for revision, _ in candidates]
    reviews = {r.outcome_revision_id: r for r in db.scalars(
        select(LearningReview).where(
            LearningReview.company_id == company_id,
            LearningReview.outcome_revision_id.in_(candidate_ids),
        )
    ).all()} if candidate_ids else {}
    items = []
    for revision, payload in candidates:
        review = reviews.get(revision.id)
        items.append({
            "job_id": revision.job_id,
            "outcome_revision_id": revision.id,
            "outcome_version": revision.version,
            "outcome_sha256": revision.sha256,
            "created_at": revision.created_at,
            "predicted_diagnosis": payload.get("predicted_diagnosis", ""),
            "confirmed_diagnosis": payload.get("confirmed_diagnosis", ""),
            "actual_repair": payload.get("actual_repair", ""),
            "resolved": payload.get("resolved"),
            "review": None if not review else {
                "id": review.id,
                "decision": review.decision,
                "reason": review.reason,
                "reviewed_by_id": review.reviewed_by_id,
                "created_at": review.created_at,
            },
        })
    return sorted(items, key=lambda item: item["created_at"], reverse=True)


def history(db, company_id, limit, offset):
    statement = select(LearningReview, OutcomeRevision).join(
        OutcomeRevision, LearningReview.outcome_revision_id == OutcomeRevision.id
    ).where(
        LearningReview.company_id == company_id,
        OutcomeRevision.company_id == company_id,
    )
    total = db.scalar(select(func.count()).select_from(LearningReview).where(
        LearningReview.company_id == company_id
    )) or 0
    rows = db.execute(statement.order_by(
        LearningReview.created_at.desc(), LearningReview.id.desc()
    ).limit(limit).offset(offset)).all()
    job_ids = {review.job_id for review, _ in rows}
    current = {}
    if job_ids:
        latest_version = select(
            OutcomeRevision.job_id, func.max(OutcomeRevision.version).label("version")
        ).where(
            OutcomeRevision.company_id == company_id,
            OutcomeRevision.job_id.in_(job_ids),
        ).group_by(OutcomeRevision.job_id).subquery()
        for revision in db.scalars(select(OutcomeRevision).join(latest_version, and_(
            OutcomeRevision.job_id == latest_version.c.job_id,
            OutcomeRevision.version == latest_version.c.version,
        )).where(OutcomeRevision.company_id == company_id)).all():
            current[revision.job_id] = revision
    items = []
    for review, source in rows:
        latest = current[review.job_id]
        if latest.id == source.id:
            status = "Current"
        elif not integrity_valid(latest):
            status = "Latest outcome integrity check failed"
        elif json.loads(latest.payload_json).get("anonymised_for_learning") is not True:
            status = "Consent withdrawn"
        else:
            status = "Superseded"
        items.append({
            "id": review.id,
            "job_id": review.job_id,
            "outcome_revision_id": source.id,
            "outcome_version": source.version,
            "outcome_sha256": review.outcome_sha256,
            "source_integrity_valid": integrity_valid(source) and source.sha256 == review.outcome_sha256,
            "decision": review.decision,
            "reason": review.reason,
            "reviewed_by_id": review.reviewed_by_id,
            "created_at": review.created_at,
            "status": status,
        })
    return {"total": total, "items": items,
            "next_offset": offset + len(items) if offset + len(items) < total else None}


def append(db, revision, actor_id, decision, reason):
    review = LearningReview(
        id=str(uuid.uuid4()), company_id=revision.company_id,
        job_id=revision.job_id, outcome_revision_id=revision.id,
        outcome_sha256=revision.sha256, decision=decision,
        reason=reason, reviewed_by_id=actor_id,
    )
    db.add(review)
    return review
