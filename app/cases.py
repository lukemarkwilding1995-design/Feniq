"""Owned technical investigations with retained history and linked evidence."""
import uuid
from datetime import datetime
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, select, update
from sqlalchemy.orm import Mapped, mapped_column, Session
from .db import Base, get_db
from .models import now, Job, User, Notification
from .passports import ProductPassport, PassportInspection, Trimmed
from .audit import log


class TechnicalCase(Base):
    __tablename__='technical_cases'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True)
    owner_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True)
    passport_id:Mapped[str|None]=mapped_column(ForeignKey('product_passports.id'),nullable=True,index=True)
    job_id:Mapped[str|None]=mapped_column(ForeignKey('jobs.id'),nullable=True,index=True)
    title:Mapped[str]=mapped_column(String(240))
    description:Mapped[str]=mapped_column(Text)
    priority:Mapped[str]=mapped_column(String(20),default='Normal')
    status:Mapped[str]=mapped_column(String(40),default='Open',index=True)
    resolution:Mapped[str]=mapped_column(Text,default='')
    version:Mapped[int]=mapped_column(Integer,default=1)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class CaseEvent(Base):
    __tablename__='case_events'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    case_id:Mapped[str]=mapped_column(ForeignKey('technical_cases.id'),index=True)
    actor_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
    kind:Mapped[str]=mapped_column(String(40))
    note:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class CaseIn(Trimmed):
    title:str=Field(min_length=1,max_length=240)
    description:str=Field(min_length=1,max_length=10000)
    priority:Literal['Low','Normal','High','Urgent']='Normal'
    passport_id:str|None=None
    job_id:str|None=None
    owner_id:int|None=None


class CaseChange(Trimmed):
    version:int=Field(ge=1)
    status:Literal['Open','Investigating','Awaiting Response','Resolved','Closed']
    note:str=Field(min_length=1,max_length=10000)
    resolution:str=Field(default='',max_length=10000)
    owner_id:int|None=None


class CaseNote(Trimmed):
    version:int=Field(ge=1)
    note:str=Field(min_length=1,max_length=10000)


TRANSITIONS={'Open':{'Investigating'},'Investigating':{'Awaiting Response','Resolved'},
             'Awaiting Response':{'Investigating','Resolved'},'Resolved':{'Investigating','Closed'},'Closed':{'Investigating'}}


