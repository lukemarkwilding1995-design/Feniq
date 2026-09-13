import os, json, uuid, secrets
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Header, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Company, User, Job, Photo, LearningRecord, Customer, WorkOrder, ApprovalRequest, Notification, AuditEvent
from .security import hash_password, verify_password, create_token, current_user
from .vision import analyse_image
from .pdf_report import build_report
from .diagnostics import diagnose as run_diagnosis, catalogue as diagnostic_catalogue
from .manufacturer_intelligence import manufacturers as manufacturer_list, systems as manufacturer_systems, route as manufacturer_route
from .knowledge_library import list_guides, get_guide, search_guides, guides_for_diagnosis
from .learning_engine import metrics as learning_metrics, patterns as learning_patterns
from .commercial_ops import dashboard as commercial_dashboard
from .audit import log as audit_log
from .snapshots import capture as capture_snapshot, original as original_snapshot, serialise as snapshot_json
from .migrations import require_current
from .workflow_policy import scope as approval_scope, transition as check_transition

BASE = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE/"uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
MAX_UPLOAD = int(os.getenv("MAX_UPLOAD_MB","10"))*1024*1024

app = FastAPI(title="FenIQ", version="1.0-demo")
app.mount("/static", StaticFiles(directory=BASE/"static"), name="static")


@app.on_event("startup")
def startup():
    require_current(engine)

def user_dep(authorization: str = Header(default=""), db: Session = Depends(get_db)):
    return current_user(db, authorization)

def require_admin(user: User = Depends(user_dep)):
    if user.role != "admin":
        raise HTTPException(403, "Admin role required")
    return user

@app.get("/")
def home():
    return FileResponse(BASE/"static"/"index.html")

class AccountInput(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def trim_fields(cls, value, info):
        if isinstance(value, str) and info.field_name != "password":
            value = value.strip()
            if not value:
                raise ValueError("This field is required")
            if info.field_name == "email" and ("@" not in value or "." not in value.split("@")[-1]):
                raise ValueError("Enter a valid email address")
        return value

class CompanyRegister(AccountInput):
    company_name: str
    admin_name: str
    email: str
    password: str

class JoinCompany(AccountInput):
    invite_code: str
    name: str
    email: str
    password: str

class Login(AccountInput):
    email: str
    password: str

class JobIn(BaseModel):
    customer: str=Field(min_length=1, max_length=255)
    reference: str=""
    product: str=""
    system_name: str=""
    fault: str=""
    module: str=""
    diagnosis: str=""
    confidence: int=0
    evidence: list[str]=Field(default_factory=list)
    diagnostic_answers: dict | None=None
    work_order_id: str | None=None
    recommendation: str=""
    work_done: str=""
    parts_required: str=""
    outcome: str=""
    engineer_notes: str=""
    signature: str=""
    approved_by_engineer: bool=False

@app.post("/api/register-company")
def register_company(data: CompanyRegister, db: Session = Depends(get_db)):
    if len(data.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
    if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,"Email already in use")
    if db.scalar(select(Company).where(Company.name==data.company_name.strip())): raise HTTPException(409,"Company already exists")
    company=Company(name=data.company_name.strip(),invite_code=secrets.token_urlsafe(9))
    db.add(company); db.flush()
    user=User(company_id=company.id,email=data.email.lower(),name=data.admin_name.strip(),password_hash=hash_password(data.password),role="admin")
    db.add(user); db.commit(); db.refresh(user)
    return {"token":create_token(user),"user":user_json(user),"invite_code":company.invite_code}

@app.post("/api/join-company")
def join_company(data: JoinCompany, db: Session = Depends(get_db)):
    if len(data.password)<8: raise HTTPException(400,"Password must be at least 8 characters")
    company=db.scalar(select(Company).where(Company.invite_code==data.invite_code))
    if not company: raise HTTPException(404,"Invite code not found")
    if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,"Email already in use")
    user=User(company_id=company.id,email=data.email.lower(),name=data.name.strip(),password_hash=hash_password(data.password),role="engineer")
    db.add(user); db.commit(); db.refresh(user)
    return {"token":create_token(user),"user":user_json(user)}

