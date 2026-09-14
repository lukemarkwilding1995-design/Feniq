"""Append-only repair outcome revisions; no automatic learning promotion."""
import hashlib,json,uuid
from datetime import datetime
from sqlalchemy import String,Integer,Text,DateTime,ForeignKey,UniqueConstraint,select
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
from .models import now

class OutcomeRevision(Base):
    __tablename__='outcome_revisions'
    __table_args__=(UniqueConstraint('job_id','version',name='uq_outcome_version'),)
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    job_id:Mapped[str]=mapped_column(ForeignKey('jobs.id'),index=True)
    company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'))
    version:Mapped[int]=mapped_column(Integer)
    actor_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    payload_json:Mapped[str]=mapped_column(Text)
    sha256:Mapped[str]=mapped_column(String(64))

def history(db,job):
    return db.scalars(select(OutcomeRevision).where(OutcomeRevision.job_id==job.id,OutcomeRevision.company_id==job.company_id).order_by(OutcomeRevision.version)).all()

def append(db,job,actor,version,payload):
    encoded=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    row=OutcomeRevision(id=str(uuid.uuid4()),job_id=job.id,company_id=job.company_id,version=version,actor_id=actor,payload_json=encoded,sha256=hashlib.sha256(encoded.encode()).hexdigest())
    db.add(row)
    return row

def serialise(row):
    return {'version':row.version,'actor_id':row.actor_id,'created_at':row.created_at,'payload':json.loads(row.payload_json),'sha256':row.sha256,'integrity_valid':hashlib.sha256(row.payload_json.encode()).hexdigest()==row.sha256}
