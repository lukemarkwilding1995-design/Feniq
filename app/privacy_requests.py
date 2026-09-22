"""Company-scoped request tracking; recording a decision does not execute disclosure or erasure."""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, select, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from .audit import log
from .db import Base, get_db
from .models import Customer, now


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
        return {"request": summary(db, request), "events": events}

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
