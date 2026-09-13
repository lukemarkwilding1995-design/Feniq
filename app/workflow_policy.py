"""Shared service-workflow gates; approval is specific to reviewed findings."""
import hashlib
import json
from fastapi import HTTPException
from sqlalchemy import select
from .models import ApprovalRequest, Job

SCOPE_FIELDS = ("product", "system_name", "fault", "module", "diagnosis", "confidence",
                "recommendation", "parts_required")
TRANSITIONS = {
    "New": {"Scheduled", "In Progress", "Cancelled"},
    "Scheduled": {"New", "In Progress", "Cancelled"},
    "In Progress": {"Awaiting Approval", "Complete", "Cancelled"},
    "Awaiting Approval": {"In Progress", "Cancelled"},
    "Complete": {"In Progress"},
    "Cancelled": {"New"},
}


def scope(job):
    content = {key: getattr(job, key) for key in SCOPE_FIELDS}
    content["evidence"] = json.loads(job.evidence_json or "[]")
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def transition(db, order, status, user):
    if status not in TRANSITIONS:
        raise HTTPException(400, "Invalid status")
    if status == order.status:
        return
    if status not in TRANSITIONS.get(order.status, set()):
        raise HTTPException(409, f"Cannot move directly from {order.status} to {status}")
    if order.status in {"Complete", "Cancelled"} and user.role != "admin":
        raise HTTPException(403, "An administrator must reopen this work order")
    if status == "Scheduled" and not order.scheduled_for:
        raise HTTPException(409, "Set a visit date before marking it Scheduled")
    if status == "In Progress" and not order.assigned_engineer_id:
        raise HTTPException(409, "Assign an engineer before starting the visit")
    if status == "Complete":
        job = db.get(Job, order.job_id) if order.job_id else None
        if not job or job.company_id != order.company_id:
            raise HTTPException(409, "Link an inspection before completing this visit")
        if not job.approved_by_engineer:
            raise HTTPException(409, "Engineer review is required before completing this visit")
        if job.outcome not in {"Adjusted / Resolved", "No Fault Found"}:
            raise HTTPException(409, "Record a resolved or no-fault outcome before completing this visit")
        pending = db.scalar(select(ApprovalRequest.id).where(ApprovalRequest.job_id == job.id, ApprovalRequest.status == "Pending"))
        if pending:
            raise HTTPException(409, "Resolve outstanding approval requests before completing this visit")
