"""One private, resumable inspection draft per engineer; never a diagnosis or sign-off."""
import json
from datetime import datetime
from typing import Any, Literal

from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from .audit import log
from .db import Base, get_db
from .diagnostics import MODULES
from .models import Customer, WorkOrder, now


class InspectionDraft(Base):
    __tablename__ = "inspection_drafts"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    step: Mapped[str] = mapped_column(String(20))
    payload_json: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class SaveDraft(BaseModel):
    expected_version: int = Field(ge=0)
    step: Literal["details", "checks", "result"]
    payload: dict[str, Any]


FIELDS = {
    "customer", "customer_id", "reference", "product", "system_name", "fault",
    "module", "diagnostic_answers", "work_order_id", "work_done",
    "parts_required", "outcome", "engineer_notes",
}
FIELD_LIMITS = {"customer": 255, "reference": 120, "product": 100,
                "system_name": 180, "module": 180}


def clean_payload(db, user, payload):
    if set(payload) - FIELDS:
        raise HTTPException(422, "Draft contains unsupported fields")
    cleaned = {}
    for key, value in payload.items():
        if key == "diagnostic_answers":
            if not isinstance(value, dict):
                raise HTTPException(422, "Draft checks must be an object")
            cleaned[key] = value
        elif key in {"customer_id", "work_order_id"}:
            if value is not None and (not isinstance(value, str) or len(value) > 64):
                raise HTTPException(422, "Invalid draft link")
            cleaned[key] = value or None
        elif not isinstance(value, str) or len(value) > FIELD_LIMITS.get(key, 10000):
            raise HTTPException(422, "Invalid draft field")
        else:
            cleaned[key] = value
    module_id = cleaned.get("module")
    if module_id:
        module = MODULES.get(module_id)
        if not module:
            raise HTTPException(422, "Unknown diagnostic module")
        checks = {check["key"]: check for check in module["checks"]}
        for key, value in cleaned.get("diagnostic_answers", {}).items():
            check = checks.get(key)
            if not check:
                raise HTTPException(422, "Unknown diagnostic check")
            if check["type"] == "bool":
                valid = type(value) is bool
            elif check["type"] == "number":
                valid = type(value) in (int, float) and 0 <= value < 1000000
            else:
                valid = value in check["options"]
            if not valid:
                raise HTTPException(422, "Invalid draft check value")
    elif cleaned.get("diagnostic_answers"):
        raise HTTPException(422, "Choose a diagnostic module before saving checks")
    customer_id = cleaned.get("customer_id")
    if customer_id:
        customer = db.get(Customer, customer_id)
        if not customer or customer.company_id != user.company_id:
            raise HTTPException(404, "Customer not found")
    order_id = cleaned.get("work_order_id")
    if order_id:
        order = db.get(WorkOrder, order_id)
        if not order or order.company_id != user.company_id:
            raise HTTPException(404, "Work order not found")
        if user.role != "admin" and order.assigned_engineer_id != user.id:
            raise HTTPException(403, "Work order is not assigned to you")
        if order.job_id or order.status in {"Complete", "Cancelled"}:
            raise HTTPException(409, "Work order can no longer start an inspection")
        if customer_id and order.customer_id and customer_id != order.customer_id:
            raise HTTPException(409, "Inspection customer must match the work order")
    encoded = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    if len(encoded.encode()) > 40000:
        raise HTTPException(422, "Draft is too large")
    return encoded


def serialise(row):
    if row is None:
        return None
    return {"version": row.version, "step": row.step,
            "payload": json.loads(row.payload_json), "updated_at": row.updated_at}


def register(app, user_dep):
    @app.get("/api/inspection-draft")
    def get_draft(response: Response, user=Depends(user_dep), db: Session = Depends(get_db)):
        response.headers["Cache-Control"] = "private, no-store"
        row = db.get(InspectionDraft, user.id)
        return serialise(row if row and row.company_id == user.company_id else None)

    @app.put("/api/inspection-draft")
    def save_draft(data: SaveDraft, user=Depends(user_dep), db: Session = Depends(get_db)):
        encoded = clean_payload(db, user, data.payload)
        current = db.get(InspectionDraft, user.id)
        if current and current.company_id != user.company_id:
            raise HTTPException(409, "Draft owner changed")
        if current:
            changed = db.execute(update(InspectionDraft).where(
                InspectionDraft.user_id == user.id,
                InspectionDraft.company_id == user.company_id,
                InspectionDraft.version == data.expected_version,
            ).values(version=InspectionDraft.version + 1, step=data.step,
                     payload_json=encoded, updated_at=now()).execution_options(synchronize_session=False))
            if changed.rowcount != 1:
                raise HTTPException(409, "Draft changed; reload it before saving")
        else:
            if data.expected_version != 0:
                raise HTTPException(409, "Draft changed; reload it before saving")
            db.add(InspectionDraft(user_id=user.id, company_id=user.company_id,
                                   version=1, step=data.step, payload_json=encoded))
        log(db, user.company_id, user.id, "inspection.draft_saved", "inspection_draft", user.id,
            {"step": data.step})
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Draft changed; reload it before saving")
        return serialise(db.get(InspectionDraft, user.id))

    @app.delete("/api/inspection-draft")
    def discard_draft(expected_version: int = Query(ge=1), user=Depends(user_dep),
                      db: Session = Depends(get_db)):
        changed = db.execute(delete(InspectionDraft).where(
            InspectionDraft.user_id == user.id,
            InspectionDraft.company_id == user.company_id,
            InspectionDraft.version == expected_version,
        ))
        if changed.rowcount != 1:
            raise HTTPException(409, "Draft changed; reload it before discarding")
        log(db, user.company_id, user.id, "inspection.draft_discarded", "inspection_draft", user.id)
        db.commit()
        return {"ok": True}
