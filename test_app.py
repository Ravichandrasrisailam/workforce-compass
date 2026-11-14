import copy
import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from app import DATA, Handler, PlanningData


class PlanningUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=PlanningData()
        DATA['starter']=cls.data
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def get(self,path):
        with urllib.request.urlopen(self.base+path) as response:
            return response.read(),response.headers

    def test_dashboard_reconciles_filters_and_annual_trend(self):
        p=dict(period='2026-01',project='PRJ-2026-000002')
        d=self.data.dashboard(p)
        self.assertEqual(len(d['demands']),1)
        self.assertEqual(d['metrics']['required'],d['metrics']['qualified']+d['metrics']['gap'])
        self.assertEqual(len(d['trend']),12)
        self.assertTrue(all(r['project_id']==p['project'] for r in d['demands']))
        self.assertGreater(d['metrics']['people'],0)

    def test_detail_qualification_matches_engine(self):
        for g in self.data.gaps[:20]:
            d=self.data.detail(g['demand_id'])
            qualified=sum(a['hours'] for a in d['allocations'] if a['qualified'])
            self.assertEqual(g['qualified_hours'],min(qualified,g['required_hours']))

    def test_scenario_changes_result_without_changing_sources(self):
        source=copy.deepcopy(self.data.tables)
        demand=self.data.gaps[0]
        result=self.data.scenario(dict(demand_id=demand['demand_id'],required_hours=0,refresh_skills=True))
        self.assertEqual(result['after']['gap_hours'],0)
        self.assertEqual(result['after']['recommendation'],'none')
        self.assertFalse(result['persisted'])
        self.assertEqual(source,self.data.tables)
        with self.assertRaises(ValueError): self.data.scenario(dict(demand_id=demand['demand_id'],required_hours=-1))

    def test_http_static_download_and_invalid_input(self):
        body,_=self.get('/')
        self.assertIn(b'Workforce Compass',body)
        body,_=self.get('/api/dashboard?period=2026-01')
        self.assertEqual(json.loads(body)['metrics']['required'],2000)
        body,headers=self.get('/api/download?table=GapAnalysis')
        self.assertIn('attachment',headers['Content-Disposition'])
        self.assertIn(b'gap_id,demand_id',body)
        with self.assertRaises(urllib.error.HTTPError) as error:self.get('/api/dashboard?period=invalid')
        self.assertEqual(error.exception.code,400)
        error.exception.close()
        with self.assertRaises(urllib.error.HTTPError) as error:self.get('/api/download?table=../../README.md')
        self.assertEqual(error.exception.code,400)
        error.exception.close()

    def test_scenario_http_and_origin_protection(self):
        payload=json.dumps(dict(demand_id=self.data.gaps[0]['demand_id'],required_hours=80)).encode()
        req=urllib.request.Request(self.base+'/api/scenario',data=payload,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as r:self.assertEqual(json.load(r)['after']['required_hours'],80)
        req.add_header('Origin','http://unrelated.example')
        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
        self.assertEqual(error.exception.code,403)
        error.exception.close()

    def test_employee_capacity_and_exceptions(self):
        d=self.data.employee('EMP-000001','2026-01')
        a=d['availability']
        self.assertEqual(a['available_hours'],d['employee']['weekly_hours']*4-a['leave_hours'])
        body,_=self.get('/api/exceptions')
        found=json.loads(body)
        self.assertEqual(len(found['counts']),4)
        self.assertTrue(any(r['injected'] for r in found['rows']))

if __name__=='__main__':unittest.main()