def register(app,user_dep,check_job):
    def access(db,identifier,user):
        case=db.get(TechnicalCase,identifier)
        if not case or case.company_id!=user.company_id:raise HTTPException(404,'Technical case not found')
        if user.role!='admin' and case.owner_id!=user.id:raise HTTPException(403,'This case is assigned to another owner')
        return case

    def owner(db,identifier,company_id,job):
        person=db.get(User,identifier)
        if not person or not person.active or person.company_id!=company_id:raise HTTPException(422,'Choose an active owner from your company')
        if job and person.role!='admin' and person.id!=job.engineer_id:raise HTTPException(422,'The owner must have access to the linked inspection')
        return person

    def event(db,case,user,kind,note):
        db.add(CaseEvent(id=str(uuid.uuid4()),case_id=case.id,actor_id=user.id,kind=kind,note=note))
        log(db,user.company_id,user.id,'case.'+kind.lower().replace(' ','_'),'technical_case',case.id)

    @app.get('/api/cases')
    def cases(user=Depends(user_dep),db:Session=Depends(get_db)):
        query=select(TechnicalCase).where(TechnicalCase.company_id==user.company_id)
        if user.role!='admin':query=query.where(TechnicalCase.owner_id==user.id)
        return db.scalars(query.order_by(TechnicalCase.created_at.desc())).all()

    @app.post('/api/cases')
    def create(data:CaseIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        if not data.passport_id and not data.job_id:raise HTTPException(422,'Link a passport or inspection to give this case context')
        if data.passport_id:
            passport=db.get(ProductPassport,data.passport_id)
            if not passport or passport.company_id!=user.company_id:raise HTTPException(404,'Passport not found')
            if passport.archived_at:raise HTTPException(409,'Restore this passport before opening a new technical case')
        job=db.get(Job,data.job_id) if data.job_id else None
        if data.job_id:check_job(job,user)
        if data.passport_id and job:
            link=db.scalar(select(PassportInspection).where(PassportInspection.job_id==job.id,PassportInspection.passport_id==data.passport_id))
            if not link:raise HTTPException(422,'Link this inspection to this passport first, or choose one source of context')
        owner_id=data.owner_id or user.id
        if user.role!='admin' and owner_id!=user.id:raise HTTPException(403,'Only administrators assign other owners')
        owner(db,owner_id,user.company_id,job)
        case=TechnicalCase(id=str(uuid.uuid4()),company_id=user.company_id,**data.model_dump(exclude={'owner_id'}),owner_id=owner_id)
        db.add(case);db.flush();event(db,case,user,'Created',data.description)
        if owner_id!=user.id:db.add(Notification(id=str(uuid.uuid4()),company_id=user.company_id,user_id=owner_id,title='Technical case assigned',body=data.title))
        db.commit();db.refresh(case);return case

    @app.get('/api/cases/{identifier}')
    def detail(identifier:str,user=Depends(user_dep),db:Session=Depends(get_db)):
        case=access(db,identifier,user)
        events=db.scalars(select(CaseEvent).where(CaseEvent.case_id==case.id).order_by(CaseEvent.created_at,CaseEvent.id)).all()
        person=db.get(User,case.owner_id)
        return {'case':case,'owner_name':person.name,'events':events}

    @app.patch('/api/cases/{identifier}')
    def change(identifier:str,data:CaseChange,user=Depends(user_dep),db:Session=Depends(get_db)):
        case=access(db,identifier,user)
        if data.status!=case.status and data.status not in TRANSITIONS[case.status]:raise HTTPException(409,'Follow the case workflow: investigate, resolve, then close')
        if case.status=='Closed' and (user.role!='admin' or data.status!='Investigating'):raise HTTPException(409,'An administrator must reopen this closed case')
        if data.status=='Resolved' and not data.resolution:raise HTTPException(422,'Record a resolution before resolving this case')
        owner_id=data.owner_id or case.owner_id
        if owner_id!=case.owner_id and user.role!='admin':raise HTTPException(403,'Only administrators reassign cases')
        person=owner(db,owner_id,user.company_id,db.get(Job,case.job_id) if case.job_id else None)
        resolution=data.resolution if data.status=='Resolved' else case.resolution if data.status=='Closed' else ''
        changed=db.execute(update(TechnicalCase).where(TechnicalCase.id==case.id,TechnicalCase.version==data.version).values(status=data.status,owner_id=owner_id,resolution=resolution,version=TechnicalCase.version+1).execution_options(synchronize_session=False))
        if changed.rowcount!=1:raise HTTPException(409,'This case changed. Refresh before saving')
        event(db,case,user,'Updated',f'{case.status} → {data.status}. Owner: {person.name}.\n{data.note}'+(f'\nResolution: {resolution}' if resolution else ''))
        if owner_id!=case.owner_id:db.add(Notification(id=str(uuid.uuid4()),company_id=user.company_id,user_id=owner_id,title='Technical case assigned',body=case.title))
        db.commit();return {'ok':True}

    @app.post('/api/cases/{identifier}/notes')
    def note(identifier:str,data:CaseNote,user=Depends(user_dep),db:Session=Depends(get_db)):
        case=access(db,identifier,user)
        if case.status=='Closed':raise HTTPException(409,'Reopen the case before adding a note')
        result=db.execute(update(TechnicalCase).where(TechnicalCase.id==case.id,TechnicalCase.version==data.version,TechnicalCase.status!='Closed').values(version=TechnicalCase.version+1).execution_options(synchronize_session=False))
        if result.rowcount!=1:raise HTTPException(409,'This case changed. Refresh before saving')
        event(db,case,user,'Note added',data.note);db.commit();return {'ok':True}
