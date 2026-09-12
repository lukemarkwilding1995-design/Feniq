from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from .db import Base

def now():
    return datetime.now(timezone.utc)

class Company(Base):
    __tablename__ = "companies"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    invite_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30), default="engineer")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    company = relationship("Company")

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    engineer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    customer: Mapped[str] = mapped_column(String(255), default="")
    reference: Mapped[str] = mapped_column(String(120), default="")
    product: Mapped[str] = mapped_column(String(100), default="")
    system_name: Mapped[str] = mapped_column(String(180), default="")
    fault: Mapped[str] = mapped_column(Text, default="")
    module: Mapped[str] = mapped_column(String(180), default="")
    diagnosis: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    recommendation: Mapped[str] = mapped_column(Text, default="")
    work_done: Mapped[str] = mapped_column(Text, default="")
    parts_required: Mapped[str] = mapped_column(Text, default="")
    outcome: Mapped[str] = mapped_column(String(100), default="")
    engineer_notes: Mapped[str] = mapped_column(Text, default="")
    signature: Mapped[str] = mapped_column(String(255), default="")
    approved_by_engineer: Mapped[bool] = mapped_column(Boolean, default=False)
    engineer = relationship("User")

class Photo(Base):
    __tablename__ = "photos"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255), default="")
    phase: Mapped[str] = mapped_column(String(30), default="before")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class LearningRecord(Base):
    __tablename__ = "learning_records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    engineer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    predicted_diagnosis: Mapped[str] = mapped_column(Text, default="")
    predicted_confidence: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_diagnosis: Mapped[str] = mapped_column(Text, default="")
    actual_repair: Mapped[str] = mapped_column(Text, default="")
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    repeat_visit_required: Mapped[bool] = mapped_column(Boolean, default=False)
    remake_or_part_correct: Mapped[str] = mapped_column(String(30), default="Not applicable")
    engineer_rating: Mapped[int] = mapped_column(Integer, default=0)
    engineer_feedback: Mapped[str] = mapped_column(Text, default="")
    anonymised_for_learning: Mapped[bool] = mapped_column(Boolean, default=True)

class Customer(Base):
    __tablename__="customers"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    name: Mapped[str]=mapped_column(String(200),index=True)
    contact_name: Mapped[str]=mapped_column(String(200),default="")
    email: Mapped[str]=mapped_column(String(320),default="")
    phone: Mapped[str]=mapped_column(String(80),default="")
    address: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class WorkOrder(Base):
    __tablename__="work_orders"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    customer_id: Mapped[str|None]=mapped_column(ForeignKey("customers.id"),nullable=True,index=True)
    job_id: Mapped[str|None]=mapped_column(ForeignKey("jobs.id"),nullable=True,index=True)
    assigned_engineer_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    title: Mapped[str]=mapped_column(String(240))
    status: Mapped[str]=mapped_column(String(40),default="New",index=True)
    priority: Mapped[str]=mapped_column(String(30),default="Normal")
    scheduled_for: Mapped[str]=mapped_column(String(80),default="")
    site_reference: Mapped[str]=mapped_column(String(160),default="")
    notes: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

class ApprovalRequest(Base):
    __tablename__="approval_requests"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    job_id: Mapped[str]=mapped_column(ForeignKey("jobs.id"),index=True)
    requested_by_id: Mapped[int]=mapped_column(ForeignKey("users.id"))
    approval_type: Mapped[str]=mapped_column(String(60))
    description: Mapped[str]=mapped_column(Text)
    estimated_cost_pence: Mapped[int]=mapped_column(Integer,default=0)
    status: Mapped[str]=mapped_column(String(30),default="Pending",index=True)
    decision_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True)
    decision_note: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

class Notification(Base):
    __tablename__="notifications"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id"),index=True)
    title: Mapped[str]=mapped_column(String(200))
    body: Mapped[str]=mapped_column(Text,default="")
    read: Mapped[bool]=mapped_column(Boolean,default=False,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"),nullable=True,index=True)
    action: Mapped[str]=mapped_column(String(100),index=True)
    entity_type: Mapped[str]=mapped_column(String(80),default="")
    entity_id: Mapped[str]=mapped_column(String(80),default="")
    detail_json: Mapped[str]=mapped_column(Text,default="{}")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
