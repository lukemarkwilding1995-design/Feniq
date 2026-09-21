"""Field-limited local research candidates with a separate, retained approval.

Payloads are de-identified by allowlist, but source links remain in this
company database. They are not anonymous or authorised for model training.
"""
import hashlib
import json
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, and_, func, select
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base
from .diagnostics import MODULES
from .learning_reviews import LearningReview, integrity_valid
from .models import DiagnosticSnapshot, now
from .outcomes import OutcomeRevision


PRODUCT_CATEGORIES = {"Window", "French Door", "Residential Door", "Bifold", "Sliding Door"}
VERIFICATION_KEYS = (
    "repair_matches_record", "full_operation_cycle",
    "original_fault_rechecked", "safety_security_rechecked",
)
VERIFICATION_VALUES = {"Pass", "Fail", "Not checked"}
REMAKE_VALUES = {"Not applicable", "Yes", "No"}
MIN_AGGREGATE_COUNT = 5


class DatasetDecision(Base):
    __tablename__ = "learning_dataset_decisions"
    __table_args__ = (UniqueConstraint("outcome_revision_id", name="uq_dataset_decision_revision"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    outcome_revision_id: Mapped[str] = mapped_column(ForeignKey("outcome_revisions.id"))
    outcome_sha256: Mapped[str] = mapped_column(String(64))
    learning_review_id: Mapped[str] = mapped_column(ForeignKey("learning_reviews.id"))
    preview_json: Mapped[str] = mapped_column(Text)
    preview_sha256: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(32))
    reason: Mapped[str] = mapped_column(Text)
    decided_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def encoded(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(payload_json):
    return hashlib.sha256(payload_json.encode()).hexdigest()


def prepare(db, revision, review):
    """Return an allowlisted payload or None when provenance/checks are incomplete."""
    if not review or review.company_id != revision.company_id or review.job_id != revision.job_id:
        return None
    if review.outcome_revision_id != revision.id or review.outcome_sha256 != revision.sha256:
        return None
    if review.decision != "Prepare for de-identification" or not integrity_valid(revision):
        return None
    source = json.loads(revision.payload_json)
    if source.get("anonymised_for_learning") is not True:
        return None
    snapshot = db.scalar(select(DiagnosticSnapshot).where(
        DiagnosticSnapshot.job_id == revision.job_id,
        DiagnosticSnapshot.company_id == revision.company_id,
    ))
    if not snapshot or snapshot.sha256 != source.get("snapshot_sha256"):
        return None
    if digest(snapshot.payload_json) != snapshot.sha256:
        return None
    original = json.loads(snapshot.payload_json)
    if original.get("job_id") != revision.job_id or original.get("company_id") != revision.company_id:
        return None
    definition = source.get("verification_definition") or {}
    answers = source.get("verification_answers") or {}
    if definition.get("id") != "feniq-core-repair-verification" or definition.get("revision") != 1:
        return None
    if set(answers) != set(VERIFICATION_KEYS) or set(answers.values()) - VERIFICATION_VALUES:
        return None
    if type(source.get("resolved")) is not bool or type(source.get("repeat_visit_required")) is not bool:
        return None
    predicted = original.get("diagnosis")
    confirmed = source.get("confirmed_diagnosis")
    match = "Unknown"
    if isinstance(predicted, str) and predicted.strip() and isinstance(confirmed, str) and confirmed.strip():
        match = "Yes" if predicted.strip().casefold() == confirmed.strip().casefold() else "No"
    module = original.get("module")
    product = original.get("product")
    remake = source.get("remake_or_part_correct")
    rating = source.get("engineer_rating")
    payload = {
        "schema_version": 1,
        "product_category": product if product in PRODUCT_CATEGORIES else "Other",
        "diagnostic_module": module if snapshot.origin == "server_diagnosis" and module in MODULES else "Unclassified",
        "diagnosis_match": match,
        "resolved": source["resolved"],
        "repeat_visit_required": source["repeat_visit_required"],
        "part_or_remake_correct": remake if remake in REMAKE_VALUES else "Unknown",
        "engineer_usefulness_rating": rating if type(rating) is int and 1 <= rating <= 5 else None,
        "verification_revision": 1,
        "verification_answers": {key: answers[key] for key in VERIFICATION_KEYS},
    }
    return payload


def latest_revisions(db, company_id):
    latest_version = select(
        OutcomeRevision.job_id, func.max(OutcomeRevision.version).label("version")
    ).where(OutcomeRevision.company_id == company_id).group_by(OutcomeRevision.job_id).subquery()
    return db.scalars(select(OutcomeRevision).join(latest_version, and_(
        OutcomeRevision.job_id == latest_version.c.job_id,
        OutcomeRevision.version == latest_version.c.version,
    )).where(OutcomeRevision.company_id == company_id)).all()


def candidates(db, company_id):
    revisions = latest_revisions(db, company_id)
    ids = [revision.id for revision in revisions]
    if not ids:
        return []
    reviews = {row.outcome_revision_id: row for row in db.scalars(select(LearningReview).where(
        LearningReview.company_id == company_id,
        LearningReview.outcome_revision_id.in_(ids),
    )).all()}
    decisions = {row.outcome_revision_id: row for row in db.scalars(select(DatasetDecision).where(
        DatasetDecision.company_id == company_id,
        DatasetDecision.outcome_revision_id.in_(ids),
    )).all()}
    items = []
    for revision in revisions:
        review = reviews.get(revision.id)
        payload = prepare(db, revision, review)
        if payload is None:
            continue
        preview_json = encoded(payload)
        decision = decisions.get(revision.id)
        items.append({
            "outcome_revision_id": revision.id,
            "outcome_version": revision.version,
            "outcome_sha256": revision.sha256,
            "learning_review_id": review.id,
            "first_reviewer_id": review.reviewed_by_id,
            "preview": payload,
            "preview_sha256": digest(preview_json),
            "decision": None if not decision else {
                "id": decision.id, "decision": decision.decision,
                "reason": decision.reason, "created_at": decision.created_at,
                "independent": decision.decided_by_id != review.reviewed_by_id,
            },
        })
    return sorted(items, key=lambda item: item["outcome_revision_id"])


def append(db, revision, review, preview, decision, reason, actor_id):
    preview_json = encoded(preview)
    row = DatasetDecision(
        id=str(uuid.uuid4()), company_id=revision.company_id, job_id=revision.job_id,
        outcome_revision_id=revision.id, outcome_sha256=revision.sha256,
        learning_review_id=review.id, preview_json=preview_json,
        preview_sha256=digest(preview_json), decision=decision,
        reason=reason, decided_by_id=actor_id,
    )
    db.add(row)
    return row


def internal_dataset(db, company_id):
    """Return only current approved field-limited payloads, without source IDs."""
    approved = {row.outcome_revision_id: row for row in db.scalars(select(DatasetDecision).where(
        DatasetDecision.company_id == company_id,
        DatasetDecision.decision == "Approve local research",
    )).all()}
    if not approved:
        return {"count": 0, "records": []}
    reviews = {row.outcome_revision_id: row for row in db.scalars(select(LearningReview).where(
        LearningReview.company_id == company_id,
        LearningReview.outcome_revision_id.in_(approved),
    )).all()}
    records = []
    for revision in latest_revisions(db, company_id):
        decision = approved.get(revision.id)
        if not decision or decision.outcome_sha256 != revision.sha256:
            continue
        review = reviews.get(revision.id)
        if (not review or decision.learning_review_id != review.id
                or decision.decided_by_id == review.reviewed_by_id):
            continue
        preview = prepare(db, revision, review)
        if preview is None or digest(encoded(preview)) != decision.preview_sha256:
            continue
        if digest(decision.preview_json) != decision.preview_sha256:
            continue
        records.append(preview)
    return {"count": len(records), "records": records}


def aggregate(db, company_id):
    """Suppress every statistic until the current independently approved cohort is large enough."""
    records = internal_dataset(db, company_id)["records"]
    result = {"eligible_count": len(records), "minimum_count": MIN_AGGREGATE_COUNT,
              "status": "Ready" if len(records) >= MIN_AGGREGATE_COUNT else "Below threshold",
              "summary": None}
    if len(records) >= MIN_AGGREGATE_COUNT:
        result["summary"] = {
            "records": len(records),
            "resolved": sum(row["resolved"] for row in records),
            "repeat_visits": sum(row["repeat_visit_required"] for row in records),
            "diagnosis_matches": sum(row["diagnosis_match"] == "Yes" for row in records),
        }
    return result


def history(db, company_id, limit, offset):
    total = db.scalar(select(func.count()).select_from(DatasetDecision).where(
        DatasetDecision.company_id == company_id
    )) or 0
    rows = db.scalars(select(DatasetDecision).where(
        DatasetDecision.company_id == company_id
    ).order_by(DatasetDecision.created_at.desc(), DatasetDecision.id.desc()).limit(limit).offset(offset)).all()
    current = {row.job_id: row for row in latest_revisions(db, company_id)} if rows else {}
    sources = {row.id: row for row in db.scalars(select(OutcomeRevision).where(
        OutcomeRevision.company_id == company_id,
        OutcomeRevision.id.in_([decision.outcome_revision_id for decision in rows]),
    )).all()} if rows else {}
    reviews = {row.id: row for row in db.scalars(select(LearningReview).where(
        LearningReview.company_id == company_id,
        LearningReview.id.in_([decision.learning_review_id for decision in rows]),
    )).all()} if rows else {}
    items = []
    for decision in rows:
        latest = current.get(decision.job_id)
        source = sources.get(decision.outcome_revision_id)
        review = reviews.get(decision.learning_review_id)
        if not latest:
            status = "Source unavailable"
        elif latest.id != decision.outcome_revision_id:
            if integrity_valid(latest) and json.loads(latest.payload_json).get("anonymised_for_learning") is not True:
                status = "Consent withdrawn"
            else:
                status = "Superseded"
        elif not integrity_valid(latest) or latest.sha256 != decision.outcome_sha256:
            status = "Source integrity check failed"
        elif not review or (decision.decision == "Approve local research" and decision.decided_by_id == review.reviewed_by_id):
            status = "Independent admin approval needed"
        else:
            status = "Current"
        items.append({
            "id": decision.id,
            "decision": decision.decision,
            "reason": decision.reason,
            "created_at": decision.created_at,
            "decided_by_id": decision.decided_by_id,
            "outcome_version": source.version if source else None,
            "source_integrity_valid": bool(source and integrity_valid(source) and source.sha256 == decision.outcome_sha256),
            "preview_sha256": decision.preview_sha256,
            "preview_integrity_valid": digest(decision.preview_json) == decision.preview_sha256,
            "status": status,
        })
    return {"total": total, "items": items,
            "next_offset": offset + len(items) if offset + len(items) < total else None}
