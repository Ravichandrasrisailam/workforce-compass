const $ = s => document.querySelector(s);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = n => Number(n || 0).toLocaleString('en-IN');
const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const monthName = p => `${months[Number(p.slice(-2))-1]} 2026`;
const state = {page:'overview',data:null,request:0,demandSearch:'',action:'',demandPage:0,peopleSearch:'',risk:'',issue:''};
const titles = {
  overview:['Overview','The right people. A clearer plan.','Connect project demand to the skills and capacity you actually have.'],
  demand:['Demand & skill gaps','See the work. Find the gaps.','Trace every shortage back to a project, role, skill and planning month.'],
  people:['People & capacity','Understand your team’s capacity.','A person can be available without having the skills a project needs.'],
  exceptions:['Exceptions','Bring the exceptions into focus.','Find the records that need a manager or HR partner to take a closer look.'],
  guide:['Understand the project','From a business problem to a decision.','A guided explanation of what this project does, why it matters and how to demonstrate it.']
};
const issueNames = {allocation_exceeds_availability:'Allocation exceeds capacity',overlapping_projects:'Overlapping project assignments',stale_skill_treated_current:'Expired skill claimed as current',demand_double_counted:'Duplicate demand'};
const issueHelp = {allocation_exceeds_availability:'Assigned hours are greater than leave-adjusted capacity. Rebalance work or agree a feasible schedule.',overlapping_projects:'Assignments to different projects share dates. Review the schedule; date overlap is a warning and does not always mean overload.',stale_skill_treated_current:'A source profile claims to be current, but its verification is older than 365 days. Reverify before relying on it.',demand_double_counted:'Two demand records share a project, month, role and skill. Keep the source history; exclude the later duplicate from totals.'};

