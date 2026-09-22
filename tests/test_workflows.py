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

    def verification(self,job_id,result='Pass'):
        definition=self.client.get('/api/jobs/'+job_id+'/verification-definition',headers=self.engineer).json()
        return {'verification_definition_id':definition['id'],'verification_definition_sha256':definition['sha256'],
                'verification_answers':{check['key']:result for check in definition['checks']}}

    def test_auth_and_roles(self):
        self.assertEqual(self.client.get('/api/jobs').status_code,401)
        self.assertEqual(self.client.get('/api/company/users',headers=self.engineer).status_code,403)
        self.assertIsNone(self.client.get('/api/company',headers=self.engineer).json()['invite_code'])
        self.assertEqual(self.client.post('/api/login',json={'email':'admin@example.com','password':'wrong'}).status_code,401)
        self.assertEqual(self.client.post('/api/register-company',json={'company_name':'  ','admin_name':'Admin','email':'bad','password':'password'}).status_code,422)
        self.assertEqual(self.client.get('/api/commercial/dashboard',headers=self.engineer).status_code,403)
        self.assertIn('learning.dataset',self.client.get('/api/permissions',headers=self.admin).json()['permissions'])
        self.assertNotIn('learning.dataset',self.client.get('/api/permissions',headers=self.engineer).json()['permissions'])
        self.assertIn('privacy.manage',self.client.get('/api/permissions',headers=self.admin).json()['permissions'])
        self.assertNotIn('privacy.manage',self.client.get('/api/permissions',headers=self.engineer).json()['permissions'])

    def test_privacy_request_register_is_scoped_and_records_decisions_only(self):
        customer=self.client.post('/api/customers',headers=self.admin,json={'name':'Fictional customer'}).json()
        outsider=self.client.post('/api/register-company',json={'company_name':'Request outsider','admin_name':'Other','email':'requests-outside@example.com','password':'strong-password'}).json()
        outsider_auth={'Authorization':'Bearer '+outsider['token']}
        url='/api/privacy-requests'
        request={'customer_id':customer['id'],'kind':'Deletion','summary':'Fictional customer asked for review of stored records'}
        self.assertEqual(self.client.get(url,headers=self.engineer).status_code,403)
        self.assertEqual(self.client.post(url,headers=self.engineer,json=request).status_code,403)
        self.assertEqual(self.client.post(url,headers=outsider_auth,json=request).status_code,404)
        created=self.client.post(url,headers=self.admin,json=request)
        self.assertEqual(created.status_code,200)
        item=created.json();self.assertEqual(item['status'],'Open')
        self.assertEqual(self.client.get(url,headers=outsider_auth).json(),[])
        detail_url=url+'/'+item['id']
        self.assertEqual(self.client.get(detail_url,headers=outsider_auth).status_code,404)
        self.assertEqual(self.client.get(detail_url,headers=self.engineer).status_code,403)
        self.assertEqual(len(self.client.get(detail_url,headers=self.admin).json()['events']),1)
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json={'version':1,'status':'Closed','note':'Skip review','resolution':'Delete all'}).status_code,409)
        investigating={'version':1,'status':'Investigating','note':'Reviewing retained service records','resolution':''}
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json=investigating).status_code,200)
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json=investigating).status_code,409)
        scope_url=detail_url+'/inventory'
        review_url=detail_url+'/scope-review'
        self.assertEqual(self.client.get(scope_url,headers=self.engineer).status_code,403)
        self.assertEqual(self.client.get(scope_url,headers=outsider_auth).status_code,404)
        initial=self.client.get(scope_url,headers=self.admin).json()
        self.assertEqual(initial['inventory']['customer']['id'],customer['id'])
        self.assertEqual(initial['inventory']['inspections'],[])
        review={'version':2,'inventory_sha256':initial['inventory_sha256'],
                'identity_checked':True,'linked_records_checked':True,'unlinked_records_reviewed':True,
                'note':'Fictional identity and unlinked records reviewed manually'}
        self.assertEqual(self.client.post(review_url,headers=self.engineer,json=review).status_code,403)
        self.assertEqual(self.client.post(review_url,headers=outsider_auth,json=review).status_code,404)
        self.assertEqual(self.client.post(review_url,headers=self.admin,json={**review,'identity_checked':False}).status_code,422)
        self.assertEqual(self.client.post(review_url,headers=self.admin,json={**review,'inventory_sha256':'0'*64}).status_code,409)
        self.assertEqual(self.client.post(review_url,headers=self.admin,json=review).status_code,200)
        self.assertTrue(self.client.get(detail_url,headers=self.admin).json()['scope_ready'])
        self.assertEqual(self.client.post(review_url,headers=self.admin,json=review).status_code,409)
        closed={'version':3,'status':'Closed','note':'Review complete; no automatic changes','resolution':'Decision recorded for separate handling'}
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json={**closed,'resolution':''}).status_code,422)
        linked=self.client.post('/api/work-orders',headers=self.admin,json={'title':'Linked fictional visit','customer_id':customer['id']})
        self.assertEqual(linked.status_code,200)
        changed=self.client.get(scope_url,headers=self.admin).json()
        self.assertNotEqual(initial['inventory_sha256'],changed['inventory_sha256'])
        self.assertFalse(self.client.get(detail_url,headers=self.admin).json()['scope_ready'])
        self.assertEqual(changed['inventory']['work_orders'][0]['id'],linked.json()['id'])
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json=closed).status_code,409)
        self.assertEqual(self.client.post(review_url,headers=self.admin,json={**review,'version':3,'inventory_sha256':changed['inventory_sha256']}).status_code,200)
        self.assertTrue(self.client.get(detail_url,headers=self.admin).json()['scope_ready'])
        closed['version']=4
        self.assertEqual(self.client.patch(detail_url,headers=self.admin,json=closed).status_code,200)
        history=self.client.get(detail_url,headers=self.admin).json()
        self.assertEqual([event['status'] for event in history['events']],['Open','Investigating','Scope reviewed','Scope reviewed','Closed'])
        self.assertIn('Decision: Decision recorded for separate handling',history['events'][-1]['note'])
        self.assertEqual(history['request']['version'],5)
        self.assertEqual(self.client.get('/api/customers',headers=self.admin).json()[0]['name'],'Fictional customer')
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:connection.execute(text("UPDATE privacy_request_events SET note='changed'"))

    def test_access_draft_requires_current_review_and_stays_within_company(self):
        customer=self.client.post('/api/customers',headers=self.admin,json={
            'name':'Fictional access customer','email':'access@example.test'}).json()
        outsider=self.client.post('/api/register-company',json={
            'company_name':'Access outsider','admin_name':'Other','email':'access-outside@example.test',
            'password':'strong-password'}).json()
        outsider_auth={'Authorization':'Bearer '+outsider['token']}
        outsider_customer=self.client.post('/api/customers',headers=outsider_auth,json={
            'name':'Other private customer','email':'outside@example.test'}).json()
        outsider_job=self.client.post('/api/jobs',headers=outsider_auth,json={
            'customer':'Fictional access customer','fault':'Other tenant inspection','product':'Window'}).json()
        request=self.client.post('/api/privacy-requests',headers=self.admin,json={
            'customer_id':customer['id'],'kind':'Access','summary':'Fictional request for linked records'}).json()
        url='/api/privacy-requests/'+request['id']
        draft_url=url+'/access-preview'
        self.assertEqual(self.client.get(draft_url,headers=self.engineer).status_code,403)
        self.assertEqual(self.client.get(draft_url,headers=outsider_auth).status_code,404)
        self.assertEqual(self.client.get(draft_url,headers=self.admin).status_code,409)
        self.assertEqual(self.client.patch(url,headers=self.admin,json={
            'version':1,'status':'Investigating','note':'Checking fictional request'}).status_code,200)
        self.assertEqual(self.client.get(draft_url,headers=self.admin).status_code,409)
        site=self.client.post('/api/sites',headers=self.admin,json={
            'customer_id':customer['id'],'name':'Access site','address':'Fictional address'}).json()
        linked=self.client.post('/api/work-orders',headers=self.admin,json={
            'customer_id':customer['id'],'title':'Access-linked visit'}).json()
        unlinked=self.job(customer='  FICTIONAL ACCESS CUSTOMER  ',reference='UNLINKED-LEAD').json()
        inventory=self.client.get(url+'/inventory',headers=self.admin).json()
        self.assertEqual(inventory['inventory']['inspections'],[])
        self.assertEqual([row['id'] for row in inventory['inventory']['possible_unlinked_inspections']],
                         [unlinked['id']])
        self.assertNotIn(outsider_job['id'],json.dumps(inventory))
        review={'version':2,'inventory_sha256':inventory['inventory_sha256'],
                'identity_checked':True,'linked_records_checked':True,'unlinked_records_reviewed':True,
                'note':'Fictional requester and unlinked records checked'}
        self.assertEqual(self.client.post(url+'/scope-review',headers=self.admin,json=review).status_code,200)
        draft_response=self.client.get(draft_url,headers=self.admin)
        self.assertEqual(draft_response.status_code,200)
        self.assertEqual(draft_response.headers['cache-control'],'private, no-store')
        draft=draft_response.json()
        self.assertTrue(draft['draft_only'])
        self.assertEqual(draft['customer']['email'],'access@example.test')
        self.assertEqual(draft['sites'][0]['id'],site['id'])
        self.assertEqual(draft['work_orders'][0]['id'],linked['id'])
        self.assertEqual(draft['possible_unlinked_inspection_count'],1)
        self.assertNotIn(unlinked['id'],json.dumps(draft))
        self.assertNotIn(outsider_customer['id'],json.dumps(draft))
        self.assertEqual(self.client.get(url,headers=self.admin).json()['request']['version'],3)
        new_lead=self.job(customer='Fictional access customer',reference='NEW-LEAD').json()
        self.assertIn(new_lead['id'],json.dumps(self.client.get(url+'/inventory',headers=self.admin).json()))
        self.assertFalse(self.client.get(url,headers=self.admin).json()['scope_ready'])
        self.assertEqual(self.client.get(draft_url,headers=self.admin).status_code,409)
        self.assertEqual(self.client.post('/api/work-orders',headers=self.admin,json={
            'customer_id':customer['id'],'title':'New linked visit'}).status_code,200)
        self.assertEqual(self.client.get(draft_url,headers=self.admin).status_code,409)
        deletion=self.client.post('/api/privacy-requests',headers=self.admin,json={
            'customer_id':customer['id'],'kind':'Deletion','summary':'Fictional deletion review'}).json()
        self.assertEqual(self.client.get('/api/privacy-requests/'+deletion['id']+'/access-preview',
                                         headers=self.admin).status_code,409)

    def test_inspection_customer_link_is_explicit_and_company_scoped(self):
        customer=self.client.post('/api/customers',headers=self.admin,json={'name':'Linked fictional customer'}).json()
        other=self.client.post('/api/customers',headers=self.admin,json={'name':'Other fictional customer'}).json()
        outsider=self.client.post('/api/register-company',json={
            'company_name':'Link outsider','admin_name':'Other','email':'link-outside@example.test',
            'password':'strong-password'}).json()
        outside_auth={'Authorization':'Bearer '+outsider['token']}
        outside_customer=self.client.post('/api/customers',headers=outside_auth,json={'name':'Outside'}).json()
        self.assertEqual(self.job(customer_id=outside_customer['id']).status_code,404)
        direct=self.job(customer='Site label differs from customer name',customer_id=customer['id']).json()
        self.assertEqual(direct['customer_id'],customer['id'])
        snapshot=self.client.get('/api/jobs/'+direct['id']+'/diagnostic-snapshot',headers=self.engineer).json()
        self.assertEqual(snapshot['payload']['customer_id'],customer['id'])
        request=self.client.post('/api/privacy-requests',headers=self.admin,json={
            'customer_id':customer['id'],'kind':'Access','summary':'Review fictional linked inspection'}).json()
        inventory=self.client.get('/api/privacy-requests/'+request['id']+'/inventory',headers=self.admin).json()['inventory']
        self.assertIn(direct['id'],[row['id'] for row in inventory['inspections']])
        self.assertEqual(inventory['possible_unlinked_inspections'],[])
        self.assertEqual(self.client.patch('/api/jobs/'+direct['id'],headers=self.engineer,
                                           json={**direct,'customer_id':other['id']}).status_code,409)
        order=self.client.post('/api/work-orders',headers=self.admin,json={
            'title':'Linked visit','customer_id':customer['id'],'assigned_engineer_id':self.engineer_id}).json()
        self.assertEqual(self.job(work_order_id=order['id'],customer_id=other['id']).status_code,409)
        from_order=self.job(work_order_id=order['id']).json()
        self.assertEqual(from_order['customer_id'],customer['id'])
        self.assertEqual(self.client.patch('/api/work-orders/'+order['id'],headers=self.admin,
                                           json={**order,'job_id':from_order['id'],
                                                 'customer_id':other['id']}).status_code,409)

    def test_admin_customer_link_correction_retains_history_and_respects_other_links(self):
        first=self.client.post('/api/customers',headers=self.admin,json={'name':'Fictional first'}).json()
        second=self.client.post('/api/customers',headers=self.admin,json={'name':'Fictional second'}).json()
        outsider=self.client.post('/api/register-company',json={
            'company_name':'Correction outsider','admin_name':'Other',
            'email':'correction-outside@example.test','password':'strong-password'}).json()
        outside_auth={'Authorization':'Bearer '+outsider['token']}
        outside_customer=self.client.post('/api/customers',headers=outside_auth,json={'name':'Other tenant'}).json()
        job=self.job(customer='Fictional first',reference='LEGACY-1').json()
        url='/api/jobs/'+job['id']+'/customer-link'
        history_url='/api/jobs/'+job['id']+'/customer-link-history'
        context_url='/api/jobs/'+job['id']+'/customer-link-context'
        context_response=self.client.get(context_url,headers=self.admin)
        self.assertEqual(context_response.headers['cache-control'],'private, no-store')
        context=context_response.json()
        self.assertEqual(context['work_orders'],[])
        self.assertEqual(context['passports'],[])
        review={'expected_customer_id':None,'target_customer_id':first['id'],
                'context_sha256':context['context_sha256'],
                'identity_confirmed':True,'reason':'Verified fictional customer and original service record'}
        self.assertEqual(self.client.get(context_url,headers=self.engineer).status_code,403)
        self.assertEqual(self.client.get(context_url,headers=outside_auth).status_code,404)
        self.assertEqual(self.client.get(history_url,headers=self.engineer).status_code,403)
        self.assertEqual(self.client.post(url,headers=self.engineer,json=review).status_code,403)
        self.assertEqual(self.client.get(history_url,headers=outside_auth).status_code,404)
        self.assertEqual(self.client.post(url,headers=outside_auth,json=review).status_code,404)
        self.assertEqual(self.client.post(url,headers=self.admin,json={**review,'identity_confirmed':False}).status_code,422)
        self.assertEqual(self.client.post(url,headers=self.admin,json={**review,'target_customer_id':outside_customer['id']}).status_code,404)
        changed=self.client.post(url,headers=self.admin,json=review)
        self.assertEqual(changed.status_code,200)
        self.assertEqual(changed.json()['customer_id'],first['id'])
        self.assertEqual(self.client.post(url,headers=self.admin,json=review).status_code,409)
        history=self.client.get(history_url,headers=self.admin).json()
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]['old_customer_id'],None)
        self.assertEqual(history[0]['new_customer_id'],first['id'])
        self.assertEqual(history[0]['actor_name'],'Admin')
        original=self.client.get('/api/jobs/'+job['id']+'/diagnostic-snapshot',headers=self.engineer).json()
        self.assertIsNone(original['payload']['customer_id'])
        request=self.client.post('/api/privacy-requests',headers=self.admin,json={
            'customer_id':first['id'],'kind':'Access','summary':'Review corrected fictional inspection'}).json()
        inventory=self.client.get('/api/privacy-requests/'+request['id']+'/inventory',headers=self.admin).json()['inventory']
        self.assertEqual([row['id'] for row in inventory['inspections']],[job['id']])
        self.assertEqual(inventory['possible_unlinked_inspections'],[])
        fresh_context=self.client.get(context_url,headers=self.admin).json()
        moved=self.client.post(url,headers=self.admin,json={**review,
            'expected_customer_id':first['id'],'target_customer_id':second['id'],
            'context_sha256':fresh_context['context_sha256'],
            'reason':'Corrected to the verified second fictional customer'})
        self.assertEqual(moved.status_code,200)
        self.assertEqual(moved.json()['customer_id'],second['id'])
        first_inventory=self.client.get('/api/privacy-requests/'+request['id']+'/inventory',headers=self.admin).json()['inventory']
        self.assertEqual(first_inventory['inspections'],[])
        self.assertEqual(first_inventory['possible_unlinked_inspections'],[])
        self.assertEqual(len(first_inventory['historical_customer_link_leads']),2)
        self.assertEqual({row['inspection_id'] for row in first_inventory['historical_customer_link_leads']},
                         {job['id']})
        self.assertNotIn('reason',json.dumps(first_inventory['historical_customer_link_leads']))
        self.assertEqual(self.client.patch('/api/privacy-requests/'+request['id'],headers=self.admin,json={
            'version':1,'status':'Investigating','note':'Reviewing historical link lead'}).status_code,200)
        lead_scope=self.client.get('/api/privacy-requests/'+request['id']+'/inventory',headers=self.admin).json()
        self.assertEqual(self.client.post('/api/privacy-requests/'+request['id']+'/scope-review',headers=self.admin,json={
            'version':2,'inventory_sha256':lead_scope['inventory_sha256'],
            'identity_checked':True,'linked_records_checked':True,'unlinked_records_reviewed':True,
            'note':'Reviewed fictional former link as a separate lead'}).status_code,200)
        draft=self.client.get('/api/privacy-requests/'+request['id']+'/access-preview',headers=self.admin).json()
        self.assertEqual(draft['historical_customer_link_lead_count'],2)
        self.assertEqual(draft['inspections'],[])
        self.assertNotIn(job['id'],json.dumps(draft))
        second_context=self.client.get(context_url,headers=self.admin).json()
        self.assertEqual(self.client.post(url,headers=self.admin,json={**review,
            'expected_customer_id':second['id'],'target_customer_id':first['id'],
            'context_sha256':second_context['context_sha256'],
            'reason':'Returned to first fictional customer after review'}).status_code,200)
        self.assertEqual(len(self.client.get(history_url,headers=self.admin).json()),3)
        returned_inventory=self.client.get('/api/privacy-requests/'+request['id']+'/inventory',headers=self.admin).json()['inventory']
        self.assertEqual(returned_inventory['historical_customer_link_leads'],[])
        self.assertEqual(returned_inventory['inspections'][0]['customer_link_events']['count'],3)
        self.assertFalse(self.client.get('/api/privacy-requests/'+request['id'],headers=self.admin).json()['scope_ready'])
        before_order=self.client.get(context_url,headers=self.admin).json()
        order=self.client.post('/api/work-orders',headers=self.admin,json={
            'title':'Confirmed visit','customer_id':first['id'],'job_id':job['id'],
            'assigned_engineer_id':self.engineer_id}).json()
        after_order=self.client.get(context_url,headers=self.admin).json()
        self.assertNotEqual(before_order['context_sha256'],after_order['context_sha256'])
        self.assertEqual(after_order['work_orders'][0]['id'],order['id'])
        correction={**review,'expected_customer_id':first['id'],'target_customer_id':second['id'],
                    'reason':'Fictional correction after another identity check'}
        self.assertEqual(self.client.post(url,headers=self.admin,json=correction).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.admin,json={**correction,
            'context_sha256':after_order['context_sha256']}).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.admin,json={**correction,
            'context_sha256':after_order['context_sha256'],'target_customer_id':None}).status_code,409)
        self.assertEqual(self.client.patch('/api/work-orders/'+order['id'],headers=self.admin,
                                           json={**order,'customer_id':second['id']}).status_code,409)
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:
                connection.execute(text("UPDATE job_customer_link_events SET reason='tampered'"))
        site=self.client.post('/api/sites',headers=self.admin,json={
            'customer_id':second['id'],'name':'Other fictional site'}).json()
        passport=self.client.post('/api/passports',headers=self.admin,json={
            'site_id':site['id'],'label':'Other product','product':'Window'}).json()
        self.assertEqual(self.client.post('/api/passports/'+passport['id']+'/inspections',
                                          headers=self.engineer,json={'job_id':job['id']}).status_code,409)

    def passport(self):
        customer=self.client.post('/api/customers',headers=self.admin,json={'name':'Passport customer'}).json()
        site=self.client.post('/api/sites',headers=self.admin,json={'customer_id':customer['id'],'name':'Site A','address':'Fictional site'}).json()
        return self.client.post('/api/passports',headers=self.admin,json={'site_id':site['id'],'label':'Kitchen window','product':'Window'}).json()

    def test_outcome_revisions_verification_and_corrections(self):
        from pypdf import PdfReader
        job=self.job().json();url='/api/jobs/'+job['id']
        product=self.passport()
        self.assertEqual(self.client.post('/api/passports/'+product['id']+'/inspections',headers=self.engineer,json={'job_id':job['id']}).status_code,200)
        data={'confirmed_diagnosis':'Keep interference','actual_repair':'Adjusted keep','resolved':True,**self.verification(job['id'])}
        stale={**data,'verification_definition_sha256':'0'*64,'verification_checks':'Checked'}
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=stale).status_code,409)
        failed={**data,'verification_answers':dict(data['verification_answers']),'verification_checks':'Checked'}
        failed['verification_answers']['original_fault_rechecked']='Fail'
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=failed).status_code,422)
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=data).status_code,422)
        data['verification_checks']='Repeated opening and closing without catching'
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=data).status_code,200)
        first=self.client.get(url+'/outcome-history',headers=self.engineer).json()
        self.assertEqual(len(first),1);self.assertTrue(first[0]['integrity_valid'])
        self.assertFalse(first[0]['payload']['anonymised_for_learning'])
        self.assertEqual(first[0]['payload']['verification_definition']['revision'],1)
        self.assertTrue(all(value=='Pass' for value in first[0]['payload']['verification_answers'].values()))
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=data).status_code,409)
        data.update(expected_version=1,resolved=False)
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=data).status_code,422)
        data['change_reason']='Fault returned during extended check'
        self.assertEqual(self.client.post(url+'/learning',headers=self.engineer,json=data).status_code,200)
        rows=self.client.get(url+'/outcome-history',headers=self.engineer).json()
        self.assertEqual(len(rows),2);self.assertEqual(rows[0],first[0])
        self.assertFalse(rows[1]['payload']['resolved'])
        self.assertEqual(rows[0]['payload']['snapshot_sha256'],rows[1]['payload']['snapshot_sha256'])
        passport=self.client.get('/api/passports/'+product['id'],headers=self.engineer).json()
        linked=passport['inspections'][0]
        self.assertEqual(linked['outcome_revision_count'],2)
        self.assertEqual(linked['repair_outcome']['payload']['change_reason'],'Fault returned during extended check')
        report=self.client.get(url+'/report.pdf',headers=self.engineer)
        self.assertEqual(report.status_code,200)
        report_text=' '.join(page.extract_text() for page in PdfReader(BytesIO(report.content)).pages)
        self.assertIn('Latest repair outcome',report_text)
        self.assertIn('Repeated opening and closing without catching',report_text)
        self.assertIn('Fault returned during extended check',report_text)
        (TEST_PATH/'outcome-report.pdf').write_bytes(report.content)
        outsider=self.client.post('/api/register-company',json={'company_name':'Outcome outsider','admin_name':'Other','email':'outcome-outsider@example.com','password':'strong-password'}).json()
        self.assertIn(self.client.get(url+'/outcome-history',headers={'Authorization':'Bearer '+outsider['token']}).status_code,[403,404])
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:connection.execute(text('DELETE FROM outcome_revisions'))

    def test_governed_learning_review_tracks_exact_current_revision(self):
        job=self.job().json();base='/api/jobs/'+job['id']
        data={'confirmed_diagnosis':'Keep interference','actual_repair':'Adjusted keep',
              'resolved':True,'verification_checks':'Repeated operation without catching',
              'anonymised_for_learning':True,**self.verification(job['id'])}
        self.assertEqual(self.client.post(base+'/learning',headers=self.engineer,json=data).status_code,200)
        revision=self.client.get(base+'/outcome-history',headers=self.engineer).json()[-1]
        queue=self.client.get('/api/learning/review-queue',headers=self.admin)
        self.assertEqual(queue.status_code,200)
        self.assertEqual(len(queue.json()),1)
        self.assertEqual(queue.json()[0]['outcome_sha256'],revision['sha256'])
        self.assertEqual(self.client.get('/api/learning/review-queue',headers=self.engineer).status_code,403)
        request={'outcome_revision_id':queue.json()[0]['outcome_revision_id'],
                 'outcome_sha256':revision['sha256'],
                 'decision':'Prepare for de-identification','reason':'Complete checks and useful result'}
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.engineer,json=request).status_code,403)
        outsider=self.client.post('/api/register-company',json={'company_name':'Review outsider','admin_name':'Other','email':'review-outsider@example.com','password':'strong-password'}).json()
        outsider_auth={'Authorization':'Bearer '+outsider['token']}
        self.assertEqual(self.client.get('/api/learning/review-queue',headers=outsider_auth).json(),[])
        self.assertEqual(self.client.get('/api/learning/review-history',headers=outsider_auth).json()['items'],[])
        self.assertEqual(self.client.get('/api/learning/review-history',headers=self.engineer).status_code,403)
        self.assertEqual(self.client.post('/api/learning/reviews',headers=outsider_auth,json=request).status_code,404)
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json={**request,'outcome_sha256':'0'*64}).status_code,409)
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json=request).status_code,200)
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json=request).status_code,409)
        self.assertEqual(self.client.get('/api/learning/review-queue',headers=self.admin).json()[0]['review']['decision'],request['decision'])
        history=self.client.get('/api/learning/review-history',headers=self.admin).json()
        self.assertEqual(history['total'],1)
        self.assertEqual(history['items'][0]['status'],'Current')
        self.assertTrue(history['items'][0]['source_integrity_valid'])
        self.assertIsNone(history['next_offset'])
        self.assertEqual(self.client.get('/api/learning/review-history',headers=self.admin,params={'limit':101}).status_code,422)
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:connection.execute(text('UPDATE learning_reviews SET reason=\'changed\''))
        data.update(expected_version=1,change_reason='Follow-up check corrected the outcome',actual_repair='Readjusted keep')
        self.assertEqual(self.client.post(base+'/learning',headers=self.engineer,json=data).status_code,200)
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json=request).status_code,409)
        revised=self.client.get('/api/learning/review-queue',headers=self.admin).json()
        self.assertEqual(len(revised),1)
        self.assertEqual(revised[0]['outcome_version'],2)
        self.assertIsNone(revised[0]['review'])
        self.assertEqual(self.client.get('/api/learning/review-history',headers=self.admin).json()['items'][0]['status'],'Superseded')
        second={**request,'outcome_revision_id':revised[0]['outcome_revision_id'],
                'outcome_sha256':revised[0]['outcome_sha256'],'decision':'Exclude',
                'reason':'Needs further verification before use'}
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json=second).status_code,200)
        data.update(expected_version=2,change_reason='Customer withdrew learning consent',anonymised_for_learning=False)
        self.assertEqual(self.client.post(base+'/learning',headers=self.engineer,json=data).status_code,200)
        self.assertEqual(self.client.get('/api/learning/review-queue',headers=self.admin).json(),[])
        pages=[self.client.get('/api/learning/review-history',headers=self.admin,params={'limit':1,'offset':n}).json() for n in (0,1)]
        self.assertEqual([page['items'][0]['status'] for page in pages],['Consent withdrawn','Consent withdrawn'])
        self.assertEqual(pages[0]['next_offset'],1)
        self.assertIsNone(pages[1]['next_offset'])
        self.assertEqual({page['items'][0]['decision'] for page in pages}, {'Prepare for de-identification','Exclude'})

    def test_field_limited_dataset_requires_separate_current_approval(self):
        job=self.job(customer='Jane Smith at 12 Example Street',fault='Phone 07123 456789 reports a stiff handle',
                     product='Window',diagnosis='Possible keep interference',module='free-text-module').json()
        base='/api/jobs/'+job['id']
        outcome={'confirmed_diagnosis':'Possible keep interference',
                 'actual_repair':'Private customer note: call 07123 456789',
                 'engineer_feedback':'Jane Smith lives at 12 Example Street',
                 'resolved':False,'repeat_visit_required':True,
                 'remake_or_part_correct':'Not applicable','engineer_rating':4,
                 'anonymised_for_learning':True,**self.verification(job['id'])}
        self.assertEqual(self.client.post(base+'/learning',headers=self.engineer,json=outcome).status_code,200)
        candidates='/api/learning/dataset-candidates'
        self.assertEqual(self.client.get(candidates,headers=self.admin).json(),[])
        self.assertEqual(self.client.get(candidates,headers=self.engineer).status_code,403)
        review_item=self.client.get('/api/learning/review-queue',headers=self.admin).json()[0]
        first_review={'outcome_revision_id':review_item['outcome_revision_id'],
                      'outcome_sha256':review_item['outcome_sha256'],
                      'decision':'Prepare for de-identification','reason':'Fictional reviewed example'}
        self.assertEqual(self.client.post('/api/learning/reviews',headers=self.admin,json=first_review).status_code,200)
        candidate=self.client.get(candidates,headers=self.admin).json()[0]
        preview=candidate['preview']
        self.assertEqual(preview['schema_version'],1)
        self.assertEqual(preview['product_category'],'Window')
        self.assertEqual(preview['diagnostic_module'],'Unclassified')
        self.assertEqual(preview['diagnosis_match'],'Yes')
        self.assertTrue(preview['repeat_visit_required'])
        self.assertEqual(set(preview['verification_answers']),{'repair_matches_record','full_operation_cycle','original_fault_rechecked','safety_security_rechecked'})
        serialized=json.dumps(preview)
        for forbidden in ('Jane Smith','12 Example Street','07123','customer','actual_repair','job_id','engineer_feedback','free-text-module'):
            self.assertNotIn(forbidden,serialized)
        outsider=self.client.post('/api/register-company',json={'company_name':'Dataset outsider','admin_name':'Other','email':'dataset-outsider@example.com','password':'strong-password'}).json()
        outsider_auth={'Authorization':'Bearer '+outsider['token']}
        self.assertEqual(self.client.get(candidates,headers=outsider_auth).json(),[])
        self.assertEqual(self.client.get('/api/learning/internal-dataset',headers=outsider_auth).json()['count'],0)
        self.assertEqual(self.client.get('/api/learning/dataset-history',headers=outsider_auth).json()['items'],[])
        self.assertEqual(self.client.get('/api/learning/dataset-history',headers=self.engineer).status_code,403)
        decision={'outcome_revision_id':candidate['outcome_revision_id'],
                  'outcome_sha256':candidate['outcome_sha256'],
                  'preview_sha256':candidate['preview_sha256'],
                  'decision':'Approve local research','reason':'Field-limited preview checked'}
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=self.engineer,json=decision).status_code,403)
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=outsider_auth,json=decision).status_code,404)
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=self.admin,json={**decision,'preview_sha256':'0'*64}).status_code,409)
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=self.admin,json=decision).status_code,409)

        self.assertEqual(self.client.get('/api/learning/aggregate',headers=self.engineer).status_code,403)
        self.assertEqual(self.client.get('/api/learning/aggregate',headers=outsider_auth).json()['eligible_count'],0)
        second=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Second Admin','email':'second@example.com','password':'strong-password'}).json()
        second_auth={'Authorization':'Bearer '+second['token']}
        grant='/api/company/users/'+str(second['user']['id'])+'/grant-admin'
        self.assertEqual(self.client.post(grant,headers=self.engineer,json={'reason':'Independent review'}).status_code,403)
        self.assertEqual(self.client.post(grant,headers=outsider_auth,json={'reason':'Independent review'}).status_code,404)
        self.assertEqual(self.client.post(grant,headers=self.admin,json={'reason':'Independent review'}).status_code,200)
        self.assertEqual(self.client.post(grant,headers=self.admin,json={'reason':'Independent review'}).status_code,409)
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=second_auth,json=decision).status_code,200)
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=second_auth,json=decision).status_code,409)
        dataset=self.client.get('/api/learning/internal-dataset',headers=self.admin).json()
        self.assertEqual(dataset,{'count':1,'records':[preview]})
        aggregate=self.client.get('/api/learning/aggregate',headers=self.admin).json()
        self.assertEqual(aggregate,{'eligible_count':1,'minimum_count':5,'status':'Below threshold','summary':None})
        self.assertNotIn(job['id'],json.dumps(dataset))
        decision_history=self.client.get('/api/learning/dataset-history',headers=self.admin).json()
        self.assertEqual(decision_history['items'][0]['status'],'Current')
        self.assertTrue(decision_history['items'][0]['preview_integrity_valid'])
        self.assertTrue(decision_history['items'][0]['source_integrity_valid'])
        self.assertEqual(decision_history['total'],1)
        self.assertEqual(self.client.get('/api/learning/dataset-history',headers=self.admin,params={'limit':0}).status_code,422)
        with engine.connect() as connection:
            stored=connection.execute(text('SELECT preview_json FROM learning_dataset_decisions')).scalar()
        self.assertNotIn('Jane Smith',stored)
        self.assertNotIn('07123',stored)
        with self.assertRaises(IntegrityError):
            with engine.begin() as connection:connection.execute(text("UPDATE learning_dataset_decisions SET reason='changed'"))
        before=self.client.get(base+'/outcome-history',headers=self.engineer).json()[-1]
        withdrawal={'expected_version':before['version'],'expected_sha256':before['sha256'],
                    'reason':'Customer withdrew research consent'}
        withdraw=base+'/learning/withdraw-consent'
        self.assertEqual(self.client.post(withdraw,headers=outsider_auth,json=withdrawal).status_code,403)
        another=self.client.post('/api/join-company',json={'invite_code':self.invite,'name':'Unassigned Engineer','email':'unassigned@example.com','password':'strong-password'}).json()
        another_auth={'Authorization':'Bearer '+another['token']}
        self.assertEqual(self.client.post(withdraw,headers=another_auth,json=withdrawal).status_code,403)
        self.assertEqual(self.client.post(withdraw,headers=self.engineer,json={**withdrawal,'expected_sha256':'0'*64}).status_code,409)
        self.assertEqual(self.client.post(withdraw,headers=self.engineer,json={**withdrawal,'reason':'   '}).status_code,422)
        self.assertEqual(self.client.post(withdraw,headers=self.engineer,json=withdrawal).status_code,200)
        after=self.client.get(base+'/outcome-history',headers=self.engineer).json()
        self.assertEqual(after[-2],before)
        self.assertEqual(after[-1]['version'],before['version']+1)
        self.assertFalse(after[-1]['payload']['anonymised_for_learning'])
        self.assertEqual(after[-1]['payload']['snapshot_sha256'],before['payload']['snapshot_sha256'])
        self.assertEqual(after[-1]['payload']['actual_repair'],before['payload']['actual_repair'])
        self.assertEqual(after[-1]['payload']['origin'],'Learning consent withdrawal')
        self.assertEqual(self.client.post(withdraw,headers=self.engineer,json=withdrawal).status_code,409)
        self.assertFalse(self.client.get(base+'/learning',headers=self.engineer).json()['anonymised_for_learning'])
        self.assertEqual(self.client.get(candidates,headers=self.admin).json(),[])
        self.assertEqual(self.client.get('/api/learning/internal-dataset',headers=self.admin).json()['count'],0)
        self.assertEqual(self.client.get('/api/learning/dataset-history',headers=self.admin).json()['items'][0]['status'],'Consent withdrawn')
        self.assertEqual(self.client.post('/api/learning/dataset-decisions',headers=self.admin,json=decision).status_code,409)

    def test_aggregate_threshold_suppresses_small_cohorts(self):
        from unittest.mock import patch
        from app import learning_dataset
        rows=[{'resolved':True,'repeat_visit_required':False,'diagnosis_match':'Yes'} for _ in range(5)]
        with patch.object(learning_dataset,'internal_dataset',return_value={'count':4,'records':rows[:4]}):
            self.assertIsNone(learning_dataset.aggregate(None,1)['summary'])
        with patch.object(learning_dataset,'internal_dataset',return_value={'count':5,'records':rows}):
            report=learning_dataset.aggregate(None,1)
        self.assertEqual(report['status'],'Ready')
        self.assertEqual(report['summary'],{'records':5,'resolved':5,'repeat_visits':0,'diagnosis_matches':5})

    def test_reviewed_search_continuation_and_stale_scope(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        job=self.job().json();url='/api/jobs/'+job['id']+'/reviewed-evidence'
        review=SimpleNamespace(id='review-a',document_sha256='abc',page_start=1,page_end=105,applicability='Test',title='Synthetic',manufacturer='Test',revision='1')
        def page(db,company,identifier,number):return review,('target hinge' if number==105 else 'unrelated text')
        with patch('app.citations.records',return_value=[{'id':'synthetic'}]),patch('app.citations.latest',return_value=review),patch('app.citations.summary',return_value={'reference_approved':True}),patch('app.citations.reviewed_page',side_effect=page):
            first=self.client.get(url,headers=self.engineer,params={'q':'hinge'}).json()
            self.assertEqual(first['next_offset'],100);self.assertEqual(first['results'],[])
            params={'q':'hinge','offset':100,'snapshot':first['snapshot']}
            second=self.client.get(url,headers=self.engineer,params=params).json()
            self.assertEqual(second['results'][0]['page'],105);self.assertIsNone(second['next_offset'])
            self.assertEqual(second['scanned_pages'],5)
            self.assertEqual(self.client.get(url,headers=self.engineer,params={**params,'q':'changed'}).status_code,409)
            review.id='review-b'
            self.assertEqual(self.client.get(url,headers=self.engineer,params=params).status_code,409)
            self.assertEqual(self.client.get(url,headers=self.engineer,params={'q':'hinge','offset':100}).status_code,409)

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

    def test_passport_repeat_failure_analysis_uses_original_diagnoses(self):
        product=self.passport();base='/api/passports/'+product['id']
        first=self.job(reference='RF-1',diagnosis='Locking point interference').json()
        second=self.job(reference='RF-2',diagnosis='  locking POINT interference  ').json()
        omitted=self.job(reference='RF-3').json()
        for job in (first,second,omitted):
            self.assertEqual(self.client.post(base+'/inspections',headers=self.engineer,json={'job_id':job['id']}).status_code,200)
        resolved={'confirmed_diagnosis':'Locking point interference','actual_repair':'Adjusted keep','resolved':True,
                  'verification_checks':'Full operation cycle passed',**self.verification(first['id'])}
        self.assertEqual(self.client.post('/api/jobs/'+first['id']+'/learning',headers=self.engineer,json=resolved).status_code,200)
        unresolved={'confirmed_diagnosis':'Locking point interference','actual_repair':'Adjustment attempted','resolved':False,
                    'repeat_visit_required':True,'verification_checks':'Fault remained during operation',**self.verification(second['id'],'Fail')}
        self.assertEqual(self.client.post('/api/jobs/'+second['id']+'/learning',headers=self.engineer,json=unresolved).status_code,200)
        analysis=self.client.get(base,headers=self.engineer).json()['failure_analysis']
        self.assertEqual(analysis['visible_linked_inspections'],3)
        self.assertEqual(analysis['original_snapshot_cases'],3)
        self.assertEqual(analysis['latest_outcomes'],2)
        self.assertEqual(analysis['omitted_without_diagnosis'],1)
        self.assertEqual(len(analysis['patterns']),1)
        pattern=analysis['patterns'][0]
        self.assertEqual(pattern['cases'],2);self.assertEqual(pattern['resolved'],1)
        self.assertEqual(pattern['not_resolved'],1);self.assertEqual(pattern['repeat_visit_required'],1)
        self.assertEqual(pattern['signal'],'Repeated diagnosis');self.assertTrue(pattern['requires_review'])
        self.assertTrue(all(item['diagnosis_basis']=='Immutable original diagnosis' for item in pattern['occurrences']))
        changed=self.client.patch('/api/jobs/'+first['id'],headers=self.engineer,json={
            'customer':'Test site','fault':'Stiff handle','product':'Window','diagnosis':'Later edited diagnosis'
        })
        self.assertEqual(changed.status_code,200)
        unchanged=self.client.get(base,headers=self.engineer).json()['failure_analysis']['patterns'][0]
        self.assertEqual(unchanged['cases'],2)
        self.assertEqual(unchanged['diagnosis'],'Locking point interference')
        corrected={**unresolved,'resolved':True,'repeat_visit_required':False,
                   'verification_checks':'Fault cleared on a later fictional test',
                   'verification_answers':self.verification(second['id'])['verification_answers'],
                   'expected_version':1,'change_reason':'Later verification completed'}
        self.assertEqual(self.client.post('/api/jobs/'+second['id']+'/learning',headers=self.engineer,json=corrected).status_code,200)
        updated=self.client.get(base,headers=self.engineer).json()['failure_analysis']['patterns'][0]
        self.assertEqual(updated['cases'],2)
        self.assertEqual(updated['resolved'],2)
        self.assertEqual(updated['not_resolved'],0)
        self.assertEqual(updated['repeat_visit_required'],0)
        self.assertFalse(updated['requires_review'])
        self.assertEqual(self.client.get('/api/jobs/'+second['id']+'/outcome-history',headers=self.engineer).json()[0]['payload']['resolved'],False)

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
        saved=self.client.post('/api/jobs/'+job['id']+'/learning',headers=self.engineer,json={'confirmed_diagnosis':'Engineer revised conclusion','actual_repair':'Adjusted keep','resolved':True,'verification_checks':'Repeated operation completed without catching',**self.verification(job['id'])})
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
        result={'confirmed_diagnosis':j['diagnosis'],'actual_repair':'Adjusted keep','resolved':True,'engineer_rating':5,'verification_checks':'Repeated operation completed without catching',**self.verification(j['id'])}
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
