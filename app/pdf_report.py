from io import BytesIO
from pathlib import Path
from html import escape
import json
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from PIL import Image as PILImage


def build_report(job, engineer_name, photos, upload_dir: Path, citations=None):
    buf=BytesIO()
    ink=colors.HexColor('#163e31')
    styles=getSampleStyleSheet()
    body=ParagraphStyle('Body',parent=styles['BodyText'],fontSize=9,leading=13,textColor=colors.HexColor('#34483e'))
    heading=ParagraphStyle('Section',parent=styles['Heading3'],fontSize=11,leading=14,textColor=ink,spaceBefore=12,spaceAfter=6)
    title=ParagraphStyle('Brand',parent=styles['Title'],alignment=0,fontSize=28,leading=32,textColor=ink)
    small=ParagraphStyle('Small',parent=body,fontSize=8,leading=11,textColor=colors.HexColor('#6e7c72'))
    def text(value,style=body):
        return Paragraph(escape(str(value or 'Not recorded')).replace('\n','<br/>'),style)
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=19*mm,title='FenIQ Service Report',author='FenIQ')
    story=[Paragraph('FenIQ',title),text('FIELD INTELLIGENCE / SERVICE REPORT',small),Spacer(1,6*mm)]
    meta=[('Customer / site',job.customer,'Reference',job.reference),('Product',job.product,'System',job.system_name),('Engineer',engineer_name,'Outcome',job.outcome),('Inspection date',job.created_at.strftime('%d %b %Y'),'Review','Engineer reviewed' if job.approved_by_engineer else 'Review required')]
    rows=[[text(k,small),text(v),text(k2,small),text(v2)] for k,v,k2,v2 in meta]
    table=Table(rows,colWidths=[28*mm,59*mm,25*mm,62*mm])
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f1f5ed')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dfe6da'))]))
    story.append(table)
    for label,value in [('Reported fault',job.fault),('Diagnosis',job.diagnosis),('Supporting evidence','\n'.join(json.loads(job.evidence_json or '[]'))),('Recommended action',job.recommendation),('Work carried out',job.work_done),('Parts / further requirements',job.parts_required),('Engineer notes',job.engineer_notes)]:
        story.extend([Paragraph(label,heading),text(value)])
    story.extend([Spacer(1,4*mm),text(f'{job.confidence}% rule score. Decision support, not a calibrated probability or a manufacturer specification.',small)])
    if photos:
        story.append(Paragraph('Photo evidence',heading))
        for p in photos:
            path=upload_dir/p.filename
            if not path.exists(): continue
            try:
                with PILImage.open(path) as image: width,height=image.size
                scale=min(150*mm/width,90*mm/height)
                story.append(KeepTogether([Image(str(path),width=width*scale,height=height*scale,hAlign='LEFT'),Spacer(1,2*mm),text(f'{p.phase.title()} - {p.original_name}',small),Spacer(1,4*mm)]))
            except (OSError,ValueError):
                story.append(text('Photo could not be included.',small))
    story.extend([Paragraph('Customer sign-off',heading),text(job.signature or 'Not signed')])
    if not job.approved_by_engineer:
        story.extend([Spacer(1,3*mm),text('Diagnosis has not yet been marked as engineer reviewed.',small)])
    if citations:
        story.extend([PageBreak(), Paragraph('Source citations',heading)])
        for citation in citations:
            story.extend([text(f"{citation['title']} | {citation['manufacturer']} | Revision {citation['revision']} | PDF page {citation['page']}"),text(citation['status'],small),text(citation['excerpt']),text('Relevance: '+citation['relevance']),text('Reviewed applicability: '+citation['applicability'],small),text('Source SHA-256: '+citation['document_sha256'],small),Spacer(1,3*mm)])
        story.append(text('Reference approval does not verify every specification or authorise remedial work. Historical citations are retained after a source review changes.',small))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#6e7c72'))
        canvas.drawString(18*mm,11*mm,'FenIQ | '+job.id[:8]);canvas.drawRightString(192*mm,11*mm,f'Page {doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    buf.seek(0)
    return buf
