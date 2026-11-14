"""Local workforce planning UI. Run: python app.py --open"""
import argparse
import copy
import csv
import io
import json
import threading
import webbrowser
from urllib.error import URLError
from urllib.request import urlopen
from collections import Counter, defaultdict
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from workforce import SEED, analyze, generate, validate

ROOT = Path(__file__).resolve().parent


class PlanningData:
    def __init__(self, full=False):
        self.config = dict(employees=5000 if full else 100, skills=300 if full else 30,
                           projects=500 if full else 10, months=12, seed=SEED)
        self.tables, self.truth = generate(**self.config)
        self.gaps, self.utilization, self.findings = analyze(self.tables)
        self.tables['GapAnalysis'] = self.gaps
        self.employees = {r['employee_id']: r for r in self.tables['Employee']}
        self.roles = {r['role_id']: r['name'] for r in self.tables['Role']}
        self.skills = {r['skill_id']: r for r in self.tables['Skill']}
        self.projects = {r['project_id']: r for r in self.tables['Project']}
        self.demands = {r['demand_id']: r for r in self.tables['DemandPlan']}
        self.profiles = {(r['employee_id'], r['skill_id']): r for r in self.tables['EmployeeSkill']}
        self.available = {(r['employee_id'], r['period']): r for r in self.tables['Availability']}
        self.util_map = {(r['employee_id'], r['period']): r for r in self.utilization}
        self.allocations = defaultdict(list)
        self.employee_allocations = defaultdict(list)
        for a in self.tables['Allocation']:
            self.allocations[a['demand_id']].append(a)
            self.employee_allocations[(a['employee_id'], self.demands[a['demand_id']]['period'])].append(a)
        self.rows = [dict(**g, **{k: v for k, v in self.demands[g['demand_id']].items() if k not in g},
                          project_name=self.projects[self.demands[g['demand_id']]['project_id']]['name'],
                          role_name=self.roles[self.demands[g['demand_id']]['role_id']],
                          skill_name=self.skills[self.demands[g['demand_id']]['skill_id']]['name']) for g in self.gaps]
        self.errors = validate(self.tables)

    def filtered(self, params, ignore_period=False):
        return [r for r in self.rows if
                (ignore_period or not params.get('period') or r['period'] == params['period']) and
                (not params.get('project') or r['project_id'] == params['project']) and
                (not params.get('role') or r['role_id'] == params['role'])]

    def people(self, params):
        period = params.get('period') or '2026-01'
        project = params.get('project')
        ids = None
        if project:
            ids = {a['employee_id'] for a in self.tables['Allocation'] if self.demands[a['demand_id']]['project_id'] == project and self.demands[a['demand_id']]['period'] == period}
        rows = []
        for e in self.employees.values():
            if params.get('role') and e['role_id'] != params['role']: continue
            if ids is not None and e['employee_id'] not in ids: continue
            if params.get('q') and params['q'].lower() not in (e['name']+' '+e['employee_id']).lower(): continue
            u = self.util_map[(e['employee_id'], period)]
            if params.get('risk') and params['risk'] != u['risk']: continue
            rows.append(dict(**e, **{k: v for k, v in u.items() if k not in e}, role_name=self.roles[e['role_id']], leave_hours=self.available[(e['employee_id'],period)]['leave_hours']))
        return sorted(rows, key=lambda r: (-r['utilization_pct'], r['employee_id']))

    def dashboard(self, params):
        rows = self.filtered(params)
        people = self.people(params)
        trend = []
        annual = self.filtered(params, ignore_period=True)
        for m in range(1,13):
            month=f'2026-{m:02}'
            subset=[r for r in annual if r['period']==month]
            trend.append(dict(period=month, required=sum(r['required_hours'] for r in subset), qualified=sum(r['qualified_hours'] for r in subset), gap=sum(r['gap_hours'] for r in subset)))
        required=sum(r['required_hours'] for r in rows)
        qualified=sum(r['qualified_hours'] for r in rows)
        availability=sum(r['available_hours'] for r in people)
        allocated=sum(r['allocated_hours'] for r in people)
        roles=[]
        for role_id,name in self.roles.items():
            group=[r for r in rows if r['role_id']==role_id]
            roles.append(dict(name=name,required=sum(r['required_hours'] for r in group),qualified=sum(r['qualified_hours'] for r in group),gap=sum(r['gap_hours'] for r in group)))
        actions=Counter(r['recommendation'] for r in rows)
        return dict(config=self.config,projects=list(self.projects.values()),roles=self.tables['Role'],
                    metrics=dict(required=required,qualified=qualified,gap=required-qualified,coverage=round(qualified/required*100,1) if required else 0,available=availability,allocated=allocated,utilization=round(allocated/availability*100,1) if availability else 0,overallocated=sum(r['risk']=='overallocated' for r in people),people=len(people)),
                    trend=trend,role_breakdown=roles,actions=actions,demands=rows,
                    capacity_scope='All assignments of people assigned to this project in the selected month.' if params.get('project') else 'All employees in the selected role and month.',
                    checks=dict(passed=not self.errors,errors=self.errors,known_anomaly_recall=len({tuple(r.values()) for r in self.truth} & {tuple(r.values()) for r in self.findings})/len(self.truth),row_counts={k:len(v) for k,v in self.tables.items()}))

    def detail(self, demand_id):
        gap=next((r for r in self.rows if r['demand_id']==demand_id),None)
        if gap is None: raise ValueError('Select a canonical demand row')
        allocations=[]
        for a in self.allocations[demand_id]:
            e=self.employees[a['employee_id']]
            s=self.profiles.get((a['employee_id'],gap['skill_id']))
            current=bool(s and 0 <= (date.fromisoformat(gap['period']+'-01')-date.fromisoformat(s['last_verified'])).days<=365)
            reasons=[]
            if e['role_id']!=gap['role_id']: reasons.append('Role does not match')
            if not s: reasons.append('Required skill missing')
            elif s['proficiency']<gap['min_proficiency']: reasons.append('Proficiency below requirement')
            if s and not current: reasons.append('Skill verification expired')
            u=self.util_map[(e['employee_id'],gap['period'])]
            allocations.append(dict(**a,employee_name=e['name'],role_name=self.roles[e['role_id']],profile=s,qualified=not reasons,reasons=reasons,utilization=u))
        events=[r for r in self.tables['Event'] if r['record_id'] in {demand_id,gap['project_id']}]
        return dict(demand=gap,allocations=allocations,events=events,candidate=self.employees.get(gap['candidate_id']))

    def employee(self, employee_id, period):
        e=self.employees[employee_id]
        profiles=[dict(**s,skill_name=self.skills[s['skill_id']]['name'],current=0<=(date.fromisoformat(period+'-01')-date.fromisoformat(s['last_verified'])).days<=365) for s in self.tables['EmployeeSkill'] if s['employee_id']==employee_id]
        allocations=[dict(**a,project_name=self.projects[self.demands[a['demand_id']]['project_id']]['name']) for a in self.employee_allocations[(employee_id,period)]]
        return dict(employee=e,role_name=self.roles[e['role_id']],profiles=profiles,availability=self.available[(employee_id,period)],utilization=self.util_map[(employee_id,period)],allocations=allocations,training=[t for t in self.tables['Training'] if t['employee_id']==employee_id])

    def scenario(self, payload):
        demand_id=payload.get('demand_id')
        before=next((g for g in self.gaps if g['demand_id']==demand_id),None)
        hours=payload.get('required_hours')
        if before is None or type(hours) is not int or not 0<=hours<=10000:
            raise ValueError('Use a canonical demand and 0..10,000 integer hours')
        if type(payload.get('refresh_skills',False)) is not bool: raise ValueError('Invalid verification option')
        tables=copy.deepcopy(self.tables)
        d=next(d for d in tables['DemandPlan'] if d['demand_id']==demand_id)
        d['required_hours']=hours
        changed=0
        if payload.get('refresh_skills'):
            ids={a['employee_id'] for a in self.allocations[demand_id]}
            for s in tables['EmployeeSkill']:
                if s['employee_id'] in ids and s['skill_id']==d['skill_id']:
                    s['last_verified']=d['period']+'-01'; changed+=1
        gaps,_,_=analyze(tables)
        after=next(g for g in gaps if g['demand_id']==demand_id)
        return dict(before=before,after=after,profiles_reverified=changed,persisted=False)


