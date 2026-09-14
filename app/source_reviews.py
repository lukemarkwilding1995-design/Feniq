"""Company review history for specific private PDF bytes and declared scope."""
import hashlib
import uuid
from datetime import datetime
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from .db import Base, get_db
from .models import now, User
from .passports import Trimmed
from .documents import document_file
from .audit import log


class SourceReview(Base):
    __tablename__='source_reviews'
    __table_args__=(UniqueConstraint('company_id','document_id','sequence',name='uq_source_review_sequence'),)
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True)
    document_id:Mapped[str]=mapped_column(String(100),index=True)
    sequence:Mapped[int]=mapped_column(Integer)
    reviewer_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
    document_sha256:Mapped[str]=mapped_column(String(64))
    status:Mapped[str]=mapped_column(String(40))
    title:Mapped[str]=mapped_column(String(300))
    manufacturer:Mapped[str]=mapped_column(String(180))
    revision:Mapped[str]=mapped_column(String(180))
    applicability:Mapped[str]=mapped_column(Text)
    page_start:Mapped[int]=mapped_column(Integer)
    page_end:Mapped[int]=mapped_column(Integer)
    note:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class ReviewIn(Trimmed):
    previous_id:str|None=None
    document_sha256:str=Field(pattern=r'^[0-9a-f]{64}$')
    status:Literal['Approved for reference','Rejected','Withdrawn']
    title:str=Field(min_length=1,max_length=300)
    manufacturer:str=Field(min_length=1,max_length=180)
    revision:str=Field(min_length=1,max_length=180)
    applicability:str=Field(min_length=1,max_length=5000)
    page_start:int=Field(ge=1)
    page_end:int=Field(ge=1)
    note:str=Field(min_length=1,max_length=10000)
    attested:bool=False


def latest(db,company_id,document_id):
    return db.scalar(select(SourceReview).where(SourceReview.company_id==company_id,SourceReview.document_id==document_id).order_by(SourceReview.sequence.desc()))


def file_hash(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def summary(db,company_id,document):
    review=latest(db,company_id,document['id'])
    if not review:return {'status':'Pending review','reference_approved':False}
    matching=review.document_sha256==document.get('sha256')
    if matching and review.status=='Approved for reference':
        try:matching=file_hash(document_file(company_id,document['id'])[0])==review.document_sha256
        except HTTPException:matching=False
    return {'id':review.id,'status':review.status if matching else 'Source changed; review required',
            'reference_approved':matching and review.status=='Approved for reference',
            'revision':review.revision,'applicability':review.applicability,'page_start':review.page_start,'page_end':review.page_end}


def register(app,user_dep):
    @app.get('/api/documents/{identifier}/reviews')
    def reviews(identifier:str,user=Depends(user_dep),db:Session=Depends(get_db)):
        path,document=document_file(user.company_id,identifier)
        history=db.scalars(select(SourceReview).where(SourceReview.company_id==user.company_id,SourceReview.document_id==identifier).order_by(SourceReview.sequence.desc())).all()
        return {'document':{'id':identifier,'title':document['title'],'manufacturer':document['manufacturer'],'revision':document.get('revision',''),'sha256':document.get('sha256',''),'page_count':document.get('page_count',0)},
                'current':summary(db,user.company_id,document),
                'history':[{'id':r.id,'sequence':r.sequence,'status':r.status,'title':r.title,'manufacturer':r.manufacturer,'revision':r.revision,'applicability':r.applicability,'page_start':r.page_start,'page_end':r.page_end,'note':r.note,'created_at':r.created_at,'reviewer':db.get(User,r.reviewer_id).name} for r in history]}

    @app.post('/api/documents/{identifier}/reviews')
    def review(identifier:str,data:ReviewIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        if user.role!='admin':raise HTTPException(403,'Company administrator review required')
        path,document=document_file(user.company_id,identifier)
        if path.suffix.lower()!='.pdf':raise HTTPException(422,'This review workflow is for PDF sources')
        prior=latest(db,user.company_id,identifier)
        if data.previous_id!=(prior.id if prior else None):raise HTTPException(409,'Another review was recorded. Refresh before submitting')
        actual=file_hash(path)
        if actual!=data.document_sha256 or actual!=document.get('sha256'):raise HTTPException(409,'Source bytes changed or the import hash is missing. Reimport and review the current file')
        if data.page_end<data.page_start or data.page_end>document.get('page_count',0):raise HTTPException(422,'Choose a valid PDF page range')
        if data.status=='Approved for reference' and not data.attested:raise HTTPException(422,'Confirm that you reviewed these source pages and their applicability')
        record=SourceReview(id=str(uuid.uuid4()),company_id=user.company_id,document_id=identifier,sequence=prior.sequence+1 if prior else 1,reviewer_id=user.id,**data.model_dump(exclude={'previous_id','attested'}))
        db.add(record);log(db,user.company_id,user.id,'source.reviewed','document',identifier,{'review_id':record.id,'status':record.status})
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,'Another review was recorded. Refresh before submitting')
        return {'id':record.id,'status':record.status}
