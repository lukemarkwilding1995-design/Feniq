"""Company-scoped request tracking; recording a decision does not execute disclosure or erasure."""
import uuid
import hashlib
import json
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, inspect, or_, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from .audit import log
from .db import Base, get_db
from .models import ApprovalRequest, Customer, DiagnosticSnapshot, Job, JobCustomerLinkEvent, LearningRecord, Photo, WorkOrder, now
from .passports import (Site, ProductPassport, PassportInspection, PassportEvent,
                        PassportCorrection, PassportStateEvent)
from .cases import TechnicalCase, CaseEvent
from .citations import Citation
from .learning_reviews import LearningReview
from .learning_dataset import DatasetDecision
from .outcomes import OutcomeRevision
from .acceptance import CustomerAcceptance
from .report_revisions import ReportRevision


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="Open", index=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PrivacyRequestEvent(Base):
    __tablename__ = "privacy_request_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    request_id: Mapped[str] = mapped_column(ForeignKey("privacy_requests.id"), index=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreateRequest(BaseModel):
    customer_id: str
    kind: Literal["Access", "Correction", "Deletion"]
    summary: str = Field(min_length=5, max_length=2000)


class ChangeRequest(BaseModel):
    version: int = Field(ge=1)
    status: Literal["Open", "Investigating", "Awaiting Decision", "Closed"]
    note: str = Field(min_length=5, max_length=2000)
    resolution: str = Field(default="", max_length=2000)


class ScopeReview(BaseModel):
    version: int = Field(ge=1)
    inventory_sha256: str = Field(min_length=64, max_length=64)
    identity_checked: bool
    linked_records_checked: bool
    unlinked_records_reviewed: bool
    note: str = Field(min_length=5, max_length=2000)


TRANSITIONS = {
    "Open": {"Investigating"},
    "Investigating": {"Awaiting Decision", "Closed"},
    "Awaiting Decision": {"Investigating", "Closed"},
    "Closed": {"Investigating"},
}