@app.post("/api/login")
def login(data: Login, db: Session = Depends(get_db)):
    user=db.scalar(select(User).where(User.email==data.email.lower()))
    if not user or not user.active or not verify_password(data.password,user.password_hash): raise HTTPException(401,"Invalid login")
    return {"token":create_token(user),"user":user_json(user)}

def user_json(u):
    return {"id":u.id,"email":u.email,"name":u.name,"role":u.role,"company_id":u.company_id,"company":u.company.name if u.company else ""}

@app.get("/api/me")
def me(user: User = Depends(user_dep)):
    return user_json(user)

@app.get("/api/company")
def company(user: User = Depends(user_dep), db: Session = Depends(get_db)):
    c=db.get(Company,user.company_id)
    return {"id":c.id,"name":c.name,"invite_code":c.invite_code if user.role=="admin" else None}

@app.get("/api/company/users")
def company_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    rows=db.scalars(select(User).where(User.company_id==admin.company_id).order_by(User.name)).all()
    return [user_json(x) for x in rows]




@app.get("/api/guides")
def guides(module: str|None=None, system: str|None=None, product: str|None=None, user: User = Depends(user_dep)):
    return list_guides(module=module,system=system,product=product)

@app.get("/api/guides/search")
def guides_search(q: str, user: User = Depends(user_dep)):
    return search_guides(q)

@app.get("/api/guides/{guide_id}")
def guide(guide_id: str, user: User = Depends(user_dep)):
    g=get_guide(guide_id)
    if not g: raise HTTPException(404,"Guide not found")
    return g

@app.get("/api/diagnostics/{module_id}/guides")
def diagnosis_guides(module_id: str, system: str|None=None, user: User = Depends(user_dep)):
    return guides_for_diagnosis(module_id,system)




@app.get("/api/health")
def health():
    return {"status":"ok","product":"FenIQ","release":"V11 Launch Candidate"}