function params(extra={}) { return new URLSearchParams({scale:$('#scale').value,period:$('#period').value,project:$('#project').value,role:$('#role').value,...extra}); }
async function api(path, query, options) {
  const response=await fetch(path+(query?'?'+query:''),options);
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || 'The request failed. Please try again.');
  return data;
}
function errorMessage(error){ $('#notice').innerHTML=`<div class="error">${esc(error.message)} <button class="text-button" id="retry">Try again</button></div>`; $('#retry').onclick=load; }
function badge(value) {
  const names={train:'Training candidate',hire:'Hiring review',none:'Covered',overallocated:'Overallocated',underutilized:'Underutilized',balanced:'Balanced'};
  return `<span class="badge ${['hire','underutilized'].includes(value)?'warn':value==='overallocated'?'danger':'green'}">${esc(names[value]||value)}</span>`;
}
function empty(message){return `<div class="empty">${esc(message)}</div>`;}
function kpi(label,value,unit,foot,icon='◫',className='') { return `<article class="kpi"><div class="kpi-top">${label}<span class="kpi-icon">${icon}</span></div><div class="kpi-value ${className}">${value}<small>${unit}</small></div><div class="kpi-foot">${foot}</div></article>`; }
function demandTable(rows) {
  if(!rows.length)return empty('No demand matches these filters. Try another role or project.');
  return `<div class="table-wrap"><table><thead><tr><th>PROJECT / PERIOD</th><th>ROLE & SKILL</th><th>DEMAND</th><th>QUALIFIED</th><th>GAP</th><th>NEXT STEP</th><th></th></tr></thead><tbody>${rows.map(r=>`<tr><td><strong>${esc(r.project_name)}</strong><small>${monthName(r.period)} · ${esc(r.project_id)}</small></td><td>${esc(r.role_name)}<small>${esc(r.skill_name)} · level ${r.min_proficiency}+</small></td><td>${fmt(r.required_hours)} h</td><td>${fmt(r.qualified_hours)} h</td><td class="gap-number">${fmt(r.gap_hours)} h</td><td>${badge(r.recommendation)}</td><td><button class="table-link" data-demand="${esc(r.demand_id)}">Explore ↗</button></td></tr>`).join('')}</tbody></table></div>`;
}
function overview() {
  const d=state.data,m=d.metrics,max=Math.max(1,...d.trend.map(t=>t.required));
  const priority=[...d.demands].sort((a,b)=>b.gap_hours-a.gap_hours).slice(0,4);
  return `<section class="intro-strip"><div class="intro-icon">◎</div><div class="intro-copy"><strong>A planning question, answered with evidence.</strong><p>Can we deliver the planned work with our current people and skills? Start with demand, then explore what is missing.</p></div><a class="text-link" href="#guide">Take the project walkthrough ↗</a></section>
  <section class="kpi-grid" aria-label="Planning summary">
    ${kpi('Planned demand',fmt(m.required),'hours',`${monthName($('#period').value)} · ${fmt(d.demands.length)} demand plans`,'▥')}
    ${kpi('Qualified coverage',fmt(m.qualified),'hours',`<span class="badge green">${m.coverage}% covered</span> of planned demand`,'✓')}
    ${kpi('Uncovered demand',fmt(m.gap),'hours','Requires a staffing or development decision','↗')}
    ${kpi('Team utilization',m.utilization+'%','',`<span class="badge ${m.overallocated?'warn':'green'}">${m.overallocated} overallocated</span> employee-months`,'♧')}
  </section>
  <div class="grid-main"><section class="panel"><div class="panel-head"><div><h2>Demand across the planning year</h2><p>Qualified hours and uncovered demand · 2026</p></div><div class="legend"><span><i class="swatch"></i>Qualified</span><span><i class="swatch light"></i>Gap</span></div></div><div class="panel-body"><div class="chart-wrap"><div class="bar-chart" role="group" aria-label="Monthly qualified coverage and gap. Each bar can select a month.">${d.trend.map(t=>`<button class="bar-group ${t.period===$('#period').value?'selected':''}" data-month="${t.period}" aria-label="${monthName(t.period)}: ${fmt(t.required)} demand hours, ${fmt(t.qualified)} qualified hours, ${fmt(t.gap)} gap hours" title="${monthName(t.period)} · ${fmt(t.required)} h demand · ${fmt(t.gap)} h gap" style="border:0;padding:0"><span class="bar" style="height:${t.qualified/max*100}%"></span><span class="bar gap" style="height:${t.gap/max*100}%"></span></button>`).join('')}</div><div class="chart-labels">${months.map(m=>`<span>${m}</span>`).join('')}</div></div><div class="chart-caption"><span>Click a month to explore its plan</span><span>Peak demand: ${fmt(max)} h</span></div></div><div class="panel-note">Demand is an approved planning scenario, not a machine learning prediction. Role and project filters apply to every month.</div></section>
  <section class="panel"><div class="panel-head"><div><h2>Where skills fall short</h2><p>Qualified coverage by role · ${monthName($('#period').value)}</p></div><span class="data-chip">${fmt(m.gap)} h gap</span></div><div class="panel-body">${d.role_breakdown.map(r=>`<div class="role-row"><div class="role-line"><span>${esc(r.name)}</span><strong>${fmt(r.gap)} h gap</strong></div><div class="progress" role="meter" aria-label="${esc(r.name)} coverage" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${r.required?Math.round(r.qualified/r.required*100):0}"><span style="width:${r.required?r.qualified/r.required*100:0}%"></span></div><div class="role-hint">${fmt(r.qualified)} of ${fmt(r.required)} demand hours covered</div></div>`).join('')}</div><div class="panel-note">A skill counts only when the role matches, proficiency is sufficient and verification is current.</div></section></div>
  <div class="section-line"><div><h2>Turn insight into action</h2><p>Suggestions for review, with assumptions attached.</p></div><a href="#demand">Review all demand →</a></div>
  <section class="action-grid"><a class="action-card" href="#demand" data-action-link="hire"><span class="action-icon">↗</span><div><h3><strong>${d.actions.hire||0}</strong>Hiring reviews</h3><p>No eligible near-ready training candidate found</p></div></a><a class="action-card" href="#demand" data-action-link="train"><span class="action-icon">⌁</span><div><h3><strong>${d.actions.train||0}</strong>Training opportunities</h3><p>One proficiency level away, with time to learn</p></div></a><a class="action-card" href="#people" data-risk-link="overallocated"><span class="action-icon">⚑</span><div><h3><strong>${m.overallocated}</strong>Capacity reviews</h3><p>Assigned work exceeds available hours</p></div></a></section>
  <section class="panel"><div class="panel-head" style="padding-bottom:18px"><div><h2>Demand that needs your attention</h2><p>Largest uncovered requirements in the current selection</p></div><span class="data-chip">${monthName($('#period').value)}</span></div>${demandTable(priority)}</section><p class="scope-note" style="margin-top:14px">Capacity scope: ${esc(d.capacity_scope)} Qualified coverage is provisional when assignments overlap; managers must review feasibility.</p>`;
}
function demandView() {
  return `<section class="intro-strip"><div class="intro-copy"><strong>Allocated does not always mean qualified.</strong><p>Open a row to see exactly why assigned hours do or do not cover demand, then try an isolated what-if scenario.</p></div></section><section class="panel"><div class="table-toolbar"><input id="demand-search" class="search" aria-label="Search project, role or skill" placeholder="Search project, role or skill…" value="${esc(state.demandSearch)}"><select id="action-filter" aria-label="Filter recommendations"><option value="">All recommendations</option><option value="hire">Hiring review</option><option value="train">Training candidate</option><option value="none">Covered</option></select></div><div id="demand-table"></div><div class="table-info"><span id="demand-info"></span><div><button class="text-button" id="prev-demand">← Previous</button><button class="text-button" id="next-demand">Next →</button></div></div></section>`;
}
function updateDemandTable(){
  const q=state.demandSearch.toLowerCase();
  const rows=state.data.demands.filter(r=>(!state.action||r.recommendation===state.action)&&`${r.project_name} ${r.project_id} ${r.role_name} ${r.skill_name}`.toLowerCase().includes(q));
  const pages=Math.max(1,Math.ceil(rows.length/20)); state.demandPage=Math.min(state.demandPage,pages-1);
  $('#demand-table').innerHTML=demandTable(rows.slice(state.demandPage*20,(state.demandPage+1)*20));
  $('#demand-info').textContent=`${fmt(rows.length)} demand plans · page ${state.demandPage+1} of ${pages}`;
  $('#prev-demand').disabled=state.demandPage===0; $('#next-demand').disabled=state.demandPage>=pages-1;
}
function peopleView(){
  const m=state.data.metrics;
  return `<section class="kpi-grid">${kpi('People in scope',fmt(m.people),'people','Selected project and role','♧')}${kpi('Available capacity',fmt(m.available),'hours','After part-time schedules and leave','◷')}${kpi('Assigned work',fmt(m.allocated),'hours','Includes every assignment for these people','▥')}${kpi('Overallocated',fmt(m.overallocated),'people','More work assigned than time available','⚑')}</section><p class="scope-note">${esc(state.data.capacity_scope)} Capacity is four planning weeks × contracted weekly hours − leave. Below 60% utilization is underutilized; above 100% is overallocated.</p><section class="panel"><div class="table-toolbar"><input class="search" id="people-search" aria-label="Search employee name or ID" placeholder="Search employee name or ID…" value="${esc(state.peopleSearch)}"><select id="risk-filter" aria-label="Filter capacity risk"><option value="">All capacity states</option><option value="overallocated">Overallocated</option><option value="balanced">Balanced</option><option value="underutilized">Underutilized</option></select></div><div id="people-table"><div class="loading"><span class="spinner"></span> Loading people…</div></div></section>`;
}
let peopleRequest=0;
async function loadPeople(){
  const request=++peopleRequest;
  try{
    const d=await api('/api/people',params({q:state.peopleSearch,risk:state.risk}));
    if(request!==peopleRequest||state.page!=='people')return;
    $('#people-table').innerHTML=d.rows.length?`<div class="table-wrap"><table><thead><tr><th>EMPLOYEE</th><th>ROLE</th><th>WEEKLY HOURS</th><th>LEAVE</th><th>AVAILABLE</th><th>ASSIGNED</th><th>UTILIZATION</th><th>STATE</th><th></th></tr></thead><tbody>${d.rows.map(r=>`<tr><td><strong>${esc(r.name)}</strong><small>${esc(r.employee_id)}</small></td><td>${esc(r.role_name)}</td><td>${r.weekly_hours} h</td><td>${r.leave_hours} h</td><td>${r.available_hours} h</td><td>${r.allocated_hours} h</td><td>${r.utilization_pct}%<div class="capacity-bar ${r.risk==='overallocated'?'over':''}"><span style="width:${Math.min(r.utilization_pct,100)}%"></span></div></td><td>${badge(r.risk)}</td><td><button class="table-link" data-employee="${r.employee_id}">Profile ↗</button></td></tr>`).join('')}</tbody></table></div><div class="table-info">Showing ${d.rows.length} of ${fmt(d.total)} matching employees. Search by ID to find anyone in the full dataset.</div>`:empty('No employees match these filters. Try another search or capacity state.');
  }catch(e){errorMessage(e);}
}
function exceptionView(){
  return `<p class="scope-note">Exceptions cover the entire selected dataset. The planning month, role and project filters do not apply here. Injected labels are displayed only for evaluation; the detection engine never reads them.</p><div id="issue-summary"></div><section class="panel"><div class="table-toolbar"><h2>Records requiring review</h2><select id="issue-filter" aria-label="Filter exception type"><option value="">All exception types</option>${Object.entries(issueNames).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></div><div id="exception-table"><div class="loading"><span class="spinner"></span> Checking exceptions…</div></div></section>`;
}
async function loadExceptions(){
  try{
    const scale=$('#scale').value,issue=state.issue;
    const d=await api('/api/exceptions',new URLSearchParams({scale,issue}));
    if(state.page!=='exceptions'||scale!==$('#scale').value||issue!==state.issue)return;
    $('#exception-count').textContent=fmt(Object.values(d.counts).reduce((a,b)=>a+b,0));
    $('#issue-summary').innerHTML=`<div class="issue-intro">${Object.entries(issueNames).map(([k,v])=>`<div class="issue-card"><strong>${fmt(d.counts[k]||0)}</strong><p>${v}</p><small>Rule-derived findings</small></div>`).join('')}</div>`;
    $('#exception-table').innerHTML=d.rows.length?`<div class="table-wrap"><table><thead><tr><th>EXCEPTION</th><th>SOURCE RECORD</th><th>REVIEW GUIDANCE</th><th>EVALUATION</th></tr></thead><tbody>${d.rows.map(r=>`<tr><td><span class="badge warn">${esc(issueNames[r.issue_type])}</span></td><td>${esc(r.entity)}<small>${esc(r.record_id)}</small></td><td style="white-space:normal;min-width:230px;max-width:380px;font-size:10px;line-height:1.7">${esc(issueHelp[r.issue_type])}</td><td><span class="badge ${r.injected?'green':'neutral'}">${r.injected?'Known injected case':'Naturally occurring'}</span></td></tr>`).join('')}</tbody></table></div><div class="table-info">Showing ${d.rows.length} of ${fmt(d.total)} findings. Download all findings for a complete audit.</div>`:empty('No exceptions match this category.');
  }catch(e){errorMessage(e);}
}
function guideView(){
  const checks=state.data.checks,c=state.data.config;
  return `<section class="guide-hero"><div class="eyebrow">THE BUSINESS PROBLEM</div><h2>A company has upcoming projects. Does it have the right people, skills and time to deliver them?</h2><p>A headcount alone cannot answer that. Some people work part-time, some are on leave, some have expired skills, and some are already assigned to several projects. This project turns those facts into evidence for staffing, training and hiring decisions.</p></section>
  <div class="guide-grid"><article class="guide-card"><div class="step-number">01</div><h3>Understand the work</h3><p>A manager defines how many hours a project needs, in which month, for a particular role and skill level.</p><div class="formula">Project → Month → Role<br>Skill + Proficiency + Hours</div><a class="table-link" href="#demand">Explore demand plans →</a></article><article class="guide-card"><div class="step-number">02</div><h3>Check the people</h3><p>Match assignments to current skills and calculate capacity after working patterns and leave.</p><div class="formula">Capacity = Weekly hours × 4 − Leave<br>Utilization = Assigned ÷ Capacity</div><a class="table-link" href="#people">Explore employee capacity →</a></article><article class="guide-card"><div class="step-number">03</div><h3>Make a defensible decision</h3><p>Identify uncovered demand, flag scheduling risks, then propose training or a hiring review.</p><div class="formula">Gap = Demand − Qualified coverage<br>Every gap links to a demand record</div><a class="table-link" href="#exceptions">Explore exceptions →</a></article></div>
  <div class="walkthrough"><section class="panel"><div class="panel-head"><h2>A concrete example</h2></div><div class="panel-body"><p>A project needs <strong>160 hours</strong> of an Engineer with level 3 proficiency. An employee works 32 hours a week and has 16 hours of leave.</p><div class="formula">Available = 32 × 4 − 16 = 112 hours<br>Assigned = 120 hours<br>Utilization = 120 ÷ 112 = 107.1%</div><p>If the employee has the right role and a current level 3 skill, the provisional gap is <strong>160 − 120 = 40 hours</strong>. The 107.1% utilization still triggers a capacity review. If that skill is expired, all 120 assigned hours fail qualification and the gap is <strong>160 hours</strong>.</p><div class="explanation">The key insight: assigning a person is not the same as proving that the work is covered. Skills, verification and time must all be reviewed.</div></div></section><section class="panel"><div class="panel-head"><h2>Try a five-minute demonstration</h2></div><div class="panel-body"><ol class="guide-list"><li>Start on <strong>Overview</strong>. Read demand, coverage and gap.</li><li>Choose a different month. See how expiry changes coverage.</li><li>Open <strong>Demand & skill gaps → Explore</strong>.</li><li>Inspect each employee’s qualification reasons.</li><li>Use <strong>What if?</strong> to change demand hours or simulate skill reverification. The baseline stays intact.</li><li>Open <strong>People & capacity</strong> and find an overallocated employee.</li><li>Review <strong>Exceptions</strong> and export the evidence.</li><li>Switch to <strong>Full scale</strong> to demonstrate the required volume.</li></ol><a class="button primary" href="#overview">Start the walkthrough →</a></div></section></div>
  <div class="walkthrough"><section class="panel"><div class="panel-head"><h2>What a recommendation means</h2></div><div class="panel-body"><p><strong>Training candidate:</strong> an employee has the correct role, current verification, exactly one proficiency level below the requirement, and at least min(gap,40) unassigned hours.</p><p><strong>Hiring review:</strong> a gap remains and no near-ready training candidate meets those rules. HR must check budget and alternatives before hiring.</p><p><strong>Covered:</strong> qualified assigned hours meet demand. Scheduling exceptions still need review.</p><div class="explanation">These are explainable candidate actions. They are not automatic hiring decisions, training completion promises, or a resource scheduling optimizer.</div></div></section><section class="panel"><div class="panel-head"><h2>Requirements & evidence</h2><span class="badge green">${checks.passed?'Integrity passed':'Review required'}</span></div><div class="panel-body"><div class="check-row"><span>Employees / skills / projects</span><strong>${fmt(c.employees)} / ${fmt(c.skills)} / ${fmt(c.projects)}</strong></div><div class="check-row"><span>Planning horizon</span><strong>12 monthly buckets</strong></div><div class="check-row"><span>Known injected cases detected</span><strong>${checks.known_anomaly_recall*100}% · 4 types</strong></div><div class="check-row"><span>Integrity errors</span><strong>${checks.errors.length}</strong></div><div class="check-row"><span>Fixed seed</span><strong>${c.seed}</strong></div><p>CSV, JSON and SQL exports, a schema, a data dictionary, tests and a two-run SHA-256 reproducibility report are included in the repository.</p><div class="chips">${Object.entries(checks.row_counts).map(([k,v])=>`<span class="data-chip">${esc(k)} · ${fmt(v)}</span>`).join('')}</div></div></section></div>
  <section class="panel"><div class="panel-head"><h2>Scope, actors and honest limits</h2></div><div class="panel-body"><p class="scope-note"><strong>Managers</strong> review demand, assignments and risks. <strong>HR partners</strong> evaluate development and hiring options. <strong>Employees</strong> supply skill evidence; <strong>IT/operations and administrators</strong> manage master data, exports and validation. This demo has a shared local workspace, without separate logins or role permissions.</p><p class="scope-note">Demand is a synthetic approved plan, not a statistical prediction. Capacity uses 12 four-week buckets (48 planning weeks). Verification expires after 365 days. Qualified coverage is provisional when scheduling conflicts exist. Creation events retain initial state; operational lifecycle updates are outside this version. What-if scenarios run in memory and do not change source records. No external or personal data is used.</p><div class="chips"><a class="button secondary" href="${downloadURL('DemandPlan')}">↓ Demand CSV</a><a class="button secondary" href="${downloadURL('Employee')}">↓ Employee CSV</a><a class="button secondary" href="${downloadURL('findings')}">↓ Findings CSV</a><a class="button secondary" href="${downloadURL('ground_truth')}">↓ Ground truth CSV</a></div></div></section>`;
}
function downloadURL(table){return '/api/download?'+new URLSearchParams({scale:$('#scale').value,table});}
function render(){
  const [label,title,subtitle]=titles[state.page];
  $('#breadcrumb').textContent=label; $('#page-title').textContent=title; $('#page-subtitle').textContent=subtitle;
  document.querySelectorAll('[data-page]').forEach(a=>{a.classList.toggle('active',a.dataset.page===state.page); if(a.dataset.page===state.page)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');});
  const exports={overview:'GapAnalysis',demand:'GapAnalysis',people:'utilization',exceptions:'findings',guide:'DemandPlan'};
  $('#export-link').href=downloadURL(exports[state.page]);
  $('#export-link').textContent='↓ Export '+{overview:'gap analysis',demand:'gap analysis',people:'utilization',exceptions:'findings',guide:'demand plans'}[state.page];
  $('#export-link').title='Exports the entire selected dataset, independent of planning filters';
  $('#content').innerHTML=({overview,demand:demandView,people:peopleView,exceptions:exceptionView,guide:guideView}[state.page])();
  if(state.page==='demand'){
    $('#action-filter').value=state.action; updateDemandTable();
    $('#demand-search').oninput=e=>{state.demandSearch=e.target.value;state.demandPage=0;updateDemandTable();};
    $('#action-filter').onchange=e=>{state.action=e.target.value;state.demandPage=0;updateDemandTable();};
    $('#prev-demand').onclick=()=>{state.demandPage--;updateDemandTable();};
    $('#next-demand').onclick=()=>{state.demandPage++;updateDemandTable();};
  }
  if(state.page==='people'){
    $('#risk-filter').value=state.risk;loadPeople();
    let timer;
    $('#people-search').oninput=e=>{state.peopleSearch=e.target.value;clearTimeout(timer);timer=setTimeout(loadPeople,200);};
    $('#risk-filter').onchange=e=>{state.risk=e.target.value;loadPeople();};
  }
  if(state.page==='exceptions'){$('#issue-filter').value=state.issue;loadExceptions();$('#issue-filter').onchange=e=>{state.issue=e.target.value;loadExceptions();};}
}
async function load(){
  const request=++state.request;
  $('#notice').textContent='';
  $('#content').innerHTML='<div class="loading"><span class="spinner"></span> Calculating demand, coverage and capacity…</div>';
  try{
    const d=await api('/api/dashboard',params());
    if(request!==state.request)return;
    state.data=d;
    const project=$('#project').value,role=$('#role').value;
    $('#project').innerHTML='<option value="">All projects</option>'+d.projects.map(p=>`<option value="${p.project_id}">${esc(p.name)}</option>`).join('');
    $('#role').innerHTML='<option value="">All roles</option>'+d.roles.map(r=>`<option value="${r.role_id}">${esc(r.name)}</option>`).join('');
    $('#project').value=project;$('#role').value=role;
    state.demandPage=0;render();
  }catch(e){if(request===state.request){$('#content').innerHTML=empty('Could not load the planning workspace. Check that python app.py is running.');errorMessage(e);}}
}
function openDialog(html){const dialog=$('#detail-dialog');$('#detail-body').innerHTML=html;if(!dialog.open)dialog.showModal();}
function detailHead(title,subtitle){return `<div class="dialog-head"><div><div class="eyebrow">SOURCE-TO-DECISION TRACE</div><h2 id="detail-title">${title}</h2><p>${subtitle}</p></div><button class="close-button" data-close aria-label="Close details">×</button></div>`;}
async function openDemand(id){
  openDialog(detailHead('Demand trace','Loading the source records…')+'<div class="loading"><span class="spinner"></span> Loading evidence…</div>');
  try{
    const d=await api('/api/demand',params({id})),r=d.demand;
    openDialog(detailHead(esc(r.project_name)+' · '+monthName(r.period),`${esc(r.role_name)} · ${esc(r.skill_name)} · proficiency ${r.min_proficiency}+<br>${esc(r.demand_id)}`)+`<div class="dialog-content"><div class="detail-metrics"><div class="detail-metric"><small>Demand</small><strong>${fmt(r.required_hours)} h</strong></div><div class="detail-metric"><small>Qualified coverage</small><strong>${fmt(r.qualified_hours)} h</strong></div><div class="detail-metric warn"><small>Uncovered gap</small><strong>${fmt(r.gap_hours)} h</strong></div></div><h3>Why do these assignments count—or fail?</h3><p class="scope-note" style="margin-top:8px">${fmt(r.allocated_hours)} hours are assigned. Only role-matched, proficient, current skills count toward coverage. Coverage is capped at demand.</p><section class="panel"><div class="table-wrap"><table><thead><tr><th>EMPLOYEE</th><th>HOURS</th><th>SKILL EVIDENCE</th><th>QUALIFICATION</th><th>CAPACITY</th></tr></thead><tbody>${d.allocations.map(a=>`<tr><td>${esc(a.employee_name)}<small>${esc(a.employee_id)} · ${esc(a.role_name)}</small></td><td>${a.hours} h</td><td>${a.profile?`Level ${a.profile.proficiency}<small>Verified ${a.profile.last_verified}</small>`:'No required skill profile'}</td><td><span class="badge ${a.qualified?'green':'warn'}">${a.qualified?'Counts toward coverage':'Does not count'}</span>${a.reasons.map(x=>`<span class="reason">${esc(x)}</span>`).join('')}</td><td>${a.utilization.utilization_pct}%<small>${a.utilization.allocated_hours} / ${a.utilization.available_hours} h</small></td></tr>`).join('')}</tbody></table></div></section><h3>Recommended next step ${badge(r.recommendation)}</h3><p class="scope-note" style="margin-top:10px">${d.candidate?`Near-ready candidate: <strong>${esc(d.candidate.name)} (${esc(d.candidate.employee_id)})</strong>. `:''}${esc(r.assumption)}</p><div class="explanation"><strong>Traceable calculation:</strong> ${fmt(r.required_hours)} demand hours − ${fmt(r.qualified_hours)} qualified hours = ${fmt(r.gap_hours)} gap hours. Concurrent assignments can make this coverage infeasible; check employee capacity and exceptions before committing.</div><section class="scenario"><h3>What if the plan changes?</h3><p>Try a different requirement or simulate reverifying assigned skill profiles. This is a temporary calculation; the original plan stays intact.</p><form id="scenario-form" class="scenario-form"><label>Required hours<input type="number" id="scenario-hours" min="0" max="10000" step="1" value="${r.required_hours}" required></label><label class="checkbox"><input id="scenario-refresh" type="checkbox"> Simulate skill reverification</label><button class="button primary" type="submit">Run what-if →</button></form><div id="scenario-result" aria-live="polite"></div></section><h3 style="margin-top:25px">Creation event history</h3><div class="event-list">${d.events.map(e=>`<span>${e.effective_date} · ${esc(e.entity)} · ${esc(e.from_state)} → ${esc(e.to_state)}<br>${esc(e.event_id)} · ${esc(e.record_id)}</span>`).join('')}</div></div>`);
    $('#scenario-form').onsubmit=async e=>{
      e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;button.textContent='Calculating…';
      try{
        const result=await api('/api/scenario',null,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scale:$('#scale').value,demand_id:id,required_hours:Number($('#scenario-hours').value),refresh_skills:$('#scenario-refresh').checked})});
        $('#scenario-result').innerHTML=`<div class="scenario-result"><strong>Scenario result</strong><br>Demand: ${fmt(result.before.required_hours)} → ${fmt(result.after.required_hours)} h · Qualified coverage: ${fmt(result.before.qualified_hours)} → ${fmt(result.after.qualified_hours)} h<br>Gap: <strong>${fmt(result.before.gap_hours)} → ${fmt(result.after.gap_hours)} h</strong> · Next step: ${badge(result.after.recommendation)}<br>${result.profiles_reverified} assigned profiles simulated as reverified. No role or proficiency levels changed. Baseline unchanged.</div>`;
      }catch(error){$('#scenario-result').innerHTML=`<div class="error">${esc(error.message)}</div>`;}finally{button.disabled=false;button.textContent='Run what-if →';}
    };
  }catch(e){openDialog(detailHead('Could not load demand','')+`<div class="dialog-content error">${esc(e.message)}</div>`);}
}
async function openEmployee(id){
  openDialog(detailHead('Employee profile','Loading skills and capacity…')+'<div class="loading"><span class="spinner"></span> Loading profile…</div>');
  try{
    const d=await api('/api/employee',params({id})),e=d.employee,a=d.availability;
    openDialog(detailHead(esc(e.name),`${esc(e.employee_id)} · ${esc(d.role_name)} · ${monthName($('#period').value)}`)+`<div class="dialog-content"><div class="detail-metrics"><div class="detail-metric"><small>Working pattern</small><strong>${e.weekly_hours} h / wk</strong></div><div class="detail-metric"><small>Leave-adjusted capacity</small><strong>${a.available_hours} h</strong></div><div class="detail-metric warn"><small>Utilization</small><strong>${d.utilization.utilization_pct}%</strong></div></div><div class="explanation">${e.weekly_hours} hours/week × 4 weeks = ${a.base_hours} base hours − ${a.leave_hours} leave hours = <strong>${a.available_hours} available hours</strong>. ${d.utilization.allocated_hours} assigned hours ÷ ${a.available_hours} = ${d.utilization.utilization_pct}% utilization. ${badge(d.utilization.risk)}</div><section class="panel"><div class="panel-head" style="padding-bottom:15px"><h3>Skill evidence</h3></div><div class="table-wrap"><table><thead><tr><th>SKILL</th><th>PROFICIENCY</th><th>LAST VERIFIED</th><th>STATUS IN THIS MONTH</th></tr></thead><tbody>${d.profiles.map(s=>`<tr><td>${esc(s.skill_name)}<small>${esc(s.skill_id)}</small></td><td>${s.proficiency} / 5</td><td>${s.last_verified}</td><td><span class="badge ${s.current?'green':'warn'}">${s.current?'Current':'Expired'}</span></td></tr>`).join('')}</tbody></table></div></section><section class="panel"><div class="panel-head" style="padding-bottom:15px"><h3>Assignments this month</h3></div>${d.allocations.length?`<div class="table-wrap"><table><thead><tr><th>PROJECT</th><th>HOURS</th><th>INCLUSIVE DAYS</th><th>SOURCE</th></tr></thead><tbody>${d.allocations.map(a=>`<tr><td>${esc(a.project_name)}</td><td>${a.hours} h</td><td>${a.start_day}–${a.end_day}</td><td>${esc(a.allocation_id)}</td></tr>`).join('')}</tbody></table></div>`:empty('No assignments in this month. This employee may be available for reassignment, subject to skill checks.')}</section><h3>Training records</h3><p class="scope-note" style="margin-top:10px">${d.training.length?d.training.map(t=>`${esc(t.training_id)} · ${esc(t.skill_id)} · target level ${t.target_proficiency} · ${esc(t.status)} · ${t.start_date} to ${t.end_date}`).join('<br>'):'No planned training records for this employee.'} Planned training does not automatically increase skill proficiency.</p></div>`);
  }catch(e){openDialog(detailHead('Could not load employee','')+`<div class="dialog-content error">${esc(e.message)}</div>`);}
}

document.addEventListener('click',e=>{
  const demand=e.target.closest('[data-demand]');if(demand)openDemand(demand.dataset.demand);
  const employee=e.target.closest('[data-employee]');if(employee)openEmployee(employee.dataset.employee);
  const month=e.target.closest('[data-month]');if(month){$('#period').value=month.dataset.month;load();}
  if(e.target.closest('[data-close]'))$('#detail-dialog').close();
  const action=e.target.closest('[data-action-link]');if(action){state.action=action.dataset.actionLink;state.demandPage=0;}
  const risk=e.target.closest('[data-risk-link]');if(risk)state.risk=risk.dataset.riskLink;
});
$('#detail-dialog').addEventListener('click',e=>{if(e.target===$('#detail-dialog')&&e.offsetX>=0&&e.offsetY>=0&&e.offsetX<e.target.clientWidth&&e.offsetY<e.target.clientHeight)return;if(e.target===$('#detail-dialog'))e.target.close();});
function route(){state.page=location.hash.slice(1) in titles?location.hash.slice(1):'overview';if(state.data)render();window.scrollTo(0,0);}
window.addEventListener('hashchange',route);
$('#period').innerHTML=months.map((m,i)=>`<option value="2026-${String(i+1).padStart(2,'0')}">${m} 2026</option>`).join('');
for(const name of ['period','project','role','scale'])$('#'+name).addEventListener('change',()=>{if(name==='scale'){$('#project').value='';$('#role').value='';}load();});
$('#reset').onclick=()=>{$('#period').value='2026-01';$('#project').value='';$('#role').value='';state.demandSearch='';state.action='';state.peopleSearch='';state.risk='';load();};
route();load();
