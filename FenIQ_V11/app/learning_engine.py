from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import LearningRecord, Job

def metrics(db: Session, company_id: int, engineer_id=None):
    stmt=select(LearningRecord).where(LearningRecord.company_id==company_id)
    if engineer_id: stmt=stmt.where(LearningRecord.engineer_id==engineer_id)
    rows=db.scalars(stmt).all()
    total=len(rows)
    exact=sum(1 for r in rows if norm(r.predicted_diagnosis)==norm(r.confirmed_diagnosis) and r.confirmed_diagnosis)
    resolved=sum(1 for r in rows if r.resolved)
    repeats=sum(1 for r in rows if r.repeat_visit_required)
    rated=[r.engineer_rating for r in rows if r.engineer_rating>0]
    return {
      "records":total,
      "diagnosis_confirmation_rate":round(exact/total*100,1) if total else 0,
      "repair_resolution_rate":round(resolved/total*100,1) if total else 0,
      "repeat_visit_rate":round(repeats/total*100,1) if total else 0,
      "average_engineer_rating":round(sum(rated)/len(rated),2) if rated else 0,
      "learning_status":"baseline" if total<50 else "early_dataset" if total<250 else "growing_dataset"
    }

def patterns(db: Session, company_id: int):
    rows=db.scalars(select(LearningRecord).where(LearningRecord.company_id==company_id)).all()
    groups=defaultdict(lambda:{"count":0,"resolved":0,"confirmed":0})
    for r in rows:
        key=r.predicted_diagnosis or "Unknown"
        g=groups[key];g["count"]+=1;g["resolved"]+=int(r.resolved)
        g["confirmed"]+=int(norm(r.predicted_diagnosis)==norm(r.confirmed_diagnosis) and bool(r.confirmed_diagnosis))
    out=[]
    for diagnosis,g in groups.items():
        out.append({
          "predicted_diagnosis":diagnosis,"cases":g["count"],
          "confirmation_rate":round(g["confirmed"]/g["count"]*100,1),
          "resolution_rate":round(g["resolved"]/g["count"]*100,1)
        })
    return sorted(out,key=lambda x:-x["cases"])

def norm(s):
    return " ".join((s or "").lower().split())
