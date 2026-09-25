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


def build_report(job, engineer_name, photos, upload_dir: Path, citations=None, outcome=None, acceptance=None,
                 company=None):
    buf=BytesIO()
    brand_name=(getattr(company,'report_name','') or getattr(company,'name','') or 'FenIQ').strip()
    brand_contact=(getattr(company,'report_contact','') or '').strip()
    brand_accent=getattr(company,'report_accent','') or '#163E31'
    ink=colors.HexColor(brand_accent)
    styles=getSampleStyleSheet()
    body=ParagraphStyle('Body',parent=styles['BodyText'],fontSize=9,leading=13,textColor=colors.HexColor('#34483e'))
    heading=ParagraphStyle('Section',parent=styles['Heading3'],fontSize=11,leading=14,textColor=ink,spaceBefore=12,spaceAfter=6)
    title=ParagraphStyle('Brand',parent=styles['Title'],alignment=0,fontSize=28,leading=32,textColor=ink)
    small=ParagraphStyle('Small',parent=body,fontSize=8,leading=11,textColor=colors.HexColor('#6e7c72'))
    def text(value,style=body):
        return Paragraph(escape(str(value or 'Not recorded')).replace('\n','<br/>'),style)
    doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=19*mm,title=f'{brand_name} Service Report',author=brand_name)
    story=[Paragraph(escape(brand_name),title),text('Powered by FenIQ | FIELD INTELLIGENCE / SERVICE REPORT',small)]
    if brand_contact:
        story.append(text(brand_contact,small))
    story.append(Spacer(1,6*mm))
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
    story.extend([Paragraph('Customer acceptance',heading)])
    if acceptance:
        payload=acceptance['payload']
        story.extend([text(f"{payload['status']} | {payload.get('customer_name') or 'Name not recorded'} | Recorded {acceptance['created_at'].strftime('%d %b %Y %H:%M')}"),text(payload.get('note') or 'No note'),text(f"Acceptance revision {acceptance['version']} | {'Current report state' if acceptance['report_current'] else 'Historical report state'}",small),text('Report state SHA-256: '+acceptance['report_sha256'],small)])
    else:
        story.append(text(job.signature or 'No governed acceptance recorded'))
    if not job.approved_by_engineer:
        story.extend([Spacer(1,3*mm),text('Diagnosis has not yet been marked as engineer reviewed.',small)])
    if outcome:
        payload=outcome['payload']
        story.extend([PageBreak(),Paragraph('Latest repair outcome',heading),
                      text(f"Retained revision {outcome['version']} | {'Integrity checked' if outcome['integrity_valid'] else 'Integrity check failed'}"),
                      Paragraph('Original predicted diagnosis',heading),text(payload.get('predicted_diagnosis')),
                      Paragraph('Engineer-confirmed diagnosis',heading),text(payload.get('confirmed_diagnosis')),
                      Paragraph('Actual repair',heading),text(payload.get('actual_repair')),
                      Paragraph('Final checks and observed results',heading),text(payload.get('verification_checks')),
                      Paragraph('Reported result',heading),text('Resolved' if payload.get('resolved') else 'Not resolved'),
                      text('Repeat visit required: '+('Yes' if payload.get('repeat_visit_required') else 'No'))])
        definition=payload.get('verification_definition')
        if definition:
            answers=payload.get('verification_answers',{})
            story.extend([Paragraph('Structured verification',heading),
                          text(f"{definition['title']} | Revision {definition['revision']}"),
                          *[text(f"{check['label']}: {answers.get(check['key'],'Not recorded')}") for check in definition['checks']],
                          text(definition['source_status'],small),
                          text('Verification definition SHA-256: '+definition['sha256'],small)])
        if payload.get('change_reason'):
            story.extend([Paragraph('Reason for correction',heading),text(payload['change_reason'])])
        story.extend([text('This is the latest engineer-submitted outcome. Earlier revisions remain in the audit history.',small),
                      text('Original diagnosis SHA-256: '+payload.get('snapshot_sha256','Not recorded'),small),
                      text('Outcome SHA-256: '+outcome['sha256'],small)])
    if citations:
        story.extend([PageBreak(), Paragraph('Source citations',heading)])
        for citation in citations:
            story.extend([text(f"{citation['title']} | {citation['manufacturer']} | Revision {citation['revision']} | PDF page {citation['page']}"),text(citation['status'],small),text(citation['excerpt']),text('Relevance: '+citation['relevance']),text('Reviewed applicability: '+citation['applicability'],small),text('Source SHA-256: '+citation['document_sha256'],small),Spacer(1,3*mm)])
        story.append(text('Reference approval does not verify every specification or authorise remedial work. Historical citations are retained after a source review changes.',small))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#6e7c72'))
        canvas.drawString(18*mm,11*mm,f'{brand_name} | FenIQ | '+job.id[:8]);canvas.drawRightString(192*mm,11*mm,f'Page {doc.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    buf.seek(0)
    return buf
