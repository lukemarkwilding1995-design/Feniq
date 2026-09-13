"""Opt-in fictional demo workspace. Never enabled by default."""
import secrets
import uuid
from datetime import datetime, timedelta
from sqlalchemy import select
from .models import Company, User, Customer, WorkOrder, Job, LearningRecord, ApprovalRequest, Notification
from .security import hash_password

def create_demo(db, role):
    company=db.scalar(select(Company).where(Company.name=="FenIQ Demo · Northline Windows"))
    if company:
        return db.scalar(select(User).where(User.company_id==company.id,User.role==role))
    company=Company(name="FenIQ Demo · Northline Windows",invite_code=secrets.token_urlsafe(12))
    db.add(company);db.flush()
    users={}
    for r,name in [("admin","Alex Morgan"),("engineer","Jamie Taylor")]:
        u=User(company_id=company.id,name=name,email=f"{r}-{uuid.uuid4().hex}@demo.invalid",role=r,password_hash=hash_password(secrets.token_urlsafe(32)))
        db.add(u);db.flush();users[r]=u
    sites=[("Willow House","18 Willow Lane, Bristol","French Door","Sash alignment / installation geometry requires further correction","Adjusted / Resolved"),
           ("Harbour Apartments","42 Harbour Road, Bristol","Window","Locking point / keep alignment issue","Parts Required"),
           ("Oakfield Studios","7 Oakfield Way, Bath","Sliding Door","Sliding sash alignment / roller-height issue","Further Investigation")]
    for i,(name,address,product,diagnosis,outcome) in enumerate(sites):
        customer=Customer(id=str(uuid.uuid4()),company_id=company.id,name=name,address=address,contact_name=["Sam Parker","Robin Lee","Casey Ellis"][i],email=f"site{i}@example.com",phone="")
        db.add(customer);db.flush()
        job=Job(id=str(uuid.uuid4()),company_id=company.id,engineer_id=users['engineer'].id,customer=name,reference=f"FI-2026-{1041+i}",product=product,system_name="Demo system",fault=["Door catches at the threshold when closing.","Handle is stiff when the window is closed.","Sliding panel is difficult to move."][i],module=["french_door_clearance","locking_camb_keep","sliding_door"][i],diagnosis=diagnosis,confidence=[72,88,62][i],evidence_json='["Fictional demo inspection: operating resistance observed.","Frame and hardware checked by engineer."]',recommendation="Check alignment and repeat the operating test after controlled adjustment.",work_done="Alignment checked and controlled adjustment completed." if i==0 else "Initial inspection completed; follow-up required.",outcome=outcome,approved_by_engineer=i==0,signature="Demo customer" if i==0 else "",created_at=datetime.now()-timedelta(days=i))
        db.add(job);db.flush()
        order=WorkOrder(id=str(uuid.uuid4()),company_id=company.id,customer_id=customer.id,job_id=job.id if i<2 else None,assigned_engineer_id=users['engineer'].id,title=["French door service","Replace window keep","Sliding door inspection"][i],status=["Complete","Awaiting Approval","Scheduled"][i],priority=["Normal","High","Normal"][i],scheduled_for=(datetime.now()+timedelta(days=i)).replace(hour=9+i,minute=0,second=0,microsecond=0).isoformat(),site_reference=job.reference,notes="Fictional demo appointment. Contact site on arrival.")
        db.add(order)
        if i==0:
            db.add(LearningRecord(id=str(uuid.uuid4()),job_id=job.id,company_id=company.id,engineer_id=users['engineer'].id,predicted_diagnosis=diagnosis,predicted_confidence=72,confirmed_diagnosis=diagnosis,actual_repair=job.work_done,resolved=True,engineer_rating=5))
        if i==1:
            db.add(ApprovalRequest(id=str(uuid.uuid4()),company_id=company.id,job_id=job.id,requested_by_id=users['engineer'].id,approval_type="Replacement part",description="Replacement window keep following alignment checks. Fictional estimate for demonstration.",estimated_cost_pence=4500))
    db.add(Notification(id=str(uuid.uuid4()),company_id=company.id,user_id=users['admin'].id,title="A parts request needs your review",body="Open Approvals to review the Harbour Apartments request."))
    db.add(Notification(id=str(uuid.uuid4()),company_id=company.id,user_id=users['engineer'].id,title="Your next visit is ready",body="Open Schedule to start the Oakfield Studios inspection."))
    db.commit()
    return users[role]
