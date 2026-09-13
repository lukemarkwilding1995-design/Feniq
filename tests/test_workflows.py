import os
import tempfile
import unittest
import json
from io import BytesIO
from pathlib import Path

TEST_DIR = None if os.getenv('FENIQ_TEST_DIR') else tempfile.TemporaryDirectory()
TEST_PATH = Path(os.environ['FENIQ_TEST_DIR']) if TEST_DIR is None else Path(TEST_DIR.name)
TEST_PATH.mkdir(parents=True,exist_ok=True)
os.environ['DATABASE_URL']='sqlite:///'+str(TEST_PATH/'test.db')
os.environ['UPLOAD_DIR']=str(TEST_PATH/'photos')
os.environ['SECRET_KEY']='test-only-key-with-more-than-thirty-two-characters'
os.environ['FENIQ_DEMO']='0'
from fastapi.testclient import TestClient
from PIL import Image
from app.main import app
from app.db import Base, engine
from app.migrations import upgrade
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.exec_driver_sql('DROP TABLE IF EXISTS feniq_schema_revisions')
        upgrade(engine)
        self.client=TestClient(app)
        a=self.client.post('/api/register-company',json={'company_name':'Test Windows','admin_name':'Admin','email':'admin@example.com','password':'strong-password'}).json()
        self.admin={'Authorization':'Bearer '+a['token']}
        self.invite=a['invite_code']
        e=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Engineer','email':'engineer@example.com','password':'strong-password'}).json()
        self.engineer={'Authorization':'Bearer '+e['token']}
        self.engineer_id=e['user']['id']

    def job(self,**extra):
        return self.client.post('/api/jobs',headers=self.engineer,json={'customer':'Test site','fault':'Stiff handle','product':'Window',**extra})

    def test_auth_and_roles(self):
        self.assertEqual(self.client.get('/api/jobs').status_code,401)
        self.assertEqual(self.client.get('/api/company/users',headers=self.engineer).status_code,403)
        self.assertIsNone(self.client.get('/api/company',headers=self.engineer).json()['invite_code'])
        self.assertEqual(self.client.post('/api/login',json={'email':'admin@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/register-company',json={'company_name':'  ','admin_name':'Admin','email':'bad','password':'password'}).status_code,422)
        self.assertEqual(self.client.get('/api/commercial/dashboard',headers=self.engineer).status_code,403)

    def test_approval_requires_review_and_current_scope(self):
        job=self.job(diagnosis='Initial finding').json()
        request=self.client.post('/api/approvals',headers=self.engineer,json={'job_id':job['id'],'approval_type':'Replacement','description':'Replace keep'}).json()
        endpoint='/api/approvals/'+request['id']+'/decision'
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={'status':'Approved'}).status_code,409)
        self.client.patch('/api/jobs/'+job['id']+'/approve',headers=self.engineer)
        job['diagnosis']='Changed finding';job['approved_by_engineer']=True
        updated=self.client.patch('/api/jobs/'+job['id'],headers=self.engineer,json=job).json()
        self.assertFalse(updated['approved_by_engineer'])
        self.client.patch('/api/jobs/'+job['id']+'/approve',headers=self.engineer)
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={'status':'Approved'}).status_code,409)
        self.assertFalse(self.client.get('/api/approvals',headers=self.admin).json()[0]['scope_current'])
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={'status':'Rejected'}).status_code,200)
        fresh=self.client.post('/api/approvals',headers=self.engineer,json={'job_id':job['id'],'approval_type':'Replacement','description':'Reviewed new scope'}).json()
        endpoint='/api/approvals/'+fresh['id']+'/decision'
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={'status':'Approved'}).status_code,200)
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={'status':'Rejected'}).status_code,409)

    def test_completion_and_reopening_gates(self):
        order=self.client.post('/api/work-orders',headers=self.admin,json={'title':'Service','assigned_engineer_id':self.engineer_id}).json()
        endpoint='/api/work-orders/'+order['id']+'/status'
        self.assertEqual(self.client.patch(endpoint+'?status=Complete',headers=self.engineer).status_code,409)
        job=self.job(work_order_id=order['id']).json()
        self.assertEqual(self.client.patch(endpoint+'?status=Complete',headers=self.engineer).status_code,409)
        job['outcome']='Adjusted / Resolved'
        self.client.patch('/api/jobs/'+job['id'],headers=self.engineer,json=job)
        self.client.patch('/api/jobs/'+job['id']+'/approve',headers=self.engineer)
        pending=self.client.post('/api/approvals',headers=self.engineer,json={'job_id':job['id'],'approval_type':'Work','description':'Decision pending'}).json()
        self.assertEqual(self.client.patch(endpoint+'?status=Complete',headers=self.engineer).status_code,409)
        self.client.post('/api/approvals/'+pending['id']+'/decision',headers=self.admin,json={'status':'Rejected'})
        self.assertEqual(self.client.patch(endpoint+'?status=Complete',headers=self.engineer).status_code,200)
        self.assertEqual(self.client.patch('/api/jobs/'+job['id'],headers=self.engineer,json=job).status_code,409)
        self.assertEqual(self.client.patch(endpoint+'?status=In%20Progress',headers=self.engineer).status_code,403)
        self.assertEqual(self.client.patch(endpoint+'?status=In%20Progress',headers=self.admin).status_code,200)
        linked={**order,'job_id':job['id'],'assigned_engineer_id':None}
        self.assertEqual(self.client.patch('/api/work-orders/'+order['id'],headers=self.admin,json=linked).status_code,422)
        order['job_id']=None
        self.assertEqual(self.client.patch('/api/work-orders/'+order['id'],headers=self.admin,json=order).status_code,409)

    def test_retained_inspection_cannot_be_deleted(self):
        job=self.job().json()
        self.assertEqual(self.client.delete('/api/jobs/'+job['id'],headers=self.engineer).status_code,409)
        self.assertEqual(self.client.get('/api/jobs/'+job['id'],headers=self.engineer).status_code,200)
        self.assertTrue(self.client.get('/api/jobs/'+job['id']+'/diagnostic-snapshot',headers=self.engineer).json()['integrity_valid'])

    def test_snapshot_survives_edits_and_learning(self):
        answers={'camb_catching':True,'works_open':True,'compression_even':'No','witness_marks':True,'keep_position_verified':True}
        job=self.job(module='locking_camb_keep',diagnostic_answers=answers).json()
        url='/api/jobs/'+job['id']+'/diagnostic-snapshot'
        original=self.client.get(url,headers=self.engineer).json()
        self.assertEqual(original['origin'],'server_diagnosis')
        self.assertEqual(original['payload']['answers'],answers)
        self.assertTrue(original['integrity_valid'])
        job['diagnosis']='Engineer revised conclusion'
        job['fault']='Updated observations'
        self.assertEqual(self.client.patch('/api/jobs/'+job['id'],headers=self.engineer,json=job).status_code,200)
        self.assertEqual(self.client.get(url,headers=self.engineer).json(),original)
        saved=self.client.post('/api/jobs/'+job['id']+'/learning',headers=self.engineer,json={'confirmed_diagnosis':'Engineer revised conclusion','actual_repair':'Adjusted keep','resolved':True})
        self.assertEqual(saved.status_code,200)
        feedback=self.client.get('/api/jobs/'+job['id']+'/learning',headers=self.engineer).json()
        self.assertEqual(feedback['predicted_diagnosis'],original['payload']['diagnosis'])
        self.assertEqual(self.client.get(url).status_code,401)
        other=self.client.post('/api/register-company',json={'company_name':'Other','admin_name':'Other','email':'other@example.com','password':'strong-password'}).json()
        self.assertEqual(self.client.get(url,headers={'Authorization':'Bearer '+other['token']}).status_code,403)
        colleague=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Colleague','email':'colleague@example.com','password':'strong-password'}).json()
        self.assertEqual(self.client.get(url,headers={'Authorization':'Bearer '+colleague['token']}).status_code,403)
        for statement in ['UPDATE diagnostic_snapshots SET payload_json = :payload WHERE job_id = :job', 'DELETE FROM diagnostic_snapshots WHERE job_id = :job']:
            with self.assertRaises(IntegrityError):
                with engine.begin() as connection:
                    connection.execute(text(statement),{'payload':'{}','job':job['id']})
        self.assertEqual(self.client.get(url,headers=self.engineer).json(),original)

    def test_legacy_snapshot_is_labelled_and_captured_before_edit(self):
        from app.db import SessionLocal
        from app.models import Job
        with SessionLocal() as db:
            db.add(Job(id='legacy-job',company_id=1,engineer_id=self.engineer_id,customer='Legacy site',diagnosis='Earlier recorded conclusion'))
            db.commit()
        url='/api/jobs/legacy-job'
        self.assertIsNone(self.client.get(url+'/diagnostic-snapshot',headers=self.engineer).json())
        job=self.client.get(url,headers=self.engineer).json()
        job['diagnosis']='Revised conclusion'
        self.assertEqual(self.client.patch(url,headers=self.engineer,json=job).status_code,200)
        snapshot=self.client.get(url+'/diagnostic-snapshot',headers=self.engineer).json()
        self.assertEqual(snapshot['origin'],'legacy_capture')
        self.assertEqual(snapshot['payload']['diagnosis'],'Earlier recorded conclusion')
        self.assertIsNone(snapshot['payload']['answers'])

    def test_complete_service_workflow(self):
        c=self.client.post('/api/customers',headers=self.admin,json={'name':'Cedar House','address':'Example address'}).json()
        w=self.client.post('/api/work-orders',headers=self.admin,json={'title':'Inspect window','customer_id':c['id'],'assigned_engineer_id':self.engineer_id,'scheduled_for':'2026-09-15T10:00'}).json()
        self.assertEqual(w['status'],'Scheduled')
        answers={'camb_catching':True,'works_open':True,'compression_even':'No','witness_marks':True,'keep_position_verified':True}
        d=self.client.post('/api/diagnostics/run',headers=self.engineer,json={'module_id':'locking_camb_keep','answers':answers})
        self.assertEqual(d.status_code,200)
        j=self.job(module='locking_camb_keep',diagnostic_answers=answers,diagnosis='forged result',work_order_id=w['id']).json()
        self.assertEqual(j['diagnosis'],d.json()['title'])
        linked=self.client.get('/api/work-orders',headers=self.engineer).json()[0]
        self.assertEqual(linked['job_id'],j['id'])
        self.assertEqual(linked['status'],'In Progress')
        self.assertEqual(self.job(work_order_id=w['id']).status_code,409)
        j['work_done']='Adjusted keep & retested <closing>'
        j['outcome']='Adjusted / Resolved'
        self.assertEqual(self.client.patch('/api/jobs/'+j['id'],headers=self.engineer,json=j).status_code,200)
        self.assertEqual(len(self.client.get('/api/jobs',headers=self.engineer).json()),1)
        self.client.patch('/api/jobs/'+j['id']+'/approve',headers=self.engineer)
        a=self.client.post('/api/approvals',headers=self.engineer,json={'job_id':j['id'],'approval_type':'Replacement part','description':'Keep required','estimated_cost_pence':4500}).json()
        self.assertEqual(self.client.post('/api/approvals/'+a['id']+'/decision',headers=self.engineer,json={'status':'Approved'}).status_code,403)
        self.assertEqual(self.client.post('/api/approvals/'+a['id']+'/decision',headers=self.admin,json={'status':'Approved','decision_note':'Proceed'}).status_code,200)
        self.assertEqual(self.client.post('/api/approvals/'+a['id']+'/decision',headers=self.admin,json={'status':'Rejected'}).status_code,409)
        result={'confirmed_diagnosis':j['diagnosis'],'actual_repair':'Adjusted keep','resolved':True,'engineer_rating':5}
        self.assertEqual(self.client.post('/api/jobs/'+j['id']+'/learning',headers=self.engineer,json=result).status_code,200)
        self.assertEqual(self.client.get('/api/learning/metrics',headers=self.engineer).json()['records'],1)
        self.assertTrue(self.client.get('/api/notifications',headers=self.engineer).json())
        self.assertTrue(self.client.get('/api/audit',headers=self.admin).json())

    def test_cross_company_assignment_rejected(self):
        other=self.client.post('/api/register-company',json={'company_name':'Other','admin_name':'Other','email':'other@example.com','password':'strong-password'}).json()
        response=self.client.post('/api/work-orders',headers=self.admin,json={'title':'Invalid assignment','assigned_engineer_id':other['user']['id']})
        self.assertEqual(response.status_code,422)
        j=self.job().json()
        self.assertEqual(self.client.get('/api/jobs/'+j['id'],headers={'Authorization':'Bearer '+other['token']}).status_code,403)

    def test_photo_validation_and_access(self):
        j=self.job().json()
        path='/api/jobs/'+j['id']+'/photos'
        self.assertEqual(self.client.post(path,headers=self.engineer,files={'file':('bad.png',b'not an image','image/png')}).status_code,400)
        img=BytesIO();Image.new('RGB',(80,60),'green').save(img,format='PNG')
        p=self.client.post(path,headers=self.engineer,data={'phase':'after'},files={'file':('test.png',img.getvalue(),'image/png')}).json()
        self.assertEqual(self.client.get(p['url']).status_code,401)
        self.assertEqual(self.client.get(p['url'],headers=self.engineer).status_code,200)
        self.assertEqual(self.client.get('/uploads/test.png').status_code,404)

    def test_diagnostic_validation(self):
        self.assertEqual(self.client.post('/api/diagnostics/run',headers=self.engineer,json={'module_id':'french_door_clearance','answers':{}}).status_code,422)
        self.assertEqual(self.client.post('/api/diagnostics/run',headers=self.engineer,json={'module_id':'missing','answers':{}}).status_code,404)
        self.assertEqual(self.client.post('/api/diagnostics/run',headers=self.engineer,json={'module_id':'french_door_clearance','answers':{'top_clearance':'wrong'}}).status_code,422)

    def test_demo_opt_in_and_repeatable(self):
        self.assertEqual(self.client.post('/api/demo').status_code,404)
        os.environ['FENIQ_DEMO']='1'
        try:
            a=self.client.post('/api/demo?role=admin').json()
            b=self.client.post('/api/demo?role=admin').json()
            self.assertEqual(a['user']['id'],b['user']['id'])
            self.assertEqual(len(self.client.get('/api/jobs',headers={'Authorization':'Bearer '+a['token']}).json()),3)
        finally: os.environ['FENIQ_DEMO']='0'

    def test_pdf_with_special_characters(self):
        j=self.job(customer='A & B <Site>',engineer_notes='Check <closing> & locking',signature='Sam & Robin').json()
        r=self.client.get('/api/jobs/'+j['id']+'/report.pdf',headers=self.engineer)
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.content.startswith(b'%PDF'))
        from pypdf import PdfReader
        text=' '.join(p.extract_text() for p in PdfReader(BytesIO(r.content)).pages)
        self.assertIn('A & B <Site>',text)
        self.assertIn('Check <closing> & locking',text)

    def test_private_document_search_and_permissions(self):
        library=TEST_PATH/'library';library.mkdir(exist_ok=True)
        from reportlab.pdfgen.canvas import Canvas
        canvas=Canvas(str(library/'sample.pdf'))
        canvas.drawString(40,700,'Private test document');canvas.showPage();canvas.save()
        (library/'manifest.json').write_text(json.dumps({'documents':[{'id':'doc-test','title':'Window guide','category':'Installation','manufacturer':'Example','systems':['R9'],'filename':'sample.pdf','source_filename':'sample.pdf','company_ids':[1],'pages':[{'page':3,'text':'Check the glazing packer position.'}]}]}),encoding='utf-8')
        os.environ['FENIQ_DOCUMENT_ROOT']=str(library)
        try:
            matches=self.client.get('/api/documents?q=glazing+packer',headers=self.admin).json()
            self.assertEqual(matches[0]['matches'][0]['page'],3)
            self.assertNotIn('company_ids',matches[0])
            self.assertNotIn('filename',matches[0])
            self.assertEqual(self.client.get('/api/documents/doc-test/file').status_code,401)
            self.assertEqual(self.client.get('/api/documents/doc-test/file',headers=self.admin).status_code,200)
            rendered=self.client.get('/api/documents/doc-test/pages/1',headers=self.admin)
            self.assertEqual(rendered.status_code,200)
            self.assertTrue(rendered.content.startswith(b'\x89PNG'))
            self.assertEqual(self.client.get('/api/documents/doc-test/pages/1').status_code,401)
            self.assertEqual(self.client.get('/api/documents/doc-test/pages/2',headers=self.admin).status_code,404)
            other=self.client.post('/api/register-company',json={'company_name':'External','admin_name':'External','email':'external@example.com','password':'strong-password'}).json()
            headers={'Authorization':'Bearer '+other['token']}
            self.assertEqual(self.client.get('/api/documents',headers=headers).json(),[])
            self.assertEqual(self.client.get('/api/documents/doc-test/file',headers=headers).status_code,404)
            self.assertEqual(self.client.get('/api/documents/doc-test/pages/1',headers=headers).status_code,404)
        finally: os.environ.pop('FENIQ_DOCUMENT_ROOT',None)

if __name__=='__main__': unittest.main()
