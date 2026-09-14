"""Retained exact-source excerpts attached to authorised inspection records."""
import hashlib
import re
import uuid
from datetime import datetime
from fastapi import Depends, HTTPException
from pydantic import Field
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, UniqueConstraint, select, update
from sqlalchemy.orm import Mapped, mapped_column, Session
from sqlalchemy.exc import IntegrityError
from .db import Base, get_db
from .models import now, Job, WorkOrder
from .passports import Trimmed
from .documents import document_file, RENDER_LOCK
from .source_reviews import latest, summary
from .audit import log


class Citation(Base):
    __tablename__='inspection_citations'
    __table_args__=(UniqueConstraint('job_id','review_id','page','excerpt_sha256',name='uq_inspection_citation'),)
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    job_id:Mapped[str]=mapped_column(ForeignKey('jobs.id'),index=True)
    company_id:Mapped[int]=mapped_column(ForeignKey('companies.id'),index=True)
    review_id:Mapped[str]=mapped_column(ForeignKey('source_reviews.id'))
    document_id:Mapped[str]=mapped_column(String(100))
    document_sha256:Mapped[str]=mapped_column(String(64))
    title:Mapped[str]=mapped_column(String(300))
    manufacturer:Mapped[str]=mapped_column(String(180))
    revision:Mapped[str]=mapped_column(String(180))
    applicability:Mapped[str]=mapped_column(Text)
    page:Mapped[int]=mapped_column(Integer)
    excerpt:Mapped[str]=mapped_column(Text)
    excerpt_sha256:Mapped[str]=mapped_column(String(64))
    relevance:Mapped[str]=mapped_column(Text)
    added_by_id:Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class CitationIn(Trimmed):
    document_id:str
    review_id:str
    page:int=Field(ge=1)
    excerpt:str=Field(min_length=10,max_length=2000)
    relevance:str=Field(min_length=1,max_length=5000)


def normalise(value):return re.sub(r'\s+',' ',value).strip()


def reviewed_page(db,company_id,identifier,page):
    path,doc=document_file(company_id,identifier)
    review=latest(db,company_id,identifier)
    status=summary(db,company_id,doc)
    if not review or not status['reference_approved']:raise HTTPException(409,'This source does not have a current reference approval')
    if page<review.page_start or page>review.page_end:raise HTTPException(422,'Choose a page within the reviewed range')
    import pypdfium2 as pdfium
    with RENDER_LOCK:
        pdf=pdfium.PdfDocument(path)
        try:
            if page>len(pdf):raise HTTPException(422,'PDF page not found')
            item=pdf[page-1]
            try:
                textpage=item.get_textpage()
                try:content=normalise(textpage.get_text_range())
                finally:textpage.close()
            finally:item.close()
        finally:pdf.close()
    return review,content


def citation_records(db,job):
    records=db.scalars(select(Citation).where(Citation.job_id==job.id,Citation.company_id==job.company_id).order_by(Citation.created_at,Citation.id)).all()
    results=[]
    for c in records:
        try:
            _,doc=document_file(job.company_id,c.document_id)
            state=summary(db,job.company_id,doc)
            current=state.get('id')==c.review_id and state['reference_approved']
            status='Current reference review' if current else 'Historical citation: review changed or withdrawn'
        except (HTTPException,OSError):
            current=False;status='Historical citation: source unavailable'
        results.append({'id':c.id,'document_id':c.document_id,'review_id':c.review_id,'title':c.title,'manufacturer':c.manufacturer,'revision':c.revision,'document_sha256':c.document_sha256,'page':c.page,'excerpt':c.excerpt,'relevance':c.relevance,'applicability':c.applicability,'current':current,'status':status,'created_at':c.created_at})
    return results


def register(app,user_dep,check_job):
    @app.get('/api/documents/{identifier}/reviewed-pages/{page}')
    def page(identifier:str,page:int,user=Depends(user_dep),db:Session=Depends(get_db)):
        review,content=reviewed_page(db,user.company_id,identifier,page)
        return {'review_id':review.id,'page':page,'text':content,'applicability':review.applicability}

    @app.get('/api/jobs/{job_id}/citations')
    def citations(job_id:str,user=Depends(user_dep),db:Session=Depends(get_db)):
        job=db.get(Job,job_id);check_job(job,user)
        return citation_records(db,job)

    @app.post('/api/jobs/{job_id}/citations')
    def attach(job_id:str,data:CitationIn,user=Depends(user_dep),db:Session=Depends(get_db)):
        job=db.get(Job,job_id);check_job(job,user)
        if db.scalar(select(WorkOrder.id).where(WorkOrder.job_id==job.id,WorkOrder.status=='Complete')):raise HTTPException(409,'Reopen the completed visit before adding evidence')
        review,content=reviewed_page(db,user.company_id,data.document_id,data.page)
        if review.id!=data.review_id:raise HTTPException(409,'Source review changed. Load the page again')
        excerpt=normalise(data.excerpt)
        if len(excerpt)<10 or excerpt not in content:raise HTTPException(422,'Use an exact excerpt from the displayed source page. OCR-only or paraphrased text cannot be attached as a source quote')
        digest=hashlib.sha256(excerpt.encode()).hexdigest()
        prior=db.scalar(select(Citation).where(Citation.job_id==job.id,Citation.review_id==review.id,Citation.page==data.page,Citation.excerpt_sha256==digest))
        if prior:return {'id':prior.id,'already_attached':True}
        citation=Citation(id=str(uuid.uuid4()),job_id=job.id,company_id=user.company_id,review_id=review.id,document_id=data.document_id,document_sha256=review.document_sha256,title=review.title,manufacturer=review.manufacturer,revision=review.revision,applicability=review.applicability,page=data.page,excerpt=excerpt,excerpt_sha256=digest,relevance=data.relevance,added_by_id=user.id)
        db.add(citation)
        db.execute(update(Job).where(Job.id==job.id).values(citation_version=Job.citation_version+1,approved_by_engineer=False))
        log(db,user.company_id,user.id,'inspection.citation_added','job',job.id,{'citation_id':citation.id,'review_id':review.id})
        try:db.commit()
        except IntegrityError:
            db.rollback();raise HTTPException(409,'The evidence changed. Refresh before attaching')
        return {'id':citation.id,'already_attached':False}
