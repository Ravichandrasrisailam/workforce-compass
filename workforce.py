"""Reproducible workforce planning submission. Python standard library only."""
import argparse
import csv
import hashlib
import json
import random
import sqlite3
from datetime import date
from pathlib import Path

SEED = 20261022
SKILL_NAMES = [
    'Python', 'SQL', 'UX Research', 'Agile Delivery',
    'JavaScript', 'Data Modeling', 'UI Design', 'Stakeholder Management',
    'Java', 'Statistics', 'Prototyping', 'Project Scheduling',
    'Cloud Architecture', 'Power BI', 'Accessibility', 'Risk Management',
    'DevOps', 'Machine Learning', 'Design Systems', 'Budget Planning',
    'API Development', 'Data Engineering', 'Interaction Design', 'Resource Planning',
    'Cybersecurity', 'Forecasting', 'Service Design', 'Quality Assurance',
    'Software Testing', 'Data Visualization', 'Usability Testing', 'Change Management',
]

def generate(employees=100, skills=30, projects=10, months=12, seed=SEED):
    if min(employees, skills, projects) < 4 or not 1 <= months <= 12:
        raise ValueError('Counts must be >= 4; months must be 1..12')
    rng = random.Random(seed)
    tables = {n: [] for n in ['Role', 'Skill', 'Employee', 'EmployeeSkill', 'Project', 'DemandPlan', 'Allocation', 'Availability', 'Training', 'GapAnalysis', 'Event']}
    for i in range(1, 5):
        tables['Role'].append(dict(role_id=f'ROL-{i:06}', name=['Engineer', 'Analyst', 'Designer', 'Project Manager'][i-1]))
    for i in range(1, skills+1):
        name=SKILL_NAMES[(i-1)%len(SKILL_NAMES)]
        if i>len(SKILL_NAMES): name+=f' / specialization {(i-1)//len(SKILL_NAMES)+1:02}'
        tables['Skill'].append(dict(skill_id=f'SKL-{i:06}', name=name, category=['Engineering', 'Analytics', 'Design', 'Delivery'][(i-1)%4], validity_days=365))
    for i in range(1, employees+1):
        eid = f'EMP-{i:06}'
        tables['Employee'].append(dict(employee_id=eid, name=f'Synthetic Employee {i:06}', role_id=f'ROL-{(i-1)%4+1:06}', weekly_hours=rng.choice([20, 32, 40, 40, 40]), status='active', effective_from='2026-01-01'))
        for s in rng.sample(range(1, skills+1), min(6, skills)):
            tables['EmployeeSkill'].append(dict(employee_skill_id=f'ES-{len(tables["EmployeeSkill"])+1:07}', employee_id=eid, skill_id=f'SKL-{s:06}', proficiency=rng.randint(1,5), last_verified=rng.choice(['2024-12-01','2025-09-01','2025-12-15']), treated_current=0))
    for i in range(1, projects+1):
        tables['Project'].append(dict(project_id=f'PRJ-2026-{i:06}', name=f'Initiative {i:04}', status='active', start_date='2026-01-01', end_date='2026-12-31'))
    # Plan around real profiles; staffing intentionally includes both suitable and
    # unsuitable allocations so the skill checks reveal meaningful variation.
    employee_lookup={e['employee_id']:e for e in tables['Employee']}
    skill_lookup={}
    for profile in tables['EmployeeSkill']:
        key=(employee_lookup[profile['employee_id']]['role_id'],profile['skill_id'])
        skill_lookup.setdefault(key,[]).append(profile)
    for m in range(1, months+1):
        period=f'2026-{m:02}'
        for emp in tables['Employee']:
            base=emp['weekly_hours']*4
            leave=rng.choice([0,0,0,8,16,32])
            tables['Availability'].append(dict(availability_id=f'AV-{len(tables["Availability"])+1:08}', employee_id=emp['employee_id'], period=period, base_hours=base, leave_hours=leave, available_hours=base-leave))
        for p in tables['Project']:
            anchor=rng.choice(tables['EmployeeSkill'])
            role=employee_lookup[anchor['employee_id']]['role_id']
            dem=dict(demand_id=f'DEM-{p["project_id"]}-2026M{m:02}', project_id=p['project_id'], period=period, role_id=role, skill_id=anchor['skill_id'], min_proficiency=rng.randint(2,4), required_hours=rng.choice([80,160,240,320]), status='approved')
            tables['DemandPlan'].append(dem)
            eligible=[s for s in skill_lookup[(role,anchor['skill_id'])] if s['proficiency']>=dem['min_proficiency'] and (date(2026,m,1)-date.fromisoformat(s['last_verified'])).days<=365]
            chosen=[employee_lookup[s['employee_id']] for s in rng.sample(eligible,min(2,len(eligible)))]
            chosen_ids={e['employee_id'] for e in chosen}
            chosen+=rng.sample([e for e in tables['Employee'] if e['employee_id'] not in chosen_ids],3-len(chosen))
            for emp in chosen:
                tables['Allocation'].append(dict(allocation_id=f'ALLOC-2026-{len(tables["Allocation"])+1:06}', employee_id=emp['employee_id'], demand_id=dem['demand_id'], hours=rng.choice([40,80,120]), start_day=1, end_day=28))
    # Explicit, isolated edge-case injections. Labels never enter planner inputs.
    first=tables['Allocation'][0]
    first['hours']=400
    second=dict(first, allocation_id=f'ALLOC-2026-{len(tables["Allocation"])+1:06}', demand_id=tables['DemandPlan'][1]['demand_id'], hours=40)
    tables['Allocation'].append(second)
    stale=tables['EmployeeSkill'][0]
    stale.update(last_verified='2024-01-01', treated_current=1)
    duplicate=dict(tables['DemandPlan'][0], demand_id='DEM-DUPLICATE-2026M01')
    tables['DemandPlan'].append(duplicate)
    truth=[dict(entity='Allocation', record_id=first['allocation_id'], issue_type='allocation_exceeds_availability'), dict(entity='Allocation', record_id=second['allocation_id'], issue_type='overlapping_projects'), dict(entity='EmployeeSkill', record_id=stale['employee_skill_id'], issue_type='stale_skill_treated_current'), dict(entity='DemandPlan', record_id=duplicate['demand_id'], issue_type='demand_double_counted')]
    for i, emp in enumerate(tables['Employee'][:max(1,employees//20)],1):
        profile=next(s for s in tables['EmployeeSkill'] if s['employee_id']==emp['employee_id'])
        tables['Training'].append(dict(training_id=f'TRN-{i:06}', employee_id=emp['employee_id'], skill_id=profile['skill_id'], status='planned', start_date='2026-02-01', end_date='2026-03-01', target_proficiency=4))
    for entity in ['Employee','Project','DemandPlan','Training']:
        pk=next(iter(tables[entity][0]))
        for row in tables[entity]:
            tables['Event'].append(dict(event_id=f'EVT-{len(tables["Event"])+1:08}', entity=entity, record_id=row[pk], from_state='none', to_state=row['status'], effective_date='2026-01-01', event_type='created'))
    return tables, truth

def analyze(t):
    findings=[]
    demands={r['demand_id']:r for r in t['DemandPlan']}
    employees={r['employee_id']:r for r in t['Employee']}
    availability={(r['employee_id'],r['period']):r['available_hours'] for r in t['Availability']}
    profiles={(r['employee_id'],r['skill_id']):r for r in t['EmployeeSkill']}
    groups={}; assigned={}; seen={}; canonical=[]
    for d in t['DemandPlan']:
        key=tuple(d[k] for k in ['project_id','period','role_id','skill_id'])
        if key in seen:
            findings.append(dict(entity='DemandPlan',record_id=d['demand_id'],issue_type='demand_double_counted'))
        else:
            canonical.append(d); seen[key]=d['demand_id']
    for s in t['EmployeeSkill']:
        if s['treated_current'] and (date(2026,1,1)-date.fromisoformat(s['last_verified'])).days>365:
            findings.append(dict(entity='EmployeeSkill',record_id=s['employee_skill_id'],issue_type='stale_skill_treated_current'))
    for a in t['Allocation']:
        d=demands[a['demand_id']]; key=(a['employee_id'],d['period'])
        groups.setdefault(key,[]).append(a)
        assigned.setdefault(d['demand_id'],[]).append(a)
    utilization=[]
    for key, available in availability.items():
        rows=groups.get(key,[]); hours=sum(a['hours'] for a in rows)
        utilization.append(dict(employee_id=key[0],period=key[1],available_hours=available,allocated_hours=hours,utilization_pct=round(hours/available*100,2),risk='overallocated' if hours>available else 'underutilized' if hours<available*.6 else 'balanced'))
        for i,a in enumerate(rows):
            if hours>available:
                findings.append(dict(entity='Allocation',record_id=a['allocation_id'],issue_type='allocation_exceeds_availability'))
            if any(demands[b['demand_id']]['project_id'] != demands[a['demand_id']]['project_id'] and max(a['start_day'],b['start_day'])<=min(a['end_day'],b['end_day']) for b in rows[:i]):
                findings.append(dict(entity='Allocation',record_id=a['allocation_id'],issue_type='overlapping_projects'))
    gaps=[]
    by_skill={}
    for profile in t['EmployeeSkill']:
        by_skill.setdefault(profile['skill_id'],[]).append(profile)
    for d in canonical:
        qualified=0; allocated=0
        asof=date.fromisoformat(d['period']+'-01')
        for a in assigned.get(d['demand_id'],[]):
            allocated+=a['hours']; s=profiles.get((a['employee_id'],d['skill_id']))
            if s and s['proficiency']>=d['min_proficiency'] and 0<=(asof-date.fromisoformat(s['last_verified'])).days<=365 and employees[a['employee_id']]['role_id']==d['role_id']:
                qualified+=a['hours']
        covered=min(qualified,d['required_hours']); gap=d['required_hours']-covered
        candidates=[s['employee_id'] for s in by_skill.get(d['skill_id'],[]) if s['proficiency']==d['min_proficiency']-1 and employees[s['employee_id']]['role_id']==d['role_id'] and 0<=(asof-date.fromisoformat(s['last_verified'])).days<=365 and availability[(s['employee_id'],d['period'])]-sum(a['hours'] for a in groups.get((s['employee_id'],d['period']),[]))>=min(gap,40)] if gap else []
        gaps.append(dict(gap_id=f'GAP-{len(gaps)+1:07}',demand_id=d['demand_id'], required_hours=d['required_hours'],allocated_hours=allocated,qualified_hours=covered,gap_hours=gap,recommendation='none' if not gap else 'train' if candidates else 'hire',candidate_id=candidates[0] if candidates else '',assumption='Training requires one proficiency level and >= min(gap,40) free hours; hiring requires budget approval. Concurrent qualified assignments require manager review.'))
    return gaps, utilization, findings

def validate(t):
    errors=[]
    keys={name:{r[next(iter(r))] for r in rows} for name,rows in t.items() if rows}
    records={name:{r[next(iter(r))]:r for r in rows} for name,rows in t.items()}
    refs={'employee_id':'Employee','role_id':'Role','skill_id':'Skill','project_id':'Project','demand_id':'DemandPlan'}
    for name,rows in t.items():
        if rows and len(keys[name])!=len(rows): errors.append(f'{name}: duplicate primary key')
        for r in rows:
            pk=next(iter(r))
            for field,target in refs.items():
                if field in r and field!=pk and r[field] not in keys[target]: errors.append(f'{name}: invalid {field}')
            if name=='Availability' and (r['available_hours']!=r['base_hours']-r['leave_hours'] or r['available_hours']<0): errors.append('Capacity reconciliation')
            if 'start_date' in r and r['start_date']>r['end_date']: errors.append('Date order')
            if name=='EmployeeSkill' and not 1<=r['proficiency']<=5: errors.append('Proficiency enum')
            if name=='Allocation' and (r['hours']<0 or not 1<=r['start_day']<=r['end_day']<=31): errors.append('Allocation range')
            allowed={'Employee':{'active'},'Project':{'active'},'DemandPlan':{'approved'},'Training':{'planned','in_progress','completed','cancelled'}}
            if name in allowed and r['status'] not in allowed[name]: errors.append('Lifecycle enum')
            if name=='Event' and (r['from_state']!='none' or r['event_type']!='created' or r['record_id'] not in keys.get(r['entity'],set())): errors.append('Event transition')
            if name=='GapAnalysis' and r['required_hours']!=r['qualified_hours']+r['gap_hours']: errors.append('Gap reconciliation')
            if name=='GapAnalysis' and r['candidate_id'] and r['candidate_id'] not in keys['Employee']: errors.append('Invalid candidate')
            if name=='Training' and not 1<=r['target_proficiency']<=5: errors.append('Training proficiency')
            if name=='Employee' and r['weekly_hours'] not in [20,32,40]: errors.append('Weekly capacity')
            if name=='Event':
                parent=records.get(r['entity'],{}).get(r['record_id'])
                if parent and r['to_state']!=parent['status']: errors.append('Event state mismatch')
        unique_fields={'EmployeeSkill':['employee_id','skill_id'],'Availability':['employee_id','period'],'GapAnalysis':['demand_id']}.get(name)
        if unique_fields and len({tuple(r[f] for f in unique_fields) for r in rows})!=len(rows): errors.append(f'{name}: duplicate natural key')
    return errors

def export(out,t,truth,utilization,findings,config):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    exports={**t,'ground_truth':truth,'utilization':utilization,'findings':findings}
    db=sqlite3.connect(':memory:')
    for name,rows in exports.items():
        (out/f'{name}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
        if rows:
            fields=list(rows[0])
            with (out/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
                w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
            defs=','.join(f'"{k}" '+('INTEGER' if isinstance(rows[0][k],int) else 'REAL' if isinstance(rows[0][k],float) else 'TEXT') for k in fields)
            db.execute(f'CREATE TABLE "{name}" ({defs})')
            db.executemany(f'INSERT INTO "{name}" VALUES ({",".join("?" for _ in fields)})',[tuple(r.values()) for r in rows])
    (out/'seed.sql').write_text('\n'.join(db.iterdump()),encoding='utf-8'); db.close()
    expected={tuple(r.values()) for r in truth}; detected={tuple(r.values()) for r in findings}
    errors=validate(t)
    summary=dict(errors=errors,passed=not errors,known_anomaly_recall=len(expected & detected)/len(expected),known_anomalies=len(expected),detected_exceptions=len(detected),total_demand_hours=sum(r['required_hours'] for r in t['GapAnalysis']),total_gap_hours=sum(r['gap_hours'] for r in t['GapAnalysis']),row_counts={k:len(v) for k,v in exports.items()})
    (out/'validation_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.iterdir()) if p.is_file() and p.name!='manifest.json'}
    (out/'manifest.json').write_text(json.dumps(dict(config=config,provenance='Entirely synthetic; no external or personal data',sha256=hashes),indent=2),encoding='utf-8')
    return summary

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--full',action='store_true'); p.add_argument('--output',default='output'); p.add_argument('--seed',type=int,default=SEED)
    p.add_argument('--employees',type=int); p.add_argument('--skills',type=int); p.add_argument('--projects',type=int); p.add_argument('--months',type=int,default=12)
    a=p.parse_args(); config=dict(employees=a.employees or (5000 if a.full else 100),skills=a.skills or (300 if a.full else 30),projects=a.projects or (500 if a.full else 10),months=a.months,seed=a.seed)
    t,truth=generate(**config); gaps,util,findings=analyze(t); t['GapAnalysis']=gaps
    summary=export(a.output,t,truth,util,findings,config)
    print(json.dumps(summary,indent=2))
    if summary['errors']: raise SystemExit(1)

if __name__=='__main__': main()