def register(app, require_admin):
    def owned(db, identifier, company_id):
        request = db.get(PrivacyRequest, identifier)
        if not request or request.company_id != company_id:
            raise HTTPException(404, "Request not found")
        return request

    def summary(db, request):
        customer = db.get(Customer, request.customer_id)
        return {
            "id": request.id, "customer_id": request.customer_id,
            "customer_name": customer.name if customer else "Unavailable customer",
            "kind": request.kind, "summary": request.summary,
            "status": request.status, "resolution": request.resolution,
            "version": request.version, "created_at": request.created_at,
        }

    def inventory(db, request):
        def record_digest(row):
            columns = {column.key: getattr(row, column.key) for column in inspect(row).mapper.column_attrs}
            encoded = json.dumps(columns, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, default=lambda value: hashlib.sha256(value).hexdigest()
                                 if isinstance(value, bytes) else value.isoformat())
            return hashlib.sha256(encoded.encode()).hexdigest()

        customer = db.get(Customer, request.customer_id)
        sites = db.scalars(select(Site).where(
            Site.company_id == request.company_id, Site.customer_id == request.customer_id
        ).order_by(Site.id)).all()
        site_ids = [row.id for row in sites]
        passports = db.scalars(select(ProductPassport).where(
            ProductPassport.company_id == request.company_id,
            ProductPassport.site_id.in_(site_ids),
        ).order_by(ProductPassport.id)).all()
        passport_ids = [row.id for row in passports]
        orders = db.scalars(select(WorkOrder).where(
            WorkOrder.company_id == request.company_id,
            WorkOrder.customer_id == request.customer_id,
        ).order_by(WorkOrder.id)).all()
        job_ids = {row.job_id for row in orders if row.job_id}
        direct_jobs = db.scalars(select(Job.id).where(
            Job.company_id == request.company_id, Job.customer_id == request.customer_id
        )).all()
        job_ids.update(direct_jobs)
        passport_jobs = db.scalars(select(PassportInspection.job_id).where(
            PassportInspection.passport_id.in_(passport_ids)
        )).all()
        job_ids.update(passport_jobs)
        jobs = db.scalars(select(Job).where(
            Job.company_id == request.company_id, Job.id.in_(job_ids)
        ).order_by(Job.id)).all()
        link_events = db.scalars(select(JobCustomerLinkEvent).join(
            Job, Job.id == JobCustomerLinkEvent.job_id
        ).where(
            JobCustomerLinkEvent.company_id == request.company_id,
            Job.company_id == request.company_id,
            or_(JobCustomerLinkEvent.job_id.in_(job_ids),
                JobCustomerLinkEvent.old_customer_id == request.customer_id,
                JobCustomerLinkEvent.new_customer_id == request.customer_id),
        ).order_by(JobCustomerLinkEvent.id)).all()
        historical_events = [row for row in link_events if row.job_id not in job_ids and
                             request.customer_id in (row.old_customer_id, row.new_customer_id)]
        historical_jobs = {row.id: row for row in db.scalars(select(Job).where(
            Job.company_id == request.company_id,
            Job.id.in_([event.job_id for event in historical_events]),
        )).all()}
        # A name match is a review lead, never proof that the inspection belongs
        # to this customer. Exclude inspections already linked elsewhere.
        structured_job_ids = set(db.scalars(select(Job.id).where(
            Job.company_id == request.company_id, Job.customer_id.is_not(None)
        )).all())
        structured_job_ids.update(db.scalars(select(WorkOrder.job_id).where(
            WorkOrder.company_id == request.company_id, WorkOrder.job_id.is_not(None),
            WorkOrder.customer_id.is_not(None)
        )).all())
        structured_job_ids.update(db.scalars(select(PassportInspection.job_id).join(
            ProductPassport, ProductPassport.id == PassportInspection.passport_id).where(
            ProductPassport.company_id == request.company_id
        )).all())
        customer_name = customer.name.strip().casefold()
        possible_unlinked = []
        if customer_name:
            possible_unlinked = [row for row in db.scalars(select(Job).where(
                Job.company_id == request.company_id,
                Job.id.not_in(structured_job_ids),
            ).order_by(Job.id)).all() if row.customer.strip().casefold() == customer_name]
        review_job_ids = [row.id for row in jobs] + [row.id for row in possible_unlinked]
        photos = db.scalars(select(Photo).where(
            Photo.company_id == request.company_id, Photo.job_id.in_(review_job_ids)
        ).order_by(Photo.id)).all()
        photo_groups = {identifier: [] for identifier in review_job_ids}
        for photo in photos:
            if photo.job_id in photo_groups:
                photo_groups[photo.job_id].append(record_digest(photo))
        cases = db.scalars(select(TechnicalCase).where(
            TechnicalCase.company_id == request.company_id,
            or_(TechnicalCase.passport_id.in_(passport_ids), TechnicalCase.job_id.in_(job_ids)),
        ).order_by(TechnicalCase.id)).all()
        passport_events = db.scalars(select(PassportEvent).where(
            PassportEvent.passport_id.in_(passport_ids)
        ).order_by(PassportEvent.id)).all()
        passport_corrections = db.scalars(select(PassportCorrection).where(
            PassportCorrection.company_id == request.company_id,
            PassportCorrection.passport_id.in_(passport_ids)
        ).order_by(PassportCorrection.id)).all()
        passport_state_events = db.scalars(select(PassportStateEvent).where(
            PassportStateEvent.company_id == request.company_id,
            PassportStateEvent.passport_id.in_(passport_ids)
        ).order_by(PassportStateEvent.id)).all()
        outcome_revisions = db.scalars(select(OutcomeRevision).where(
            OutcomeRevision.company_id == request.company_id,
            OutcomeRevision.job_id.in_(review_job_ids),
        ).order_by(OutcomeRevision.id)).all()
        diagnostic_snapshots = db.scalars(select(DiagnosticSnapshot).where(
            DiagnosticSnapshot.company_id == request.company_id,
            DiagnosticSnapshot.job_id.in_(review_job_ids),
        ).order_by(DiagnosticSnapshot.id)).all()
        citations = db.scalars(select(Citation).where(
            Citation.company_id == request.company_id,
            Citation.job_id.in_(review_job_ids),
        ).order_by(Citation.id)).all()
        approvals = db.scalars(select(ApprovalRequest).where(
            ApprovalRequest.company_id == request.company_id,
            ApprovalRequest.job_id.in_(review_job_ids),
        ).order_by(ApprovalRequest.id)).all()
        learning_records = db.scalars(select(LearningRecord).where(
            LearningRecord.company_id == request.company_id,
            LearningRecord.job_id.in_(review_job_ids),
        ).order_by(LearningRecord.id)).all()
        learning_reviews = db.scalars(select(LearningReview).where(
            LearningReview.company_id == request.company_id,
            LearningReview.job_id.in_(review_job_ids),
        ).order_by(LearningReview.id)).all()
        dataset_decisions = db.scalars(select(DatasetDecision).where(
            DatasetDecision.company_id == request.company_id,
            DatasetDecision.job_id.in_(review_job_ids),
        ).order_by(DatasetDecision.id)).all()
        customer_acceptances = db.scalars(select(CustomerAcceptance).where(
            CustomerAcceptance.company_id == request.company_id,
            CustomerAcceptance.job_id.in_(review_job_ids),
        ).order_by(CustomerAcceptance.id)).all()
        report_revisions = db.scalars(select(ReportRevision).where(
            ReportRevision.company_id == request.company_id,
            ReportRevision.job_id.in_(review_job_ids),
        ).order_by(ReportRevision.id)).all()
        case_events = db.scalars(select(CaseEvent).where(
            CaseEvent.case_id.in_([row.id for row in cases])
        ).order_by(CaseEvent.id)).all()
        def grouped_digest(rows, owner_key):
            grouped = {}
            for row in rows:
                grouped.setdefault(getattr(row, owner_key), []).append(record_digest(row))
            return grouped

        passport_history = grouped_digest(passport_events, "passport_id")
        passport_correction_history = grouped_digest(passport_corrections, "passport_id")
        passport_state_history = grouped_digest(passport_state_events, "passport_id")
        outcome_history = grouped_digest(outcome_revisions, "job_id")
        snapshot_history = grouped_digest(diagnostic_snapshots, "job_id")
        citation_history = grouped_digest(citations, "job_id")
        approval_history = grouped_digest(approvals, "job_id")
        learning_history = grouped_digest(learning_records, "job_id")
        review_history = grouped_digest(learning_reviews, "job_id")
        dataset_history = grouped_digest(dataset_decisions, "job_id")
        acceptance_history = grouped_digest(customer_acceptances, "job_id")
        report_history = grouped_digest(report_revisions, "job_id")
        case_history = grouped_digest(case_events, "case_id")
        link_history = grouped_digest(link_events, "job_id")
        def history_digest(grouped, identifier):
            values = grouped.get(identifier, [])
            return {"count": len(values), "metadata_sha256": hashlib.sha256(json.dumps(values).encode()).hexdigest()}

        payload = {
            "schema_version": 7,
            "customer": {"id": customer.id, "name": customer.name, "record_sha256": record_digest(customer)},
            "sites": [{"id": row.id, "name": row.name, "record_sha256": record_digest(row)} for row in sites],
            "passports": [{"id": row.id, "label": row.label, "record_sha256": record_digest(row),
                           "lifecycle_events": history_digest(passport_history, row.id),
                           "identity_corrections": history_digest(passport_correction_history, row.id),
                           "state_events": history_digest(passport_state_history, row.id)} for row in passports],
            "work_orders": [{"id": row.id, "title": row.title, "job_id": row.job_id,
                             "record_sha256": record_digest(row)} for row in orders],
            "inspections": [{"id": row.id, "reference": row.reference,
                             "record_sha256": record_digest(row),
                             "customer_link_events": history_digest(link_history, row.id),
                             "outcome_revisions": history_digest(outcome_history, row.id),
                             "diagnostic_snapshots": history_digest(snapshot_history, row.id),
                             "reviewed_citations": history_digest(citation_history, row.id),
                             "commercial_approvals": history_digest(approval_history, row.id),
                             "learning_records": history_digest(learning_history, row.id),
                             "learning_reviews": history_digest(review_history, row.id),
                             "dataset_decisions": history_digest(dataset_history, row.id),
                             "customer_acceptances": history_digest(acceptance_history, row.id),
                             "report_revisions": history_digest(report_history, row.id),
                             "photo_count": len(photo_groups[row.id]),
                             "photo_metadata_sha256": hashlib.sha256(json.dumps(photo_groups[row.id]).encode()).hexdigest()} for row in jobs],
            "possible_unlinked_inspections": [{"id": row.id, "reference": row.reference,
                                               "customer_text": row.customer,
                                               "record_sha256": record_digest(row),
                                               "outcome_revisions": history_digest(outcome_history, row.id),
                                               "diagnostic_snapshots": history_digest(snapshot_history, row.id),
                                               "reviewed_citations": history_digest(citation_history, row.id),
                                               "commercial_approvals": history_digest(approval_history, row.id),
                                               "learning_records": history_digest(learning_history, row.id),
                                               "learning_reviews": history_digest(review_history, row.id),
                                               "dataset_decisions": history_digest(dataset_history, row.id),
                                               "customer_acceptances": history_digest(acceptance_history, row.id),
                                               "report_revisions": history_digest(report_history, row.id),
                                               "photo_count": len(photo_groups[row.id]),
                                               "photo_metadata_sha256": hashlib.sha256(json.dumps(photo_groups[row.id]).encode()).hexdigest()} for row in possible_unlinked],
            "historical_customer_link_leads": [{
                "event_id": row.id, "inspection_id": row.job_id,
                "inspection_reference": historical_jobs[row.job_id].reference,
                "event_record_sha256": record_digest(row),
                "inspection_record_sha256": record_digest(historical_jobs[row.job_id]),
            } for row in historical_events if row.job_id in historical_jobs],
            "technical_cases": [{"id": row.id, "title": row.title, "record_sha256": record_digest(row),
                                 "case_events": history_digest(case_history, row.id)} for row in cases],
            "scope_note": "The main inventory uses current explicit inspection-customer, site, passport and work-order links. Inspection counts and checksums include retained diagnostic snapshots, reviewed citations, commercial approvals, learning records, research-governance decisions, customer acceptances and exact PDF report revisions. Those record rows and PDF bytes require separate manual review and are excluded from the Access draft; outcome revisions already in that draft may contain overlapping repair details. Exact customer-name matches and historical correction links below are manual-review leads, not current linked records. Other names and systems may be missed. Private library content and media bytes require manual review; photo metadata counts are not file integrity checks.",
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return {"inventory": payload, "inventory_sha256": hashlib.sha256(encoded.encode()).hexdigest()}

    def scope_ready(db, request, version, inventory_sha256):
        reviews = db.scalars(select(PrivacyRequestEvent).where(
            PrivacyRequestEvent.request_id == request.id,
            PrivacyRequestEvent.status == "Scope reviewed",
        )).all()
        return any((evidence := json.loads(row.note)).get("ready_version") == version
                   and evidence.get("inventory_sha256") == inventory_sha256 for row in reviews)

    @app.get("/api/privacy-requests")
    def list_requests(admin=Depends(require_admin), db: Session = Depends(get_db)):
        rows = db.scalars(select(PrivacyRequest).where(
            PrivacyRequest.company_id == admin.company_id
        ).order_by(PrivacyRequest.created_at.desc(), PrivacyRequest.id.desc())).all()
        return [summary(db, row) for row in rows]

    @app.post("/api/privacy-requests")
    def create_request(data: CreateRequest, admin=Depends(require_admin), db: Session = Depends(get_db)):
        customer = db.get(Customer, data.customer_id)
        if not customer or customer.company_id != admin.company_id:
            raise HTTPException(404, "Customer not found")
        note = data.summary.strip()
        if len(note) < 5:
            raise HTTPException(422, "Describe the request")
        request = PrivacyRequest(id=str(uuid.uuid4()), company_id=admin.company_id,
                                 customer_id=customer.id, kind=data.kind, summary=note,
                                 created_by_id=admin.id)
        db.add(request)
        db.flush()
        db.add(PrivacyRequestEvent(id=str(uuid.uuid4()), request_id=request.id,
                                   actor_id=admin.id, status="Open", note=note))
        log(db, admin.company_id, admin.id, "privacy_request.created", "privacy_request", request.id)
        db.commit()
        return summary(db, request)

    @app.get("/api/privacy-requests/{identifier}")
    def get_request(identifier: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
        request = owned(db, identifier, admin.company_id)
        events = db.scalars(select(PrivacyRequestEvent).where(
            PrivacyRequestEvent.request_id == request.id
        ).order_by(PrivacyRequestEvent.created_at, PrivacyRequestEvent.id)).all()
        return {"request": summary(db, request), "events": events,
                "scope_ready": scope_ready(db, request, request.version,
                                           inventory(db, request)["inventory_sha256"])}

    @app.get("/api/privacy-requests/{identifier}/inventory")
    def get_inventory(identifier: str, admin=Depends(require_admin), db: Session = Depends(get_db)):
        return inventory(db, owned(db, identifier, admin.company_id))

    @app.post("/api/privacy-requests/{identifier}/scope-review")
    def review_scope(identifier: str, data: ScopeReview,
                     admin=Depends(require_admin), db: Session = Depends(get_db)):
        request = owned(db, identifier, admin.company_id)
        if request.status not in {"Investigating", "Awaiting Decision"}:
            raise HTTPException(409, "Investigate the request before reviewing its scope")
        if not (data.identity_checked and data.linked_records_checked and data.unlinked_records_reviewed):
            raise HTTPException(422, "Confirm identity and review both linked and unlinked records")
        note = data.note.strip()
        if len(note) < 5:
            raise HTTPException(422, "Describe the manual review")
        current = inventory(db, request)
        if current["inventory_sha256"] != data.inventory_sha256:
            raise HTTPException(409, "Linked records changed; reopen the inventory")
        changed = db.execute(update(PrivacyRequest).where(
            PrivacyRequest.id == request.id, PrivacyRequest.company_id == admin.company_id,
            PrivacyRequest.version == data.version,
        ).values(version=PrivacyRequest.version + 1).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            raise HTTPException(409, "Request changed; reload it")
        evidence = json.dumps({"inventory_sha256": current["inventory_sha256"],
                               "ready_version": data.version + 1, "note": note,
                               "identity_checked": True, "linked_records_checked": True,
                               "unlinked_records_reviewed": True}, sort_keys=True)
        db.add(PrivacyRequestEvent(id=str(uuid.uuid4()), request_id=request.id,
                                   actor_id=admin.id, status="Scope reviewed", note=evidence))
        log(db, admin.company_id, admin.id, "privacy_request.scope_reviewed", "privacy_request", request.id,
            {"inventory_sha256": current["inventory_sha256"]})
        db.commit()
        return {"ok": True, "version": data.version + 1}

    @app.get("/api/privacy-requests/{identifier}/access-preview")
    def access_preview(identifier: str, response: Response,
                       admin=Depends(require_admin), db: Session = Depends(get_db)):
        request = owned(db, identifier, admin.company_id)
        if request.kind != "Access" or request.status not in {"Investigating", "Awaiting Decision"}:
            raise HTTPException(409, "An active access request is required")
        scope = inventory(db, request)
        if not scope_ready(db, request, request.version, scope["inventory_sha256"]):
            raise HTTPException(409, "Review the current identity and inventory before preparing a draft")

        def selected(row, keys):
            return {key: getattr(row, key).isoformat() if isinstance(getattr(row, key), datetime)
                    else getattr(row, key) for key in keys}

        items = scope["inventory"]
        customer = db.get(Customer, request.customer_id)
        site_ids = [row["id"] for row in items["sites"]]
        passport_ids = [row["id"] for row in items["passports"]]
        order_ids = [row["id"] for row in items["work_orders"]]
        job_ids = [row["id"] for row in items["inspections"]]
        case_ids = [row["id"] for row in items["technical_cases"]]
        sites = db.scalars(select(Site).where(Site.company_id == admin.company_id, Site.id.in_(site_ids)).order_by(Site.id)).all()
        passports = db.scalars(select(ProductPassport).where(ProductPassport.company_id == admin.company_id, ProductPassport.id.in_(passport_ids)).order_by(ProductPassport.id)).all()
        orders = db.scalars(select(WorkOrder).where(WorkOrder.company_id == admin.company_id, WorkOrder.id.in_(order_ids)).order_by(WorkOrder.id)).all()
        jobs = db.scalars(select(Job).where(Job.company_id == admin.company_id, Job.id.in_(job_ids)).order_by(Job.id)).all()
        cases = db.scalars(select(TechnicalCase).where(TechnicalCase.company_id == admin.company_id, TechnicalCase.id.in_(case_ids)).order_by(TechnicalCase.id)).all()
        outcomes = db.scalars(select(OutcomeRevision).where(OutcomeRevision.company_id == admin.company_id, OutcomeRevision.job_id.in_(job_ids)).order_by(OutcomeRevision.job_id, OutcomeRevision.version)).all()
        photos = db.scalars(select(Photo).where(Photo.company_id == admin.company_id, Photo.job_id.in_(job_ids)).order_by(Photo.id)).all()
        passport_events = db.scalars(select(PassportEvent).where(PassportEvent.passport_id.in_(passport_ids)).order_by(PassportEvent.id)).all()
        passport_corrections = db.scalars(select(PassportCorrection).where(PassportCorrection.company_id == admin.company_id, PassportCorrection.passport_id.in_(passport_ids)).order_by(PassportCorrection.passport_id, PassportCorrection.version)).all()
        passport_state_events = db.scalars(select(PassportStateEvent).where(PassportStateEvent.company_id == admin.company_id, PassportStateEvent.passport_id.in_(passport_ids)).order_by(PassportStateEvent.passport_id, PassportStateEvent.version)).all()
        case_events = db.scalars(select(CaseEvent).where(CaseEvent.case_id.in_(case_ids)).order_by(CaseEvent.id)).all()
        response.headers["Cache-Control"] = "private, no-store"
        return {
            "request_id": request.id, "request_version": request.version,
            "inventory_sha256": scope["inventory_sha256"],
            "draft_only": True,
            "review_note": "Internal draft of explicitly linked FenIQ records. Check identity, third-party content, unlinked records and media separately before any disclosure. This endpoint does not send or export data.",
            "possible_unlinked_inspection_count": len(items["possible_unlinked_inspections"]),
            "historical_customer_link_lead_count": len(items["historical_customer_link_leads"]),
            "customer": selected(customer, ("id", "name", "contact_name", "email", "phone", "address")),
            "sites": [selected(row, ("id", "name", "address")) for row in sites],
            "passports": [selected(row, ("id", "site_id", "label", "product", "manufacturer", "system_name", "serial_number", "version", "archived_at")) for row in passports],
            "work_orders": [selected(row, ("id", "customer_id", "job_id", "title", "status", "scheduled_for", "site_reference", "notes")) for row in orders],
            "inspections": [selected(row, ("id", "reference", "customer", "product", "fault", "diagnosis", "recommendation", "work_done", "parts_required", "outcome", "engineer_notes", "signature", "created_at")) for row in jobs],
            "outcome_revisions": [{"job_id": row.job_id, "version": row.version,
                                   "payload": json.loads(row.payload_json)} for row in outcomes],
            "photo_metadata": [selected(row, ("id", "job_id", "original_name", "phase")) for row in photos],
            "passport_events": [selected(row, ("passport_id", "kind", "occurred_on", "note")) for row in passport_events],
            "passport_corrections": [{"passport_id": row.passport_id, "version": row.version,
                                       "created_at": row.created_at.isoformat(),
                                       "payload": json.loads(row.payload_json)} for row in passport_corrections],
            "passport_state_events": [{"passport_id": row.passport_id, "version": row.version,
                                        "created_at": row.created_at.isoformat(),
                                        "payload": json.loads(row.payload_json)} for row in passport_state_events],
            "technical_cases": [selected(row, ("id", "title", "description", "status", "resolution")) for row in cases],
            "case_events": [selected(row, ("case_id", "kind", "note")) for row in case_events],
        }

    @app.patch("/api/privacy-requests/{identifier}")
    def change_request(identifier: str, data: ChangeRequest,
                       admin=Depends(require_admin), db: Session = Depends(get_db)):
        request = owned(db, identifier, admin.company_id)
        note = data.note.strip()
        resolution = data.resolution.strip()
        if len(note) < 5:
            raise HTTPException(422, "Explain the status change")
        if data.status == request.status or data.status not in TRANSITIONS[request.status]:
            raise HTTPException(409, "Follow the request review workflow")
        if data.status == "Closed" and len(resolution) < 5:
            raise HTTPException(422, "Record a decision before closing")
        if data.status != "Closed" and resolution:
            raise HTTPException(422, "Record the decision only when closing")
        if data.status == "Closed":
            current_hash = inventory(db, request)["inventory_sha256"]
            if not scope_ready(db, request, data.version, current_hash):
                raise HTTPException(409, "Review the current inventory and identity before closing")
        changed = db.execute(update(PrivacyRequest).where(
            PrivacyRequest.id == request.id,
            PrivacyRequest.company_id == admin.company_id,
            PrivacyRequest.version == data.version,
        ).values(status=data.status, resolution=resolution,
                 version=PrivacyRequest.version + 1).execution_options(synchronize_session=False))
        if changed.rowcount != 1:
            raise HTTPException(409, "Request changed; reload it")
        retained_note = note + ("\nDecision: " + resolution if resolution else "")
        db.add(PrivacyRequestEvent(id=str(uuid.uuid4()), request_id=request.id,
                                   actor_id=admin.id, status=data.status, note=retained_note))
        log(db, admin.company_id, admin.id, "privacy_request.status_changed", "privacy_request", request.id,
            {"status": data.status})
        db.commit()
        db.refresh(request)
        return summary(db, request)
