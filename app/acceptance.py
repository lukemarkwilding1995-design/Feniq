"""Append-only customer acceptance bound to an exact report state."""
import hashlib, json, uuid
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from .audit import log as audit_log
from .db import Base, get_db
from .models import Job, Photo, User, now
from .outcomes import OutcomeRevision

class CustomerAcceptance(Base):
    __tablename__="customer_acceptances"
    __table_args__=(UniqueConstraint("job_id","version",name="uq_customer_acceptance_version"),)
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    job_id:Mapped[str]=mapped_column(ForeignKey("jobs.id"),index=True)
    company_id:Mapped[int]=mapped_column(ForeignKey("companies.id"),index=True)
    version:Mapped[int]=mapped_column(Integer)
    actor_id:Mapped[int]=mapped_column(ForeignKey("users.id"))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    report_sha256:Mapped[str]=mapped_column(String(64))
    payload_json:Mapped[str]=mapped_column(Text)
    sha256:Mapped[str]=mapped_column(String(64))

class AcceptanceIn(BaseModel):
    expected_version:int=Field(ge=0)
    status:Literal["Accepted","Declined","Customer unavailable"]
    customer_name:str=Field(default="",max_length=255)
    customer_confirmed:bool=False
    note:str=Field(default="",max_length=2000)
    change_reason:str=Field(default="",max_length=2000)

def report_scope(db,job):
    outcome=db.scalar(select(OutcomeRevision).where(OutcomeRevision.job_id==job.id).order_by(OutcomeRevision.version.desc()))
    payload={key:getattr(job,key) for key in ("customer","reference","product","system_name","fault","diagnosis","confidence","evidence_json","recommendation","work_done","parts_required","outcome","engineer_notes","signature","approved_by_engineer","citation_version")}
    payload["outcome_sha256"]=outcome.sha256 if outcome else None
    photos=db.scalars(select(Photo).where(Photo.job_id==job.id).order_by(Photo.id)).all()
    payload["photos"]=[{"id":photo.id,"filename":photo.filename,"original_name":photo.original_name,"phase":photo.phase,"created_at":photo.created_at.isoformat()} for photo in photos]
    encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(encoded.encode()).hexdigest()

def rows(db,job):
    return db.scalars(select(CustomerAcceptance).where(CustomerAcceptance.job_id==job.id,CustomerAcceptance.company_id==job.company_id).order_by(CustomerAcceptance.version)).all()

def serialise(row,current_scope):
    bound=f"{row.report_sha256}\n{row.payload_json}"
    return {"version":row.version,"created_at":row.created_at,"actor_id":row.actor_id,"report_sha256":row.report_sha256,"report_current":row.report_sha256==current_scope,"payload":json.loads(row.payload_json),"sha256":row.sha256,"integrity_valid":hashlib.sha256(bound.encode()).hexdigest()==row.sha256}

def register(app,user_dep):
    router=APIRouter()
    def job_for(db,job_id,user):
        job=db.get(Job,job_id)
        if not job: raise HTTPException(404,"Job not found")
        if job.company_id!=user.company_id: raise HTTPException(403,"Wrong company")
        if user.role!="admin" and job.engineer_id!=user.id: raise HTTPException(403,"Not your job")
        return job
    @router.get("/api/jobs/{job_id}/acceptance-history")
    def history(job_id:str,response:Response,user:User=Depends(user_dep),db:Session=Depends(get_db)):
        job=job_for(db,job_id,user);response.headers["Cache-Control"]="private, no-store";scope=report_scope(db,job)
        return [serialise(row,scope) for row in rows(db,job)]
    @router.post("/api/jobs/{job_id}/acceptance-history")
    def record(job_id:str,data:AcceptanceIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
        job=job_for(db,job_id,user)
        if not job.approved_by_engineer: raise HTTPException(409,"Engineer review is required before customer acceptance")
        history=rows(db,job)
        if data.expected_version!=len(history): raise HTTPException(409,"Customer acceptance changed; reload the inspection")
        name,note,reason=data.customer_name.strip(),data.note.strip(),data.change_reason.strip()
        if data.status!="Customer unavailable" and not name: raise HTTPException(422,"Record the customer's name")
        if data.status!="Customer unavailable" and not data.customer_confirmed: raise HTTPException(422,"Confirm the customer made this acceptance decision")
        if history and len(reason)<5: raise HTTPException(422,"Explain why the acceptance record is being corrected")
        payload={"status":data.status,"customer_name":name,"customer_confirmed":data.customer_confirmed,"note":note,"change_reason":reason}
        encoded=json.dumps(payload,sort_keys=True,separators=(",",":"),ensure_ascii=False);scope=report_scope(db,job)
        bound=f"{scope}\n{encoded}"
        row=CustomerAcceptance(id=str(uuid.uuid4()),job_id=job.id,company_id=job.company_id,version=len(history)+1,actor_id=user.id,report_sha256=scope,payload_json=encoded,sha256=hashlib.sha256(bound.encode()).hexdigest())
        db.add(row);audit_log(db,user.company_id,user.id,"inspection.customer_acceptance_recorded","job",job.id,{"version":row.version,"status":data.status});db.commit();db.refresh(row)
        return serialise(row,scope)
    app.include_router(router)
