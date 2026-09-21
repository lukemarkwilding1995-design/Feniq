"""Company-admin decisions on consented outcome revisions.

These decisions do not anonymise records or promote them to a model/rule set.
"""
import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, select
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
    revisions = db.scalars(select(OutcomeRevision).where(
        OutcomeRevision.company_id == company_id
    ).order_by(OutcomeRevision.job_id, OutcomeRevision.version.desc())).all()
    latest = {}
    for revision in revisions:
        latest.setdefault(revision.job_id, revision)
    eligible = []
    for revision in latest.values():
        if not integrity_valid(revision):
            continue
        payload = json.loads(revision.payload_json)
        if payload.get("anonymised_for_learning") is True:
            eligible.append((revision, payload))
    return eligible


def queue(db, company_id):
    candidates = current_candidates(db, company_id)
    reviews = {r.outcome_revision_id: r for r in db.scalars(
        select(LearningReview).where(LearningReview.company_id == company_id)
    ).all()}
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


def append(db, revision, actor_id, decision, reason):
    review = LearningReview(
        id=str(uuid.uuid4()), company_id=revision.company_id,
        job_id=revision.job_id, outcome_revision_id=revision.id,
        outcome_sha256=revision.sha256, decision=decision,
        reason=reason, reviewed_by_id=actor_id,
    )
    db.add(review)
    return review
