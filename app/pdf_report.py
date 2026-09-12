from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
import json

def build_report(job, engineer_name, photos, upload_dir: Path):
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16*mm, leftMargin=16*mm, topMargin=14*mm, bottomMargin=14*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("FenIQTitle", parent=styles["Title"], fontSize=24, leading=26, spaceAfter=4)
    h = ParagraphStyle("H", parent=styles["Heading3"], fontSize=11, leading=13, spaceBefore=9, spaceAfter=5, textColor=colors.HexColor("#14324a"))
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=9.5, leading=13)
    story = [Paragraph("FenIQ", title), Paragraph("FENESTRATION INTELLIGENCE — SERVICE REPORT", styles["Small"]), Spacer(1, 5*mm)]
    data = [
        ["Customer / Site", job.customer or "—", "Reference", job.reference or "—"],
        ["Product", job.product or "—", "System", job.system_name or "—"],
        ["Engineer", engineer_name, "Outcome", job.outcome or "—"],
    ]
    t=Table(data, colWidths=[30*mm,55*mm,25*mm,55*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#f2f6f9")),
        ("BOX",(0,0),(-1,-1),0.25,colors.HexColor("#cfd9e0")),
        ("INNERGRID",(0,0),(-1,-1),0.25,colors.HexColor("#dce4e9")),
        ("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTSIZE",(0,0),(-1,-1),8.5),
        ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),
        ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story += [t]
    sections = [
        ("Reported Fault", job.fault),
        ("Inspection & Findings", ". ".join(json.loads(job.evidence_json or "[]"))),
        ("Diagnosis", f"{job.diagnosis} ({job.confidence}% diagnostic confidence). {job.recommendation}"),
        ("Work Carried Out", job.work_done),
        ("Parts / Further Requirements", job.parts_required),
        ("Engineer Notes", job.engineer_notes),
    ]
    for heading, text in sections:
        story += [Paragraph(heading,h), Paragraph((text or "—").replace("\n","<br/>"),body)]
    if photos:
        story += [Spacer(1,5*mm), Paragraph("Photo Evidence",h)]
        cells=[]
        for p in photos[:6]:
            fp=upload_dir/p.filename
            if fp.exists():
                try: cells.append(Image(str(fp), width=48*mm, height=36*mm))
                except Exception: pass
        for i in range(0,len(cells),3):
            row=cells[i:i+3]+[""]*(3-len(cells[i:i+3]))
            story.append(Table([row], colWidths=[52*mm]*3))
    story += [Spacer(1,7*mm), Paragraph(f"<b>Customer Sign-off:</b> {job.signature or 'Not signed'}",body)]
    if not job.approved_by_engineer:
        story += [Spacer(1,3*mm), Paragraph("<b>Note:</b> Diagnosis has not been marked as engineer-approved.", styles["Small"])]
    doc.build(story)
    buf.seek(0)
    return buf