DATA={}
LOCK=threading.Lock()

def get_data(scale):
    if scale not in {'starter','full'}: raise ValueError('Unknown dataset')
    with LOCK:
        if scale not in DATA: DATA[scale]=PlanningData(scale=='full')
    return DATA[scale]


class Handler(BaseHTTPRequestHandler):
    def send(self, body, content_type='application/json', status=200, filename=None):
        raw=body if isinstance(body,bytes) else (json.dumps(body).encode() if content_type=='application/json' else body.encode())
        self.send_response(status)
        self.send_header('Content-Type',content_type+'; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        url=urlparse(self.path)
        p={k:v[0] for k,v in parse_qs(url.query).items()}
        try:
            static={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
            if url.path in static:
                name,mime=static[url.path]; return self.send((ROOT/'web'/name).read_bytes(),mime)
            if not url.path.startswith('/api/'): return self.send({'error':'Not found'},status=404)
            data=get_data(p.get('scale','starter'))
            p.setdefault('period','2026-01')
            if p.get('period') and p['period'] not in {f'2026-{i:02}' for i in range(1,13)}: raise ValueError('Invalid month')
            if url.path=='/api/dashboard': return self.send(data.dashboard(p))
            if url.path=='/api/people':
                rows=data.people(p); return self.send(dict(rows=rows[:100],total=len(rows)))
            if url.path=='/api/demand': return self.send(data.detail(p['id']))
            if url.path=='/api/employee': return self.send(data.employee(p['id'],p.get('period','2026-01')))
            if url.path=='/api/exceptions':
                truth={(r['entity'],r['record_id'],r['issue_type']) for r in data.truth}
                rows=[dict(**f,injected=(f['entity'],f['record_id'],f['issue_type']) in truth) for f in data.findings]
                if p.get('issue'): rows=[r for r in rows if r['issue_type']==p['issue']]
                return self.send(dict(rows=rows[:200],total=len(rows),counts=Counter(r['issue_type'] for r in data.findings),scope='Entire dataset; global planning filters do not apply.'))
            if url.path=='/api/download':
                name=p.get('table','GapAnalysis')
                exports={**data.tables,'utilization':data.utilization,'findings':data.findings,'ground_truth':data.truth}
                if name not in exports: raise ValueError('Unknown export')
                rows=exports[name]; buf=io.StringIO(newline='')
                if rows:
                    writer=csv.DictWriter(buf,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
                return self.send(buf.getvalue(),'text/csv',filename=name+'.csv')
            return self.send({'error':'Not found'},status=404)
        except (ValueError,KeyError) as e: return self.send({'error':str(e)},status=400)

    def do_POST(self):
        try:
            if urlparse(self.path).path!='/api/scenario': return self.send({'error':'Not found'},status=404)
            if self.headers.get('Origin') and self.headers['Origin'] != 'http://'+self.headers.get('Host',''):
                return self.send({'error':'Only same-origin scenarios allowed'},status=403)
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=4096: raise ValueError('Invalid payload size')
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict): raise ValueError('Expected a scenario object')
            return self.send(get_data(payload.get('scale','starter')).scenario(payload))
        except (ValueError,KeyError,TypeError) as e: return self.send({'error':str(e)},status=400)


class LocalServer(ThreadingHTTPServer):
    # Windows permits two listeners on the same port when SO_REUSEADDR is set.
    allow_reuse_address = False


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=8000)
    p.add_argument('--open',action='store_true',help='Open the local app in your default browser')
    args=p.parse_args()
    url=f'http://127.0.0.1:{args.port}'
    try:
        server=LocalServer(('127.0.0.1',args.port),Handler)
    except OSError:
        try:
            with urlopen(url,timeout=2) as response:
                existing=b'<title>Workforce Compass' in response.read(8192)
        except (URLError,OSError): existing=False
        if existing:
            print(f'Workforce Compass is already running at {url}',flush=True)
            if args.open: webbrowser.open(url)
            return
        p.exit(1,f'Port {args.port} is in use. Try --port {args.port+1}\n')
    get_data('starter')
    print(f'Workforce Compass is running at {url}\nPress Ctrl+C to stop.',flush=True)
    if args.open: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()
