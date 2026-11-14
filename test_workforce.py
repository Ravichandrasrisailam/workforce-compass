import json
import tempfile
import unittest
from pathlib import Path
from workforce import generate, analyze, validate, export

class WorkforceTests(unittest.TestCase):
    def setUp(self):
        self.t,self.truth=generate(20,12,5,3)

    def test_reproducibility_and_exports(self):
        other,truth=generate(20,12,5,3)
        self.assertEqual(self.t,other)
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for out,t,labels in [(a,self.t,self.truth),(b,other,truth)]:
                gaps,util,findings=analyze(t); t['GapAnalysis']=gaps
                export(out,t,labels,util,findings,{})
            self.assertEqual(json.loads((Path(a)/'manifest.json').read_text()),json.loads((Path(b)/'manifest.json').read_text()))

    def test_edge_detection_and_no_label_dependency(self):
        gaps,util,findings=analyze(self.t)
        self.assertTrue({tuple(r.values()) for r in self.truth} <= {tuple(r.values()) for r in findings})
        self.assertEqual(len(gaps),15)
        self.assertTrue(all(g['required_hours']==g['qualified_hours']+g['gap_hours'] for g in gaps))
        self.assertTrue(any(r['risk']=='overallocated' for r in util))

    def test_validation_rejects_broken_parent_and_capacity(self):
        self.assertEqual(validate(self.t),[])
        self.t['Employee'][0]['role_id']='MISSING'
        self.t['Availability'][0]['available_hours']+=1
        errors=validate(self.t)
        self.assertIn('Employee: invalid role_id',errors)
        self.assertIn('Capacity reconciliation',errors)

    def test_expired_skill_cannot_cover_demand(self):
        for s in self.t['EmployeeSkill']: s['last_verified']='2020-01-01'
        gaps,_,_=analyze(self.t)
        self.assertTrue(all(g['qualified_hours']==0 for g in gaps))

    def test_seed_changes_data(self):
        self.assertNotEqual(self.t,generate(20,12,5,3,seed=7)[0])

if __name__=='__main__': unittest.main()
