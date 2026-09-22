"""Persistent company site/product identity and append-only lifecycle records."""
import uuid
from datetime import date, datetime
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import String, Text, ForeignKey, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from .db import Base, get_db
from .models import now, Customer, Job, WorkOrder
from .audit import log


class Site(Base):
    __tablename__ = "sites"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ProductPassport(Base):
    __tablename__ = "product_passports"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[str] = mapped_column(ForeignKey("sites.id"), index=True)
    label: Mapped[str] = mapped_column(String(200))
    product: Mapped[str] = mapped_column(String(100))
    manufacturer: Mapped[str] = mapped_column(String(180), default="")
    system_name: Mapped[str] = mapped_column(String(180), default="")
    serial_number: Mapped[str] = mapped_column(String(180), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class PassportInspection(Base):
    __tablename__ = "passport_inspections"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("product_passports.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), unique=True, index=True)


class PassportEvent(Base):
    __tablename__ = "passport_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    passport_id: Mapped[str] = mapped_column(ForeignKey("product_passports.id"), index=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(40))
    occurred_on: Mapped[str] = mapped_column(String(10))
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Trimmed(BaseModel):
    @field_validator('*', mode='before')
    @classmethod
    def trim(cls, value):
        return value.strip() if isinstance(value, str) else value


class SiteIn(Trimmed):
    customer_id: str
    name: str = Field(min_length=1, max_length=200)
    address: str = ""


class PassportIn(Trimmed):
    site_id: str
    label: str = Field(min_length=1, max_length=200)
    product: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(default="", max_length=180)
    system_name: str = Field(default="", max_length=180)
    serial_number: str = Field(default="", max_length=180)


class EventIn(Trimmed):
    kind: Literal['Manufacture note', 'Installation note', 'Service note', 'Warranty note', 'Correction note']
    occurred_on: date
    note: str = Field(min_length=1, max_length=10000)


class LinkIn(BaseModel):
    job_id: str


def register(app, user_dep, check_job):
    def owned(db, model, identifier, user):
        record = db.get(model, identifier)
        if not record or record.company_id != user.company_id:
            raise HTTPException(404, "Record not found")
        return record

    def admin(user):
        if user.role != 'admin':
            raise HTTPException(403, "Company administrator required")

    @app.get('/api/sites')
    def sites(user=Depends(user_dep), db: Session=Depends(get_db)):
        return db.scalars(select(Site).where(Site.company_id==user.company_id).order_by(Site.name)).all()

    @app.post('/api/sites')
    def create_site(data:SiteIn, user=Depends(user_dep), db:Session=Depends(get_db)):
        admin(user); owned(db,Customer,data.customer_id,user)
        site=Site(id=str(uuid.uuid4()),company_id=user.company_id,**data.model_dump())
        db.add(site);log(db,user.company_id,user.id,'site.created','site',site.id)
        db.commit();db.refresh(site);return site

    @app.get('/api/passports')
    def passports(user=Depends(user_dep),db:Session=Depends(get_db)):
        return db.scalars(select(ProductPassport).where(ProductPassport.company_id==user.company_id).order_by(ProductPassport.created_at.desc())).all()

    @app.post('/api/passports')
    def create_passport(data:PassportIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        admin(user);owned(db,Site,data.site_id,user)
        product=ProductPassport(id=str(uuid.uuid4()),company_id=user.company_id,**data.model_dump())
        db.add(product);db.flush()
        db.add(PassportEvent(id=str(uuid.uuid4()),passport_id=product.id,recorded_by_id=user.id,kind='Passport created',occurred_on=date.today().isoformat(),note='Product identity registered. Manufacturer details are user supplied, not verified specifications.'))
        log(db,user.company_id,user.id,'passport.created','passport',product.id)
        db.commit();db.refresh(product);return product

    @app.get('/api/passports/{identifier}')
    def detail(identifier:str,user=Depends(user_dep),db:Session=Depends(get_db)):
        from .outcomes import history as outcome_history, serialise as serialise_outcome
        from .repeat_failures import analyse as analyse_failures
        product=owned(db,ProductPassport,identifier,user)
        events=db.scalars(select(PassportEvent).where(PassportEvent.passport_id==identifier).order_by(PassportEvent.created_at,PassportEvent.id)).all()
        query=select(Job).join(PassportInspection,PassportInspection.job_id==Job.id).where(PassportInspection.passport_id==identifier,Job.company_id==user.company_id)
        if user.role!='admin': query=query.where(Job.engineer_id==user.id)
        jobs=db.scalars(query).all()
        inspections=[]
        for job in jobs:
            rows=outcome_history(db,job)
            latest=serialise_outcome(rows[-1]) if rows else None
            inspections.append({'id':job.id,'reference':job.reference,'outcome':job.outcome,'created_at':job.created_at,
                                'repair_outcome':latest,'outcome_revision_count':len(rows)})
        return {'passport':product,'site':owned(db,Site,product.site_id,user),'events':events,
                'inspections':inspections,'failure_analysis':analyse_failures(db,jobs)}

    @app.post('/api/passports/{identifier}/events')
    def add_event(identifier:str,data:EventIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        owned(db,ProductPassport,identifier,user)
        record=PassportEvent(id=str(uuid.uuid4()),passport_id=identifier,recorded_by_id=user.id,kind=data.kind,occurred_on=data.occurred_on.isoformat(),note=data.note)
        db.add(record);log(db,user.company_id,user.id,'passport.event_added','passport',identifier,{'event_id':record.id})
        db.commit();db.refresh(record);return record

    @app.post('/api/passports/{identifier}/inspections')
    def link(identifier:str,data:LinkIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        product=owned(db,ProductPassport,identifier,user)
        job=db.get(Job,data.job_id);check_job(job,user)
        site=owned(db,Site,product.site_id,user)
        if job.customer_id and job.customer_id!=site.customer_id:
            raise HTTPException(409,'Passport customer conflicts with the inspection customer')
        linked_customers=set(db.scalars(select(WorkOrder.customer_id).where(
            WorkOrder.company_id==user.company_id,WorkOrder.job_id==job.id,
            WorkOrder.customer_id.is_not(None))).all())
        if any(customer_id!=site.customer_id for customer_id in linked_customers):
            raise HTTPException(409,'Passport customer conflicts with a linked work order')
        prior=db.scalar(select(PassportInspection).where(PassportInspection.job_id==job.id))
        if prior:
            if prior.passport_id==identifier:return {'ok':True}
            raise HTTPException(409,'This inspection is already linked to another product passport')
        db.add(PassportInspection(id=str(uuid.uuid4()),passport_id=identifier,job_id=job.id))
        db.add(PassportEvent(id=str(uuid.uuid4()),passport_id=identifier,recorded_by_id=user.id,kind='Inspection linked',occurred_on=date.today().isoformat(),note='An inspection was linked. Its report remains subject to assigned-engineer access.'))
        log(db,user.company_id,user.id,'passport.inspection_linked','passport',identifier,{'job_id':job.id})
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,'Inspection link changed; refresh and try again')
        return {'ok':True}
