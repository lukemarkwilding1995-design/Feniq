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

    def passport(self):
        customer=self.client.post('/api/customers',headers=self.admin,json={'name':'Passport customer'}).json()
        site=self.client.post('/api/sites',headers=self.admin,json={'customer_id':customer['id'],'name':'Site A','address':'Fictional site'}).json()
        return self.client.post('/api/passports',headers=self.admin,json={'site_id':site['id'],'label':'Kitchen window','product':'Window'}).json()

    def test_reviewed_citation_exactness_history_and_pdf(self):
        import hashlib
        from reportlab.pdfgen.canvas import Canvas
        from pypdf import PdfReader
        library=TEST_PATH/'citation-library';library.mkdir(exist_ok=True)
        path=library/'fixture.pdf';canvas=Canvas(str(path))
        quote='Fictional source: inspect the sample hinge before adjustment.'
        canvas.drawString(40,700,quote);canvas.showPage();canvas.drawString(40,700,'Unreviewed second page');canvas.showPage();canvas.save()
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        (library/'manifest.json').write_text(json.dumps({'documents':[{'id':'citation-fixture','title':'Fictional citation guide','manufacturer':'Test only','revision':'1','category':'Test','filename':'fixture.pdf','sha256':digest,'company_ids':[1],'page_count':2,'pages':[]}]}),encoding='utf-8')
        os.environ['FENIQ_DOCUMENT_ROOT']=str(library)
        try:
            job=self.job(approved_by_engineer=True).json();url='/api/jobs/'+job['id']+'/citations'
            source='/api/documents/citation-fixture'
            self.assertEqual(self.client.get(source+'/reviewed-pages/1',headers=self.engineer).status_code,409)
            review={'document_sha256':digest,'status':'Approved for reference','title':'Fictional citation guide','manufacturer':'Test only','revision':'1','applicability':'Fictional testing only','page_start':1,'page_end':1,'note':'Synthetic review','attested':True}
            result=self.client.post(source+'/reviews',headers=self.admin,json=review).json()
            page=self.client.get(source+'/reviewed-pages/1',headers=self.engineer).json()
            self.assertIn(quote,page['text'])
            search='/api/jobs/'+job['id']+'/reviewed-evidence'
            found=self.client.get(search,headers=self.engineer,params={'q':'sample hinge'}).json()
            self.assertEqual(len(found['results']),1)
            self.assertEqual(found['results'][0]['page'],1)
            self.assertEqual(found['results'][0]['document_sha256'],digest)
            self.assertIn(quote,found['results'][0]['excerpt'])
            self.assertFalse(found['limited'])
            for query in [{'q':'unreviewed second'},{'q':'invented value'},{'q':'hinge','applicability':'different system'}]:
                self.assertEqual(self.client.get(search,headers=self.engineer,params=query).json()['results'],[])
            other=self.client.post('/api/register-company',json={'company_name':'Evidence outsider','admin_name':'Other','email':'evidence-other@example.com','password':'strong-password'}).json()
            self.assertIn(self.client.get(search,headers={'Authorization':'Bearer '+other['token']},params={'q':'hinge'}).status_code,[403,404])
            self.assertEqual(self.client.get(search,headers=self.engineer,params={'q':'!!'}).status_code,422)

            self.assertEqual(self.client.get(source+'/reviewed-pages/2',headers=self.engineer).status_code,422)
            data={'document_id':'citation-fixture','review_id':result['id'],'page':1,'excerpt':'Invented source specification','relevance':'Fictional hinge investigation'}
            self.assertEqual(self.client.post(url,headers=self.engineer,json=data).status_code,422)
            data['excerpt']=quote
            approval=self.client.post('/api/approvals',headers=self.engineer,json={'job_id':job['id'],'approval_type':'Test','description':'Pending scope'}).json()
            self.assertEqual(self.client.post(url,headers=self.engineer,json=data).status_code,200)
            self.assertTrue(self.client.post(url,headers=self.engineer,json=data).json()['already_attached'])
            self.assertFalse(self.client.get('/api/jobs/'+job['id'],headers=self.engineer).json()['approved_by_engineer'])
            self.client.patch('/api/jobs/'+job['id']+'/approve',headers=self.engineer)
            self.assertEqual(self.client.post('/api/approvals/'+approval['id']+'/decision',headers=self.admin,json={'status':'Approved'}).status_code,409)
            self.assertEqual(len(self.client.get(url,headers=self.engineer).json()),1)
            self.assertTrue(self.client.get(url,headers=self.engineer).json()[0]['current'])
            review.update(previous_id=result['id'],status='Withdrawn')
            self.assertEqual(self.client.post(source+'/reviews',headers=self.admin,json=review).status_code,200)
            self.assertFalse(self.client.get(url,headers=self.engineer).json()[0]['current'])
            self.assertEqual(self.client.get(search,headers=self.engineer,params={'q':'hinge'}).json()['results'],[])
            self.assertEqual(self.client.post(url,headers=self.engineer,json=data).status_code,409)
            pdf=self.client.get('/api/jobs/'+job['id']+'/report.pdf',headers=self.engineer)
            self.assertEqual(pdf.status_code,200)
            text_content=' '.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
            self.assertIn(quote,text_content);self.assertIn('Historical citation',text_content)
            (TEST_PATH/'citation-report.pdf').write_bytes(pdf.content)
            with self.assertRaises(IntegrityError):
                with engine.begin() as connection:connection.execute(text('DELETE FROM inspection_citations'))
        finally:os.environ.pop('FENIQ_DOCUMENT_ROOT',None)

    def test_controlled_source_review_history_and_changed_bytes(self):
        import hashlib
        from reportlab.pdfgen.canvas import Canvas
        library=TEST_PATH/'review-library';library.mkdir(exist_ok=True)
        path=library/'fictional.pdf';canvas=Canvas(str(path));canvas.drawString(40,700,'Fictional test manufacturer guide - Revision 1');canvas.showPage();canvas.save()
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        (library/'manifest.json').write_text(json.dumps({'documents':[{'id':'review-test','title':'Fictional guide','manufacturer':'Test only','revision':'1','category':'Test','filename':'fictional.pdf','sha256':digest,'company_ids':[1],'page_count':1,'pages':[]}]}),encoding='utf-8')
        os.environ['FENIQ_DOCUMENT_ROOT']=str(library)
        try:
            url='/api/documents/review-test/reviews'
            data={'document_sha256':digest,'status':'Approved for reference','title':'Fictional guide','manufacturer':'Test only','revision':'1','applicability':'Fictional product only; not a real specification','page_start':1,'page_end':1,'note':'Synthetic fixture review','attested':False}
            self.assertEqual(self.client.post(url,headers=self.engineer,json=data).status_code,403)
            self.assertEqual(self.client.post(url,headers=self.admin,json=data).status_code,422)
            data['attested']=True
            approved=self.client.post(url,headers=self.admin,json=data)
            self.assertEqual(approved.status_code,200)
            self.assertTrue(self.client.get('/api/documents',headers=self.engineer).json()[0]['source_review']['reference_approved'])
            self.assertEqual(self.client.post(url,headers=self.admin,json=data).status_code,409)
            path.write_bytes(path.read_bytes()+b'\nchanged source bytes')
            self.assertFalse(self.client.get('/api/documents',headers=self.admin).json()[0]['source_review']['reference_approved'])
            data['previous_id']=approved.json()['id']
            self.assertEqual(self.client.post(url,headers=self.admin,json=data).status_code,409)
            path.write_bytes(path.read_bytes().removesuffix(b'\nchanged source bytes'))
            data['status']='Withdrawn';data['note']='Reference approval withdrawn after further review'
            self.assertEqual(self.client.post(url,headers=self.admin,json=data).status_code,200)
            result=self.client.get(url,headers=self.admin).json()
            self.assertEqual(len(result['history']),2)
            self.assertFalse(result['current']['reference_approved'])
            with self.assertRaises(IntegrityError):
                with engine.begin() as connection:connection.execute(text('DELETE FROM source_reviews'))
            other=self.client.post('/api/register-company',json={'company_name':'External review','admin_name':'Other','email':'review-other@example.com','password':'strong-password'}).json()
            self.assertEqual(self.client.get(url,headers={'Authorization':'Bearer '+other['token']}).status_code,404)
        finally:os.environ.pop('FENIQ_DOCUMENT_ROOT',None)

    def test_technical_case_resolution_and_version_guards(self):
        job=self.job().json()
        created=self.client.post('/api/cases',headers=self.engineer,json={'title':'Recurring catch','description':'Investigate repeat fault','job_id':job['id']})
        self.assertEqual(created.status_code,200)
        case=created.json();url='/api/cases/'+case['id']
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':1,'status':'Closed','note':'Skip investigation'}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':1,'status':'Investigating','note':'Tests started'}).status_code,200)
        self.assertEqual(self.client.post(url+'/notes',headers=self.engineer,json={'version':1,'note':'Stale note'}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':2,'status':'Resolved','note':'No explanation'}).status_code,422)
        self.assertEqual(self.client.post(url+'/notes',headers=self.engineer,json={'version':2,'note':'Alignment checked'}).status_code,200)
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':3,'status':'Resolved','note':'Checks complete','resolution':'Alignment correction verified'}).status_code,200)
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':4,'status':'Closed','note':'Closed after review'}).status_code,200)
        self.assertEqual(self.client.post(url+'/notes',headers=self.engineer,json={'version':5,'note':'Cannot edit closed history'}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.engineer,json={'version':5,'status':'Investigating','note':'Reopen'}).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.admin,json={'version':5,'status':'Investigating','note':'Further investigation authorised'}).status_code,200)
        detail=self.client.get(url,headers=self.engineer).json()
        self.assertEqual(len(detail['events']),6)
        self.assertTrue(any('Alignment correction verified' in e['note'] for e in detail['events']))
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:connection.execute(text('DELETE FROM case_events'))

    def test_technical_case_ownership_and_link_boundaries(self):
        job=self.job().json();product=self.passport()
        data={'title':'Case','description':'Investigation','job_id':job['id'],'passport_id':product['id']}
        self.assertEqual(self.client.post('/api/cases',headers=self.engineer,json=data).status_code,422)
        self.client.post('/api/passports/'+product['id']+'/inspections',headers=self.engineer,json={'job_id':job['id']})
        case=self.client.post('/api/cases',headers=self.engineer,json=data).json();url='/api/cases/'+case['id']
        colleague=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Colleague','email':'case-colleague@example.com','password':'strong-password'}).json()
        headers={'Authorization':'Bearer '+colleague['token']}
        self.assertEqual(self.client.get('/api/cases',headers=headers).json(),[])
        self.assertEqual(self.client.get(url,headers=headers).status_code,403)
        self.assertEqual(self.client.patch(url,headers=self.admin,json={'version':1,'status':'Open','owner_id':colleague['user']['id'],'note':'Invalid assignment'}).status_code,422)
        other=self.client.post('/api/register-company',json={'company_name':'Other case company','admin_name':'Other','email':'case-other@example.com','password':'strong-password'}).json()
        external={'Authorization':'Bearer '+other['token']}
        self.assertEqual(self.client.get(url,headers=external).status_code,404)
        self.assertEqual(self.client.post('/api/cases',headers=external,json=data).status_code,404)

    def test_passport_lifecycle_and_retained_links(self):
        product=self.passport();url='/api/passports/'+product['id']
        job=self.job(reference='PASSPORT-TEST').json()
        self.assertEqual(self.client.post(url+'/inspections',headers=self.engineer,json={'job_id':job['id']}).status_code,200)
        self.assertEqual(self.client.post(url+'/inspections',headers=self.engineer,json={'job_id':job['id']}).status_code,200)
        self.assertEqual(self.client.post(url+'/events',headers=self.engineer,json={'kind':'Service note','occurred_on':'2026-09-13','note':'Adjusted and checked operation'}).status_code,200)
        detail=self.client.get(url,headers=self.engineer).json()
        self.assertEqual(len(detail['events']),3)
        self.assertEqual(detail['inspections'][0]['id'],job['id'])
        colleague=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Other engineer','email':'colleague@example.com','password':'strong-password'}).json()
        other_headers={'Authorization':'Bearer '+colleague['token']}
        self.assertEqual(self.client.get(url,headers=other_headers).json()['inspections'],[])
        self.assertEqual(self.client.post(url+'/inspections',headers=other_headers,json={'job_id':job['id']}).status_code,403)
        another=self.passport()
        self.assertEqual(self.client.post('/api/passports/'+another['id']+'/inspections',headers=self.admin,json={'job_id':job['id']}).status_code,409)
        for table in ('passport_events','passport_inspections'):
            with self.assertRaises(IntegrityError):
                with engine.begin() as connection: connection.execute(text('DELETE FROM '+table))

    def test_passport_company_and_admin_boundaries(self):
        product=self.passport();url='/api/passports/'+product['id']
        self.assertEqual(self.client.post('/api/passports',headers=self.engineer,json={'site_id':product['site_id'],'label':'Other','product':'Window'}).status_code,403)
        other=self.client.post('/api/register-company',json={'company_name':'External','admin_name':'External','email':'external@example.com','password':'strong-password'}).json()
        headers={'Authorization':'Bearer '+other['token']}
        self.assertEqual(self.client.get('/api/passports',headers=headers).json(),[])
        self.assertEqual(self.client.get(url,headers=headers).status_code,404)
        self.assertEqual(self.client.post('/api/passports',headers=headers,json={'site_id':product['site_id'],'label':'Invalid','product':'Door'}).status_code,404)
        self.assertEqual(self.client.post(url+'/events',headers=headers,json={'kind':'Service note','occurred_on':'2026-09-13','note':'Denied'}).status_code,404)
        self.assertEqual(self.client.post(url+'/events',headers=self.admin,json={'kind':'Service note','occurred_on':'invalid','note':'Invalid date'}).status_code,422)

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