@app.get("/api/audit")
def audit_events(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Admin required")
    return db.scalars(select(AuditEvent).where(AuditEvent.company_id==user.company_id).order_by(AuditEvent.created_at.desc()).limit(250)).all()

@app.get("/api/permissions")
def permissions(user:User=Depends(user_dep)):
    if user.role=="admin":
        return {"role":"admin","permissions":["company.read","users.read","jobs.all","work_orders.manage","approvals.decide","audit.read","analytics.company"]}
    return {"role":"engineer","permissions":["jobs.own","work_orders.assigned","approvals.request","learning.submit","guides.read","diagnostics.run"]}

class CustomerIn(BaseModel):
    name:str=Field(min_length=1, max_length=200)
    contact_name:str=""
    email:str=""
    phone:str=""
    address:str=""

class WorkOrderIn(BaseModel):
    title:str=Field(min_length=1, max_length=240)
    customer_id:str|None=None
    job_id:str|None=None
    assigned_engineer_id:int|None=None
    priority:Literal["Low", "Normal", "High", "Urgent"]="Normal"
    scheduled_for:str=""
    site_reference:str=""
    notes:str=""

class ApprovalIn(BaseModel):
    job_id:str
    approval_type:str=Field(min_length=1, max_length=60)
    description:str=Field(min_length=1)
    estimated_cost_pence:int=Field(default=0, ge=0)

class ApprovalDecisionIn(BaseModel):
    status:str
    decision_note:str=""

@app.get("/api/commercial/dashboard")
def commercial(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Company commercial dashboard requires admin access")
    return commercial_dashboard(db,user.company_id)

@app.get("/api/customers")
def customers(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    return db.scalars(select(Customer).where(Customer.company_id==user.company_id).order_by(Customer.name)).all()

@app.post("/api/customers")
def create_customer(data:CustomerIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    c=Customer(id=str(uuid.uuid4()),company_id=user.company_id,**data.model_dump());db.add(c);db.commit();db.refresh(c);return c

@app.get("/api/work-orders")
def work_orders(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    q=select(WorkOrder).where(WorkOrder.company_id==user.company_id)
    if user.role!="admin": q=q.where(WorkOrder.assigned_engineer_id==user.id)
    return db.scalars(q.order_by(WorkOrder.created_at.desc())).all()

@app.post("/api/work-orders")
def create_work_order(data:WorkOrderIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Admin required")
    validate_work_order(data, user, db)
    w=WorkOrder(id=str(uuid.uuid4()),company_id=user.company_id,status="Scheduled" if data.scheduled_for else "New",**data.model_dump())
    db.add(w)
    if w.assigned_engineer_id:
        db.add(Notification(id=str(uuid.uuid4()),company_id=user.company_id,user_id=w.assigned_engineer_id,title="New work order assigned",body=w.title))
    audit_log(db,user.company_id,user.id,"work_order.created","work_order",w.id)
    db.commit();db.refresh(w);return w

@app.patch("/api/work-orders/{work_order_id}/status")
def update_work_order(work_order_id:str,status:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    w=db.get(WorkOrder,work_order_id)
    if not w or w.company_id!=user.company_id: raise HTTPException(404,"Work order not found")
    if user.role!="admin" and w.assigned_engineer_id!=user.id: raise HTTPException(403,"Not assigned to this work order")
    check_transition(db,w,status,user)
    w.status=status
    audit_log(db,user.company_id,user.id,"work_order.status","work_order",w.id,{"status":status})
    db.commit();return {"ok":True}

@app.get("/api/approvals")
def approvals(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    q=select(ApprovalRequest).where(ApprovalRequest.company_id==user.company_id)
    if user.role!="admin": q=q.where(ApprovalRequest.requested_by_id==user.id)
    rows=db.scalars(q.order_by(ApprovalRequest.created_at.desc())).all()
    return [{"id":a.id,"job_id":a.job_id,"approval_type":a.approval_type,"description":a.description,
             "estimated_cost_pence":a.estimated_cost_pence,"status":a.status,"decision_note":a.decision_note,
             "created_at":a.created_at,"scope_current":bool(a.scope_sha256) and a.scope_sha256==approval_scope(db.get(Job,a.job_id)) if db.get(Job,a.job_id) else False}
            for a in rows]

@app.post("/api/approvals")
def request_approval(data:ApprovalIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    job=db.get(Job,data.job_id);check_job(job,user)
    a=ApprovalRequest(id=str(uuid.uuid4()),company_id=user.company_id,requested_by_id=user.id,scope_sha256=approval_scope(job),**data.model_dump())
    db.add(a)
    admins=db.scalars(select(User).where(User.company_id==user.company_id,User.role=="admin",User.active==True)).all()
    for admin in admins:
        db.add(Notification(id=str(uuid.uuid4()),company_id=user.company_id,user_id=admin.id,title=f"Approval required: {data.approval_type}",body=data.description))
    db.commit();db.refresh(a);return a

@app.post("/api/approvals/{approval_id}/decision")
def decide_approval(approval_id:str,data:ApprovalDecisionIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    if user.role!="admin": raise HTTPException(403,"Admin required")
    a=db.get(ApprovalRequest,approval_id)
    if not a or a.company_id!=user.company_id: raise HTTPException(404,"Approval not found")
    if data.status not in ["Approved","Rejected"]: raise HTTPException(400,"Decision must be Approved or Rejected")
    if a.status != "Pending": raise HTTPException(409,"This request already has a decision")
    job=db.get(Job,a.job_id)
    if data.status=="Approved":
        if not job or not job.approved_by_engineer: raise HTTPException(409,"Engineer review is required before authorising this request")
        if not a.scope_sha256 or a.scope_sha256!=approval_scope(job): raise HTTPException(409,"The inspection findings changed or this is a legacy request. Reject it and submit a new request for the current findings")
    conditions=[ApprovalRequest.id==a.id,ApprovalRequest.status=="Pending"]
    if data.status=="Approved":
        conditions.append(select(Job.id).where(Job.id==a.job_id,Job.updated_at==job.updated_at,Job.approved_by_engineer==True).exists())
    result=db.execute(update(ApprovalRequest).where(*conditions).values(status=data.status,decision_by_id=user.id,decision_note=data.decision_note).execution_options(synchronize_session=False))
    if result.rowcount!=1: raise HTTPException(409,"The request or inspection changed. Refresh before deciding")
    audit_log(db,user.company_id,user.id,"approval.decided","approval",a.id,{"status":data.status})
    db.add(Notification(id=str(uuid.uuid4()),company_id=user.company_id,user_id=a.requested_by_id,title=f"{a.approval_type}: {data.status}",body=data.decision_note))
    db.commit();return {"ok":True}

@app.get("/api/notifications")
def notifications(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    return db.scalars(select(Notification).where(Notification.user_id==user.id).order_by(Notification.created_at.desc()).limit(50)).all()

@app.post("/api/notifications/{notification_id}/read")
def read_notification(notification_id:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    n=db.get(Notification,notification_id)
    if not n or n.user_id!=user.id: raise HTTPException(404,"Notification not found")
    n.read=True;db.commit();return {"ok":True}

@app.get("/api/plans")
def plans():
    return [
      {"id":"engineer","name":"Engineer","monthly_gbp":29,"description":"Individual engineer workspace"},
      {"id":"pro","name":"Pro","monthly_gbp":99,"description":"Small installer/team"},
      {"id":"business","name":"Business","monthly_gbp":299,"description":"Company operations and analytics"},
      {"id":"manufacturer","name":"Manufacturer","monthly_gbp":999,"description":"Manufacturer intelligence starting tier"}
    ]

class LearningIn(BaseModel):
    confirmed_diagnosis: str
    actual_repair: str
    resolved: bool
    repeat_visit_required: bool=False
    remake_or_part_correct: str="Not applicable"
    engineer_rating: int=0
    engineer_feedback: str=""
    anonymised_for_learning: bool=True

@app.post("/api/jobs/{job_id}/learning")
def save_learning(job_id: str, data: LearningIn, user: User = Depends(user_dep), db: Session = Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    if job.engineer_id!=user.id and user.role!="admin":
        raise HTTPException(403,"Only the assigned engineer or admin can confirm the repair outcome")
    existing=db.scalar(select(LearningRecord).where(LearningRecord.job_id==job.id))
    if existing:
        record=existing
    else:
        record=LearningRecord(id=str(uuid.uuid4()),job_id=job.id,company_id=job.company_id,engineer_id=job.engineer_id)
        db.add(record)
    if not existing:
        snapshot=capture_snapshot(db,job,user.id)
        predicted=json.loads(snapshot.payload_json)
        record.predicted_diagnosis=predicted["diagnosis"]
        record.predicted_confidence=predicted["confidence"]
    record.confirmed_diagnosis=data.confirmed_diagnosis
    record.actual_repair=data.actual_repair
    record.resolved=data.resolved
    record.repeat_visit_required=data.repeat_visit_required
    record.remake_or_part_correct=data.remake_or_part_correct
    record.engineer_rating=max(0,min(5,data.engineer_rating))
    record.engineer_feedback=data.engineer_feedback
    record.anonymised_for_learning=data.anonymised_for_learning
    db.commit()
    return {"ok":True,"record_id":record.id}

@app.get("/api/learning/metrics")
def get_learning_metrics(user: User = Depends(user_dep), db: Session = Depends(get_db)):
    return learning_metrics(db,user.company_id,None if user.role=="admin" else user.id)

@app.get("/api/learning/patterns")
def get_learning_patterns(user: User = Depends(user_dep), db: Session = Depends(get_db)):
    return learning_patterns(db,user.company_id,None if user.role=="admin" else user.id)

class ManufacturerRouteIn(BaseModel):
    manufacturer_id: str
    system_id: str
    symptom_text: str=""

@app.get("/api/manufacturers")
def get_manufacturers(user: User = Depends(user_dep)):
    return manufacturer_list()

@app.get("/api/manufacturer-systems")
def get_manufacturer_systems(manufacturer_id: str|None=None, user: User = Depends(user_dep)):
    return manufacturer_systems(manufacturer_id)

@app.post("/api/manufacturer-route")
def route_manufacturer(data: ManufacturerRouteIn, user: User = Depends(user_dep)):
    result=manufacturer_route(data.manufacturer_id,data.system_id,data.symptom_text)
    if result.get("status")=="not_found":
        raise HTTPException(404,"Manufacturer/system not found")
    return result

class DiagnoseIn(BaseModel):
    module_id: str
    answers: dict

@app.get("/api/diagnostics/catalogue")
def diagnostics_catalogue(user: User = Depends(user_dep)):
    return diagnostic_catalogue()

@app.post("/api/diagnostics/run")
def diagnostics_run(data: DiagnoseIn, user: User = Depends(user_dep)):
    try:
        validate_answers(data.module_id, data.answers)
        return run_diagnosis(data.module_id, data.answers)
    except KeyError:
        raise HTTPException(404, "Diagnostic module not found")

@app.post("/api/jobs")
def create_job(data: JobIn, user: User = Depends(user_dep), db: Session = Depends(get_db)):
    apply_diagnosis(data)
    work_order = None
    if data.work_order_id:
        work_order = db.get(WorkOrder, data.work_order_id)
        if not work_order or work_order.company_id != user.company_id: raise HTTPException(404,"Work order not found")
        if user.role != "admin" and work_order.assigned_engineer_id != user.id: raise HTTPException(403,"Work order is not assigned to you")
        if work_order.job_id: raise HTTPException(409,"This work order already has an inspection")
        if work_order.status in {"Complete","Cancelled"}: raise HTTPException(409,"An administrator must reopen this work order before starting an inspection")
    job=Job(
        id=str(uuid.uuid4()), company_id=user.company_id, engineer_id=(work_order.assigned_engineer_id if work_order and work_order.assigned_engineer_id else user.id),
        customer=data.customer,reference=data.reference,product=data.product,system_name=data.system_name,
        fault=data.fault,module=data.module,diagnosis=data.diagnosis,confidence=max(0,min(100,data.confidence)),
        evidence_json=json.dumps(data.evidence),recommendation=data.recommendation,work_done=data.work_done,
        parts_required=data.parts_required,outcome=data.outcome,engineer_notes=data.engineer_notes,
        signature=data.signature,approved_by_engineer=data.approved_by_engineer
    )
    db.add(job);db.flush()
    capture_snapshot(db,job,user.id,data.diagnostic_answers,"server_diagnosis" if data.diagnostic_answers is not None else "engineer_entered")
    if work_order:
        work_order.job_id=job.id
        work_order.status="In Progress"
    audit_log(db,user.company_id,user.id,"inspection.created","job",job.id)
    db.commit();db.refresh(job)
    return job_json(job, db)

@app.get("/api/jobs")
def jobs(user: User = Depends(user_dep), db: Session = Depends(get_db)):
    stmt=select(Job).where(Job.company_id==user.company_id)
    if user.role!="admin": stmt=stmt.where(Job.engineer_id==user.id)
    rows=db.scalars(stmt.order_by(Job.created_at.desc())).all()
    return [job_json(x,db) for x in rows]

@app.get("/api/jobs/{job_id}")
def one_job(job_id: str, user: User = Depends(user_dep), db: Session = Depends(get_db)):
    job=db.get(Job,job_id); check_job(job,user)
    return job_json(job,db)

@app.patch("/api/jobs/{job_id}/approve")
def approve(job_id: str, user: User = Depends(user_dep), db: Session = Depends(get_db)):
    job=db.get(Job,job_id); check_job(job,user)
    if job.engineer_id!=user.id and user.role!="admin": raise HTTPException(403,"Only job engineer/admin can approve")
    job.approved_by_engineer=True
    audit_log(db,user.company_id,user.id,"inspection.reviewed","job",job.id)
    db.commit()
    return {"ok":True}

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str, user: User = Depends(user_dep), db: Session = Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    if user.role!="admin" and job.engineer_id!=user.id: raise HTTPException(403)
    from .models import DiagnosticSnapshot
    from .passports import PassportInspection
    for model in (DiagnosticSnapshot,LearningRecord,WorkOrder,ApprovalRequest,PassportInspection):
        if db.scalar(select(model.id).where(model.job_id==job.id)):
            raise HTTPException(409,"This inspection has retained history or linked work. Deletion is blocked; archival is not yet available")
    photos=db.scalars(select(Photo).where(Photo.job_id==job.id)).all()
    for p in photos:
        try:(UPLOAD_DIR/p.filename).unlink()
        except FileNotFoundError:pass
        db.delete(p)
    db.delete(job);db.commit();return {"ok":True}

def check_job(job,user):
    if not job: raise HTTPException(404,"Job not found")
    if job.company_id!=user.company_id: raise HTTPException(403,"Wrong company")
    if user.role!="admin" and job.engineer_id!=user.id: raise HTTPException(403,"Not your job")

def job_json(j,db):
    photos=db.scalars(select(Photo).where(Photo.job_id==j.id).order_by(Photo.created_at)).all()
    return {
        "id":j.id,"created_at":j.created_at.isoformat(),"customer":j.customer,"reference":j.reference,
        "product":j.product,"system_name":j.system_name,"fault":j.fault,"module":j.module,
        "diagnosis":j.diagnosis,"confidence":j.confidence,"evidence":json.loads(j.evidence_json or "[]"),
        "recommendation":j.recommendation,"work_done":j.work_done,"parts_required":j.parts_required,
        "outcome":j.outcome,"engineer_notes":j.engineer_notes,"signature":j.signature,
        "approved_by_engineer":j.approved_by_engineer,
        "engineer":{"id":j.engineer.id,"name":j.engineer.name},
        "photos":[{"id":p.id,"url":f"/api/photos/{p.id}/content","phase":p.phase,"name":p.original_name} for p in photos]
    }

@app.post("/api/jobs/{job_id}/photos")
async def upload_photo(job_id:str, phase:str=Form("before"), file:UploadFile=File(...), user:User=Depends(user_dep), db:Session=Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    ext=Path(file.filename or "").suffix.lower()
    if ext not in {".jpg",".jpeg",".png",".webp"}: raise HTTPException(400,"Use JPG, PNG or WEBP")
    if phase not in {"before","after"}: raise HTTPException(400,"Invalid photo phase")
    data=await file.read(MAX_UPLOAD+1)
    if len(data)>MAX_UPLOAD: raise HTTPException(400,"Image exceeds upload limit")
    try:
        with Image.open(BytesIO(data)) as img:
            if img.width * img.height > 25_000_000: raise ValueError("Image too large")
            img.verify()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(400,"Upload a valid image up to 25 megapixels")
    pid=str(uuid.uuid4());filename=pid+ext
    (UPLOAD_DIR/filename).write_bytes(data)
    p=Photo(id=pid,job_id=job.id,company_id=user.company_id,filename=filename,original_name=file.filename or "",phase=phase)
    db.add(p);db.commit()
    return {"id":pid,"url":f"/api/photos/{pid}/content"}

@app.post("/api/photos/{photo_id}/analyse")
def analyse_photo(photo_id:str, user:User=Depends(user_dep), db:Session=Depends(get_db)):
    p=db.get(Photo,photo_id)
    if not p or p.company_id!=user.company_id: raise HTTPException(404,"Photo not found")
    job=db.get(Job,p.job_id);check_job(job,user)
    return analyse_image(UPLOAD_DIR/p.filename)

@app.get("/api/jobs/{job_id}/report.pdf")
def pdf(job_id:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    photos=db.scalars(select(Photo).where(Photo.job_id==job.id)).all()
    buf=build_report(job,job.engineer.name,photos,UPLOAD_DIR)
    return StreamingResponse(buf,media_type="application/pdf",headers={"Content-Disposition":f'inline; filename="FenIQ-{job.id[:8]}.pdf"'})

@app.get("/api/analytics")
def analytics(user:User=Depends(user_dep),db:Session=Depends(get_db)):
    stmt=select(Job).where(Job.company_id==user.company_id)
    if user.role!="admin": stmt=stmt.where(Job.engineer_id==user.id)
    rows=db.scalars(stmt).all()
    counts_diag={};counts_prod={}
    for j in rows:
        counts_diag[j.diagnosis]=counts_diag.get(j.diagnosis,0)+1
        counts_prod[j.product]=counts_prod.get(j.product,0)+1
    top=lambda d:max(d.items(),key=lambda x:x[1]) if d else None
    return {
        "total":len(rows),
        "resolved":sum("Resolved" in (j.outcome or "") for j in rows),
        "remakes":sum("Remake" in (j.outcome or "") for j in rows),
        "top_diagnosis":top(counts_diag),
        "top_product":top(counts_prod)
    }


def validate_answers(module_id, answers):
    from .diagnostics import MODULES
    import math
    module = MODULES.get(module_id)
    if not module: raise KeyError(module_id)
    for check in module["checks"]:
        value = answers.get(check["key"])
        if value is None:
            if check.get("required"): raise HTTPException(422, f"Complete: {check['label']}")
            continue
        valid = True
        if check["type"] == "bool": valid = type(value) is bool
        elif check["type"] == "number": valid = type(value) in (int,float) and math.isfinite(value) and value >= 0
        elif check["type"] == "choice": valid = value in check["options"]
        if not valid: raise HTTPException(422, f"Invalid answer: {check['label']}")

def apply_diagnosis(data):
    if data.diagnostic_answers is None: return
    try:
        validate_answers(data.module, data.diagnostic_answers)
        result = run_diagnosis(data.module, data.diagnostic_answers)
    except KeyError:
        raise HTTPException(422,"Unknown diagnostic module")
    data.diagnosis=result["title"]
    data.confidence=result["confidence"]
    from .diagnostics import MODULES
    recorded=[]
    for check in MODULES[data.module]["checks"]:
        if check["key"] in data.diagnostic_answers:
            value=data.diagnostic_answers[check["key"]]
            if type(value) is bool: value="Yes" if value else "No"
            recorded.append(f"{check['label']}: {value}{' '+check['unit'] if check.get('unit') else ''}")
    data.evidence=result["evidence"]+recorded
    data.recommendation=result["recommendation"]

def validate_work_order(data,user,db):
    for model, identifier in [(Customer,data.customer_id),(Job,data.job_id),(User,data.assigned_engineer_id)]:
        if identifier is not None:
            entity=db.get(model,identifier)
            if not entity or entity.company_id != user.company_id:
                raise HTTPException(422,"Customer, inspection and engineer must belong to your company")
            if model is User and not entity.active: raise HTTPException(422,"Engineer is inactive")
    if data.job_id:
        job=db.get(Job,data.job_id)
        if data.assigned_engineer_id!=job.engineer_id:
            raise HTTPException(422,"The visit engineer must match the linked inspection engineer")
    if data.scheduled_for:
        from datetime import datetime
        try: datetime.fromisoformat(data.scheduled_for)
        except ValueError: raise HTTPException(422,"Enter a valid scheduled date and time")

@app.patch("/api/work-orders/{work_order_id}")
def edit_work_order(work_order_id:str,data:WorkOrderIn,user:User=Depends(require_admin),db:Session=Depends(get_db)):
    w=db.get(WorkOrder,work_order_id)
    if not w or w.company_id!=user.company_id: raise HTTPException(404,"Work order not found")
    if w.status in {"Complete","Cancelled"}: raise HTTPException(409,"Reopen this work order before editing it")
    if w.job_id and data.job_id!=w.job_id: raise HTTPException(409,"An existing inspection link cannot be replaced or removed")
    validate_work_order(data,user,db)
    for key,value in data.model_dump().items(): setattr(w,key,value)
    audit_log(db,user.company_id,user.id,"work_order.updated","work_order",w.id)
    db.commit();db.refresh(w);return w

@app.patch("/api/jobs/{job_id}")
def edit_job(job_id:str,data:JobIn,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    if db.scalar(select(WorkOrder.id).where(WorkOrder.job_id==job.id,WorkOrder.status=="Complete")):
        raise HTTPException(409,"An administrator must reopen the completed visit before editing its inspection")
    old_scope=approval_scope(job)
    old_service=(job.work_done,job.outcome,job.signature,job.engineer_notes)
    capture_snapshot(db,job,user.id)
    apply_diagnosis(data)
    values=data.model_dump(exclude={"evidence","diagnostic_answers","work_order_id"})
    for key,value in values.items(): setattr(job,key,value)
    job.evidence_json=json.dumps(data.evidence)
    if old_scope!=approval_scope(job) or old_service!=(job.work_done,job.outcome,job.signature,job.engineer_notes):
        job.approved_by_engineer=False
    audit_log(db,user.company_id,user.id,"inspection.updated","job",job.id)
    db.commit();db.refresh(job);return job_json(job,db)

@app.get("/api/jobs/{job_id}/learning")
def read_learning(job_id:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    return db.scalar(select(LearningRecord).where(LearningRecord.job_id==job_id))

@app.get("/api/jobs/{job_id}/diagnostic-snapshot")
def read_diagnostic_snapshot(job_id:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    job=db.get(Job,job_id);check_job(job,user)
    return snapshot_json(original_snapshot(db,job_id))

@app.get("/api/photos/{photo_id}/content")
def photo_content(photo_id:str,user:User=Depends(user_dep),db:Session=Depends(get_db)):
    photo=db.get(Photo,photo_id)
    if not photo: raise HTTPException(404,"Photo not found")
    check_job(db.get(Job,photo.job_id),user)
    path=UPLOAD_DIR/photo.filename
    if not path.is_file(): raise HTTPException(404,"Photo file not found")
    return FileResponse(path,headers={"Cache-Control":"private, no-store"})

@app.get("/api/config")
def client_config():
    return {"demo_enabled":os.getenv("FENIQ_DEMO","0")=="1","vision_enabled":bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_VISION_MODEL"))}

@app.get("/api/documents")
def technical_documents(q:str="",category:str="",system:str="",manufacturer:str="",user:User=Depends(user_dep)):
    from .documents import catalogue
    return catalogue(user.company_id,q,category,system,manufacturer)

@app.get("/api/documents/{document_id}/file")
def technical_document_file(document_id:str,user:User=Depends(user_dep)):
    from .documents import document_file
    path,doc=document_file(user.company_id,document_id)
    media_type={'.pdf':'application/pdf','.mp4':'video/mp4','.mov':'video/quicktime','.webm':'video/webm'}.get(path.suffix.lower(),'application/octet-stream')
    return FileResponse(path,media_type=media_type,filename=doc['source_filename'],content_disposition_type="inline",headers={"Cache-Control":"private, no-store"})

@app.get("/api/documents/{document_id}/pages/{page_number}")
def technical_document_page(document_id:str,page_number:int,user:User=Depends(user_dep)):
    from .documents import page_image
    return Response(page_image(user.company_id,document_id,page_number),media_type='image/png',headers={"Cache-Control":"private, no-store"})

@app.post("/api/demo")
def demo_session(role:Literal["admin","engineer"]="admin",db:Session=Depends(get_db)):
    if os.getenv("FENIQ_DEMO","0")!="1": raise HTTPException(404,"Not found")
    from .demo import create_demo
    demo_user=create_demo(db,role)
    return {"token":create_token(demo_user),"user":user_json(demo_user)}

from .passports import register as register_passports
register_passports(app,user_dep,check_job)
