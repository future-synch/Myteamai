
const PAGES=['cc','af','kb','sm','ah'];
function showPage(id){
  PAGES.forEach(p=>{document.getElementById('page-'+p).classList.remove('active');document.getElementById('tn-'+p).classList.remove('active')});
  document.getElementById('page-'+id).classList.add('active');
  document.getElementById('tn-'+id).classList.add('active');
}

// KB data
const KB_DATA={
  'kb-match-w11':{icon:'🏠',iconBg:'#E1F5EE',title:'W11 applicant matching criteria playbook',type:'Playbook',typeCls:'kt-playbook',prov:'Captured from chat session · Claude Sonnet · Saved by Curtis · 4 min ago',
    steps:[{n:'1',text:'Hard filter first — Python only',note:'Budget must be ≥ property price × 0.95. Bedrooms must be within stated min/max range. Applied before any AI call.'},
           {n:'2',text:'Must-have features are non-negotiable',note:'If applicant listed garden, parking, or quiet as must-have, properties without these are excluded regardless of score.'},
           {n:'3',text:'Financing strength weights the score',note:'Cash buyer always scores higher than AIP. AIP held scores higher than mortgage required. AIP pending = flagged.'},
           {n:'4',text:'KYC status is separate from match score',note:'KYC-incomplete applicants are returned in results but flagged as can_progress: false. They cannot proceed to offer.'},
           {n:'5',text:'Top 3–5 results with rationale',note:'Each result includes a plain-English match reason. Rationale stored here for reference across sessions.'}],
    note:'Derived from the Match Applicants session on 14 Ladbroke Road W11 (Apr 22). The 2-stage logic — Python hard filter then Claude scoring — was confirmed as the preferred approach after the earlier valuation session showed that AI-only filtering produced too many near-misses on budget. This playbook is loaded automatically whenever Match Applicants runs.',
    provItems:[{color:'#D4537E',label:'Chat session — 14 Ladbroke Road matching',meta:'Today 09:41 · Claude Sonnet'},{color:'#7F77DD',label:'Saved to KB by Curtis',meta:'Today 09:45'},{color:'#1D9E75',label:'Available to all models in workspace',meta:'Automatic · no action needed'}]},

  'kb-val-method':{icon:'📊',iconBg:'#FAEEDA',title:'Valuation Methodology — W11 Spring 2026',type:'Playbook',typeCls:'kt-playbook',prov:'Flow output · Valuation Brief · 22 Abbotsbury Road · 2 days ago · Claude Opus',
    steps:[{n:'1',text:'Recency weighting is critical in spring 2026',note:'Land Registry data from Q4 2025 and Q1 2026 should be weighted more heavily. Summer 2025 sales are underpriced relative to current market.'},
           {n:'2',text:'Abbotsbury / Ladbroke Road comparable bracket',note:'Properties on these streets trade in a consistent price-per-sqft range. Use as anchor comparables for nearby instructions.'},
           {n:'3',text:'Garden aspect adds 8–12% in W11',note:'South-facing gardens on W11 properties consistently command a premium vs. north-facing equivalents. Flag in valuation briefing.'},
           {n:'4',text:'Off-market discount is typically 3–5%',note:'Properties introduced off-market and sold without portal listing transact at a modest discount vs. portal-listed equivalents. Honest to note this to clients.'}],
    note:'Generated from the Valuation Brief run for 22 Abbotsbury Road on Apr 20. Claude Opus analysis surfaced four W11-specific pricing patterns that are not in the standard comparable methodology. Saved here so future valuation sessions load these as context — avoiding repeated discovery.',
    provItems:[{color:'#BA7517',label:'Valuation Brief — 22 Abbotsbury Rd',meta:'Apr 20 · Claude Opus'},{color:'#7F77DD',label:'Auto-saved to KB on flow completion',meta:'Apr 20 14:22'},{color:'#1D9E75',label:'Available to all models in workspace',meta:'Automatic'}]},

  'kb-kyc-flow':{icon:'⚖️',iconBg:'#FCEBEB',title:'KYC Escalation Workflow — Overdue Contacts',type:'Workflow',typeCls:'kt-workflow',prov:'Flow output · KYC / AML Status · Mrs Patterson · yesterday · Claude Haiku',
    steps:[{n:'1',text:'Day 1–3 overdue: send document reminder email',note:'Standard reminder via HubSpot sequence. Log the send in activity. Set follow-up task for day 4.'},
           {n:'2',text:'Day 4–6 overdue: personal call from agent',note:'Agent calls directly. Log outcome. If voicemail: leave message referencing specific missing document. Update Lead Status.'},
           {n:'3',text:'Day 7+ overdue: escalate to manager',note:'Flag in HubSpot. Pipeline stage does not advance. Manager reviews whether to extend deadline or mark as stalled.'},
           {n:'4',text:'No property introductions or offer stage without KYC clear',note:'This is a hard gate in the KYC / AML Status flow. can_progress: false until all three items are received and logged.'}],
    note:'Triggered by Mrs Patterson KYC case (6 days overdue as of Apr 22). The escalation path was determined in a chat session and saved here. This workflow is now loaded as context whenever KYC / AML Status returns a blocked result — so any team member or model can follow the same escalation path.',
    provItems:[{color:'#E24B4A',label:'KYC / AML Status blocked — Mrs Patterson',meta:'Yesterday · Claude Haiku'},{color:'#D4537E',label:'Escalation steps captured in chat',meta:'Yesterday 16:30 · Claude Sonnet'},{color:'#7F77DD',label:'Saved to KB by Marta',meta:'Yesterday 16:45'},{color:'#1D9E75',label:'Available to all models',meta:'Automatic'}]},

  'kb-social-voice':{icon:'🎨',iconBg:'#FBEAF0',title:'Social caption rules — Curtis Sloane voice',type:'Playbook',typeCls:'kt-playbook',prov:'Chat capture · Olesya · Mon 14 Apr · Claude Sonnet',
    steps:[{n:'1',text:'Never use: luxury, prestigious, stunning, opportunity',note:'These are estate agent clichés that have lost all meaning. Flag any AI output containing these words for regeneration.'},
           {n:'2',text:'Instagram: 100–150 words, no exclamation marks',note:'Storytelling first, property last. Caption should feel like a letter to the neighbourhood, not an advertisement.'},
           {n:'3',text:'LinkedIn: 100–200 words, one clear idea',note:'Personal observation → insight → neighbourhood connection. Start with a real observation, not a statistic.'},
           {n:'4',text:'Hashtags: 3–5 maximum',note:'Always include #HollandPark #W11 #CurtisSloane. One seasonal or topical tag. No generic property hashtags.'},
           {n:'5',text:'Rotate through: Abundance · Belonging · Discovery · Local Authority',note:'Each post belongs to one pillar. Balance across the month. Never two consecutive posts in the same pillar.'}],
    note:'Distilled from the brand voice document and the first Social Content Draft session. These 15 rules are injected into the system context of every Social Content Draft run. Approved captions are also stored here as style references — so voice consistency improves over time.',
    provItems:[{color:'#D4537E',label:'Brand voice doc ingested from Notion',meta:'Apr 14 · system'},{color:'#D4537E',label:'Rules distilled in chat session',meta:'Apr 14 · Claude Sonnet'},{color:'#7F77DD',label:'Saved to KB by Curtis',meta:'Apr 14 17:02'},{color:'#1D9E75',label:'Injected into Social Content Draft system context',meta:'Automatic on every call'}]}
};

function selectKB(id){
  document.querySelectorAll('.kb-item').forEach(i=>i.classList.remove('sel'));
  document.querySelectorAll('.kb-si').forEach(i=>i.classList.remove('active'));
  const item=document.getElementById('kbi-'+id);
  if(item)item.classList.add('sel');
  const d=KB_DATA[id];
  if(!d)return;
  document.getElementById('kd-icon').textContent=d.icon;
  document.getElementById('kd-icon').style.background=d.iconBg;
  document.getElementById('kd-title').textContent=d.title;
  document.getElementById('kd-type').textContent=d.type;
  document.getElementById('kd-type').className='kb-type '+d.typeCls;
  document.getElementById('kd-provenance').textContent=d.prov;
  document.getElementById('kd-steps').innerHTML=d.steps.map(s=>`<div class="kb-step"><div class="kb-step-n">${s.n}</div><div><div class="kb-step-text">${s.text}</div><div class="kb-step-note">${s.note}</div></div></div>`).join('');
  document.getElementById('kd-note').textContent=d.note;
  document.getElementById('kd-prov').innerHTML=d.provItems.map(p=>`<div class="prov-item"><div class="prov-dot" style="background:${p.color}"></div><span class="prov-label">${p.label}</span><span class="prov-meta">${p.meta}</span></div>`).join('');
}

// Action flows
const FD={
  welcome:{ib:'#E1F5EE',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 3a1 1 0 011-1h10a1 1 0 011 1v8a1 1 0 01-1 1H3a1 1 0 01-1-1V3z" stroke="#085041" stroke-width="1.3"/><path d="M2 4l6 4 6-4" stroke="#085041" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'fn_generate_welcome()',s:'POST /api/bot/welcome · Claude Sonnet · output → KB on completion',b:'Active',bc:'bg',
    st:[{c:'sng',n:'1',nm:'Intent classified',d:'WELCOME_CLIENT detected. Required fields validated.'},{c:'sng',n:'2',nm:'HubSpot create',d:'Contact created. Lifecycle Stage → Welcome Sent. Source tagged.'},{c:'snp',n:'3',nm:'Claude drafts message',d:'Sonnet produces welcome. Max 1,000 tokens. Brand voice context loaded from KB.'},{c:'sng',n:'4',nm:'Dispatch or return + KB save',d:'dispatch: true → HubSpot email. Completed output auto-saved to KB with provenance.'}],
    inp:[{f:'client_name',t:'string',r:1},{f:'source',t:'enum',r:1},{f:'agent_name',t:'string',r:1},{f:'dispatch',t:'boolean',r:1},{f:'budget_gbp',t:'integer',r:0}],
    out:[{f:'status',t:'"ok"|"error"'},{f:'message_draft',t:'string'},{f:'hubspot_contact_id',t:'string|null'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'client_name',r:'min 2 chars'},{f:'source',r:'Rightmove|Zoopla|Referral|Direct|Other'},{f:'dispatch',r:'boolean required'}],kyc:0},
  applicant:{ib:'#EEEDFE',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="8" cy="5.5" r="3" stroke="#3C3489" stroke-width="1.3"/><path d="M2 14c0-3.314 2.686-5 6-5s6 1.686 6 5" stroke="#3C3489" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'Register Applicant',s:'POST /api/bot/register-applicant · Claude Sonnet',b:'Running',bc:'bp',
    st:[{c:'sng',n:'1',nm:'Profile intake',d:'Name, email, budget, bedrooms, types, financing, channel, must-haves.'},{c:'sng',n:'2',nm:'HubSpot record',d:'Contact. Lifecycle Stage → Registered & Profiled. Applicant Profile group populated.'},{c:'sng',n:'3',nm:'KYC init',d:'pof_received, id_received, address_received all false.'},{c:'snp',n:'4',nm:'Python hard filter',d:'Budget and bedrooms filter on Buyers: Active.'},{c:'snp',n:'5',nm:'Claude scoring',d:'0.0–1.0: must-haves, financing, timeline. KB context: W11 matching criteria loaded.'},{c:'sna',n:'6',nm:'Output + KB save',d:'Welcome draft + top 3 matches returned. Session auto-saved to KB as SOP.'}],
    inp:[{f:'full_name',t:'string',r:1},{f:'email',t:'string',r:1},{f:'budget_gbp',t:'integer',r:1},{f:'bedrooms_min',t:'integer',r:1},{f:'financing',t:'enum',r:1},{f:'preferred_channel',t:'enum',r:1},{f:'property_types',t:'[string]',r:1},{f:'must_have',t:'[string]',r:0}],
    out:[{f:'applicant_id',t:'string'},{f:'kyc_checklist',t:'object'},{f:'first_matches',t:'[PropertyMatch]'},{f:'welcome_draft',t:'string'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'email',r:'valid format'},{f:'budget_gbp',r:'min 100,000'},{f:'financing',r:'cash|mortgage_aip|mortgage_no_aip|unknown'}],kyc:1},
  match:{ib:'#E1F5EE',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><circle cx="5" cy="8" r="3" stroke="#085041" stroke-width="1.3"/><circle cx="11" cy="8" r="3" stroke="#085041" stroke-width="1.3"/><path d="M8 5v6" stroke="#085041" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'Match Applicants',s:'POST /api/bot/match-applicants · Claude Sonnet',b:'Active',bc:'bg',
    st:[{c:'sng',n:'1',nm:'KB context loaded',d:'W11 matching criteria playbook injected as system context. Applies to scoring and rationale.'},{c:'sng',n:'2',nm:'Python hard filter',d:'Buyers: Active. Budget and bedrooms filter. No AI call.'},{c:'snp',n:'3',nm:'Claude scoring',d:'0.0–1.0 with KB-informed rationale. Plain-English match reason per applicant.'},{c:'sng',n:'4',nm:'Results + KB update',d:'Top N returned. Match rationale appended to KB playbook for future reference.'}],
    inp:[{f:'property_ref',t:'string',r:1},{f:'price_gbp',t:'integer',r:0},{f:'bedrooms',t:'integer',r:0},{f:'features',t:'[string]',r:0},{f:'max_results',t:'integer',r:0}],
    out:[{f:'property',t:'object'},{f:'matches',t:'[ApplicantMatch]'},{f:'total_searched',t:'integer'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'property_ref',r:'required'},{f:'max_results',r:'max 20'},{f:'can_progress',r:'false blocks offer if KYC incomplete'}],kyc:1},
  val:{ib:'#FAEEDA',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 13L6 8l3 3 5-7" stroke="#633806" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/><path d="M2 2v11h12" stroke="#633806" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'Valuation Brief',s:'POST /api/bot/valuation-brief · Claude Opus',b:'3 this month',bc:'ba',
    st:[{c:'sng',n:'1',nm:'KB context loaded',d:'Previous W11 valuation methodology playbook injected. Recency weights and micro-market patterns applied.'},{c:'sng',n:'2',nm:'Land Registry + portal pull',d:'Sold prices, active listings. Recency weighted. 5 comparables max.'},{c:'snp',n:'3',nm:'Claude Opus analysis',d:'Price range, price-per-sqft, market commentary. New patterns flagged for KB update.'},{c:'sna',n:'4',nm:'Brief + KB save',d:'Full brief returned. Any new W11 pricing patterns discovered are appended to KB methodology playbook.'}],
    inp:[{f:'property_address',t:'string',r:1},{f:'postcode',t:'string',r:1},{f:'property_type',t:'enum',r:1},{f:'bedrooms',t:'integer',r:1},{f:'sqft',t:'integer',r:0},{f:'condition',t:'enum',r:0}],
    out:[{f:'sold_comparables',t:'[Comparable]'},{f:'price_range_low',t:'integer'},{f:'price_per_sqft',t:'float|null'},{f:'ai_commentary',t:'string'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'postcode',r:'valid UK format'},{f:'property_type',r:'house|flat|maisonette'}],kyc:0},
  social:{ib:'#FBEAF0',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="2" y="2" width="5" height="5" rx="1.5" stroke="#72243E" stroke-width="1.3"/><rect x="9" y="2" width="5" height="5" rx="1.5" stroke="#72243E" stroke-width="1.3"/><rect x="2" y="9" width="5" height="5" rx="1.5" stroke="#72243E" stroke-width="1.3"/><path d="M11.5 9v6M9 11.5h6" stroke="#72243E" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'Social Content Draft',s:'POST /api/bot/social-draft · Claude Sonnet',b:'New',bc:'bpk',
    st:[{c:'snpk',n:'1',nm:'KB context loaded',d:'Social caption rules playbook + all previously approved captions loaded. Voice consistency improves with every approved post.'},{c:'snp',n:'2',nm:'Claude drafts captions',d:'IG caption (100–150w) and LI caption (100–200w). Rules enforced: no luxury/prestigious/stunning. Pillar-aware.'},{c:'snpk',n:'3',nm:'Photo direction + webhook payload',d:'Photo brief generated. Make.com payload assembled.'},{c:'sna',n:'4',nm:'Approval gate + KB save',d:'Status: draft until approved. On approval → webhook fires + approved caption saved to KB as style reference.'}],
    inp:[{f:'pillar',t:'enum',r:1},{f:'platform',t:'enum',r:1},{f:'post_type',t:'enum',r:1},{f:'theme',t:'string',r:1},{f:'scheduled_date',t:'date',r:1},{f:'canva_design_id',t:'string',r:0}],
    out:[{f:'ig_caption',t:'string'},{f:'li_caption',t:'string'},{f:'ig_hashtags',t:'string'},{f:'photo_direction',t:'string'},{f:'webhook_payload',t:'object'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'pillar',r:'Belonging|Abundance|Discovery|Local Authority'},{f:'voice',r:'no: luxury, prestigious, stunning, opportunity'},{f:'ig_caption',r:'100–150w, no exclamation marks'}],kyc:0},
  outreach:{ib:'#EEEDFE',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M2 4a1 1 0 011-1h10a1 1 0 011 1v1L8 9 2 5V4z" stroke="#3C3489" stroke-width="1.3"/><path d="M2 5v7a1 1 0 001 1h10a1 1 0 001-1V5" stroke="#3C3489" stroke-width="1.3"/></svg>`,t:'Draft Outreach',s:'POST /api/bot/draft-outreach · GPT-4o mini',b:'Daily',bc:'bp',
    st:[{c:'sng',n:'1',nm:'KB context loaded',d:'High-response outreach patterns playbook injected. GPT-4o mini receives same KB context as Claude models.'},{c:'snp',n:'2',nm:'Draft generated',d:'Personalised by recipient_type. ≤120 words for handwritten note. No placeholder text.'},{c:'sng',n:'3',nm:'Returned + pattern update',d:'Human reviews and delivers. High-response patterns flagged for KB update after agent review.'}],
    inp:[{f:'recipient_name',t:'string',r:1},{f:'recipient_type',t:'enum',r:1},{f:'channel',t:'enum',r:1},{f:'agent_name',t:'string',r:1},{f:'context',t:'string',r:0}],
    out:[{f:'draft',t:'string'},{f:'word_count',t:'integer'},{f:'tone_notes',t:'string'}],
    val:[{f:'recipient_type',r:'long_term_resident|recent_enquirer|warm_lead|lapsed'},{f:'channel',r:'email|handwritten_note|letter'}],kyc:0},
  kyc:{ib:'#F1EFE8',is:`<svg width="14" height="14" viewBox="0 0 16 16" fill="none"><rect x="3" y="2" width="10" height="12" rx="2" stroke="#444441" stroke-width="1.3"/><path d="M6 6h4M6 8.5h4M6 11h2" stroke="#444441" stroke-width="1.3" stroke-linecap="round"/></svg>`,t:'KYC / AML Status',s:'GET /api/bot/kyc-status · Claude Haiku',b:'Compliance',bc:'bx',
    st:[{c:'sng',n:'1',nm:'KB context loaded',d:'KYC escalation workflow injected. If blocked status returned, escalation steps are immediately available in context.'},{c:'sna',n:'2',nm:'Gate evaluated + KB log',d:'can_progress: false if any item missing. Blocked cases auto-logged to KB compliance record with timestamp.'}],
    inp:[{f:'name_or_id',t:'string',r:1},{f:'type',t:'enum',r:1}],
    out:[{f:'kyc_status',t:'"complete"|"in_progress"|"not_started"'},{f:'checklist',t:'object'},{f:'outstanding',t:'[string]'},{f:'can_progress',t:'boolean'},{f:'kb_entry_id',t:'string'}],
    val:[{f:'type',r:'client|applicant'},{f:'can_progress',r:'false if any item false'}],kyc:1}
};

let currentFlow = 'welcome';

function selectFlow(id){
  document.querySelectorAll('.fc').forEach(c=>c.classList.remove('sel'));
  const card=document.getElementById('fc-'+id);if(card)card.classList.add('sel');
  const f=FD[id];if(!f)return;
  currentFlow=id;
  document.getElementById('d-icon').style.background=f.ib;
  document.getElementById('d-icon').innerHTML=f.is;
  document.getElementById('d-title').textContent=f.t;
  document.getElementById('d-sub').textContent=f.s;
  document.getElementById('d-badge').textContent=f.b;
  document.getElementById('d-badge').className='badge '+f.bc;
  document.getElementById('d-steps').innerHTML=f.st.map(s=>`<div class="step-it"><div class="sn ${s.c}">${s.n}</div><div><div class="sname">${s.nm}</div><div class="sdetail">${s.d}</div></div></div>`).join('');
  document.getElementById('d-input').innerHTML='<div class="stitle">Input fields</div>'+f.inp.map(i=>`<div class="srow"><span class="sf">${i.f}</span><span class="st">${i.t}</span><span class="${i.r?'sreq':'sopt'}">${i.r?'req':'opt'}</span></div>`).join('');
  document.getElementById('d-output').innerHTML='<div class="stitle">Output fields</div>'+f.out.map(o=>`<div class="srow"><span class="sf">${o.f}</span><span class="st">${o.t}</span></div>`).join('');
  document.getElementById('d-val').innerHTML=f.val.map(v=>`<div class="vrow"><span class="vf">${v.f}</span><span class="vr">${v.r}</span></div>`).join('');
  document.getElementById('d-kyc').style.display=f.kyc?'flex':'none';
}

function filterFlows(cat){
  document.querySelectorAll('.fpill').forEach(p=>p.classList.remove('active'));
  document.getElementById('fa-'+cat).classList.add('active');
  document.querySelectorAll('.fc').forEach(c=>{c.style.display=(cat==='all'||c.dataset.cat===cat)?'':'none'});
}

function filterKB(cat){
  document.querySelectorAll('.kb-filter').forEach(f=>f.classList.remove('active'));
  document.getElementById('kf-'+cat).classList.add('active');
  document.querySelectorAll('.kb-item').forEach(i=>{i.style.display=(cat==='all'||i.dataset.cat===cat)?'':'none'});
}

selectFlow('welcome');
selectKB('kb-match-w11');

// ── SESSION ───────────────────────────────────────────────────
// The workspace needs the token the login page stored. No token: back to login
// with next=<current path>, so sign-in returns to this page (FS-76 blocker A).
// The inline bootstrap in workspace.html also gates the page before any paint;
// this is a defence-in-depth check for when workspace.js executes anyway.
const TOKEN = localStorage.getItem('token');
if (!TOKEN) window.location.replace('/?next=' + location.pathname);

// Explicit sign out from the account menu: no next param, back to a clean login.
function signOut(){
  localStorage.clear();
  window.location.href = '/';
}

// ── AGENT COMMAND WINDOW (FS-76) ──────────────────────────────
// Every command goes to POST /classify first. Two intents are wired to a flow:
//   WELCOME_CLIENT     -> POST /bot/welcome-from-text
//   REGISTER_APPLICANT -> the register form -> POST /bot/register-applicant
// The welcome form (opened from Action Flows > Run flow) posts to /bot/welcome.
// Every other known intent says plainly that it is not connected yet and runs
// nothing. Nothing here ever sends an email: dispatch is always false.
//
// Rule for this file: text that came from the user or from the server is put
// in with textContent / createTextNode, never innerHTML. welcome_draft.html_body
// is deliberately never rendered.

async function postJSON(path, body){
  let res;
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + TOKEN },
      body: JSON.stringify(body),
    });
  } catch (e) {
    return { ok: false, status: 0, data: { detail: 'Could not reach the server.' } };
  }
  if (res.status === 401) {          // expired or missing session: back to login with next
    try { localStorage.clear(); } catch (e) {}
    window.location.replace('/?next=' + window.location.pathname);
    return { ok: false, status: 401, data: { detail: 'Session expired.' } };
  }
  const data = await res.json().catch(() => ({ detail: 'Invalid JSON response' }));
  return { ok: res.ok, status: res.status, data };
}

// Human-readable reason from an error response (errors list, 422 detail list,
// detail string, message, status).
function reasonFrom(data){
  if (data && Array.isArray(data.errors) && data.errors.length) return data.errors.join(', ');
  if (data && Array.isArray(data.detail)) return data.detail.map(d => (d && d.msg) || JSON.stringify(d)).join(', ');
  if (data && typeof data.detail === 'string') return data.detail;
  if (data && typeof data.message === 'string' && data.message) return data.message;
  if (data && typeof data.status === 'string') return data.status;
  return 'Unknown error';
}

// ── tiny DOM builder: text always goes through textContent ────
function mk(tag, attrs, kids){
  const e = document.createElement(tag);
  if (attrs) Object.keys(attrs).forEach(k => {
    const v = attrs[k];
    if (v === undefined || v === null || v === false) return;
    if (k === 'text') e.textContent = v;
    else if (k === 'class') e.className = v;
    else if (k === 'style') e.style.cssText = v;
    else if (k.slice(0, 2) === 'on') e[k] = v;
    else e.setAttribute(k, v === true ? '' : v);
  });
  (kids || []).forEach(c => {
    if (c === null || c === undefined) return;
    e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  });
  return e;
}

// ── the two threads (desktop agent window, mobile agent card) ─
const SURF = {
  desk: { key: 'desk', body: 'agent-body',     typing: 'agent-typing',     mobile: false },
  mob:  { key: 'mob',  body: 'mob-agent-body', typing: 'mob-agent-typing', mobile: true  }
};
const busy = { desk: false, mob: false };

const AVATAR_CSS = 'width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0';
const USER_BUBBLE_CSS = 'background:#F1EFE8;border-radius:12px 12px 2px 12px;padding:8px 12px;font-size:12px;color:#1a1a18;max-width:80%;overflow-wrap:anywhere';
const TONES = {
  card:  'background:#fff;border:1px solid #D3D1C7;color:#1a1a18;',
  plain: 'background:#F5F4F0;color:#1a1a18;',
  ok:    'background:#E1F5EE;border:1px solid #5DCAA5;color:#085041;',
  info:  'background:#E6F1FB;border:1px solid #85B7EB;color:#0C447C;',
  warn:  'background:#FAEEDA;border:1px solid #EF9F27;color:#633806;',
  err:   'background:#FCEBEB;border:1px solid #F09595;color:#A32D2D;'
};
// Class names the Layout spec / FS-76 name for each kind of message.
const TONE_CLASS = {
  card: 'agent-result-card', ok: 'agent-confirmation', info: 'agent-info',
  warn: 'agent-warning', err: 'agent-error', plain: null
};

function toThread(surf, node){
  const body = document.getElementById(surf.body);
  body.appendChild(node);
  body.scrollTop = body.scrollHeight;
  return node;
}

function userMsg(surf, text){
  if (surf.mobile) {
    return toThread(surf, mk('div', { style: 'display:flex;align-items:flex-start;gap:8px;justify-content:flex-end' },
      [mk('div', { class: 'mob-msg-u', style: 'overflow-wrap:anywhere', text })]));
  }
  return toThread(surf, mk('div', { style: 'display:flex;justify-content:flex-end' },
    [mk('div', { style: USER_BUBBLE_CSS, text })]));
}

// One agent message. label = small caption above the bubble (desktop only),
// kids = DOM nodes, tone = key of TONES, wide = stretch to the thread width.
function agentMsg(surf, label, kids, tone, wide){
  tone = tone || 'card';
  const bubble = mk('div', {
    class: [surf.mobile ? 'mob-msg-card' : null, TONE_CLASS[tone]].filter(Boolean).join(' ') || null,
    style: TONES[tone] + 'border-radius:2px 10px 10px 10px;padding:10px 12px;font-size:12px;line-height:1.55;overflow-wrap:anywhere;min-width:0'
  }, kids);
  const inner = [];
  if (label && !surf.mobile) {
    inner.push(mk('div', { class: 'agent-fn-label', style: 'font-size:9px;color:#B4B2A9;margin-bottom:3px;padding-left:2px', text: label }));
  }
  inner.push(bubble);
  const wrap = mk('div', { style: 'min-width:0;max-width:' + (surf.mobile ? '88%' : '92%') + (wide ? ';width:100%' : '') }, inner);
  return toThread(surf, mk('div', { style: 'display:flex;align-items:flex-start;gap:8px' },
    [mk('div', { style: AVATAR_CSS, text: 'AI' }), wrap]));
}

function note(surf, text, tone){
  return agentMsg(surf, null, [mk('div', { text })], tone || 'plain');
}

// Error card (TS 6.3): what went wrong, the reason, and what to do next.
function errorMsg(surf, headline, reason, next){
  const kids = [mk('div', { style: 'font-weight:500', text: headline })];
  if (reason) kids.push(mk('div', { style: 'margin-top:3px', text: reason }));
  kids.push(mk('div', { style: 'margin-top:5px;font-size:11px', text: next }));
  return agentMsg(surf, null, kids, 'err');
}

function showTyping(surf){
  hideTyping(surf);
  toThread(surf, mk('div', { id: surf.typing, role: 'status', style: 'display:flex;align-items:flex-start;gap:8px' }, [
    mk('div', { style: AVATAR_CSS, text: 'AI' }),
    mk('div', { style: 'background:#F5F4F0;border-radius:2px 10px 10px 10px;padding:9px 12px;font-size:12px;color:#888780', text: 'Running flow…' })
  ]));
}
function hideTyping(surf){
  const t = document.getElementById(surf.typing);
  if (t) t.remove();
}

// ── command -> /classify -> flow ──────────────────────────────
const INTENT_LABELS = {
  WELCOME_CLIENT: 'Generate welcome',
  REGISTER_APPLICANT: 'Register applicant',
  MATCH_APPLICANTS: 'Match applicants',
  VALUATION_BRIEF: 'Valuation brief',
  KYC_STATUS: 'KYC status',
  DRAFT_OUTREACH: 'Draft outreach'
};
function intentLabel(intent){
  if (INTENT_LABELS[intent]) return INTENT_LABELS[intent];
  const s = String(intent || '').toLowerCase().replace(/_/g, ' ').trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : 'That flow';
}

async function sendCommand(surf, text){
  text = (text || '').trim();
  if (!text || busy[surf.key]) return;
  busy[surf.key] = true;
  try {
    userMsg(surf, text);
    showTyping(surf);
    const r = await postJSON('/classify', { text });
    hideTyping(surf);
    if (r.status === 401) return;                      // signing out
    if (!r.ok) {
      errorMsg(surf, 'Something went wrong. Nothing was run.', reasonFrom(r.data), 'Try again in a moment. If it keeps happening, tell your administrator.');
      return;
    }
    if (r.data.status !== 'ok') { renderUnknown(surf, r.data); return; }
    if (r.data.intent === 'WELCOME_CLIENT') { await runWelcomeFromText(surf, text); return; }
    if (r.data.intent === 'REGISTER_APPLICANT') { openRegisterForm(surf); return; }
    notConnected(surf, intentLabel(r.data.intent));
  } finally {
    hideTyping(surf);
    busy[surf.key] = false;
  }
}

function renderUnknown(surf, data){
  const list = mk('ul', { style: 'margin:6px 0 0 16px;padding:0;color:#5F5E5A' });
  (Array.isArray(data.capabilities) ? data.capabilities : []).forEach(c => list.appendChild(mk('li', { text: String(c) })));
  agentMsg(surf, 'Not recognised', [
    mk('div', { style: 'font-weight:500', text: data.message || "I can't help with that." }),
    list
  ], 'card');
}

function notConnected(surf, label){
  agentMsg(surf, 'Not connected yet', [
    mk('div', { style: 'font-weight:500', text: label + " isn't connected yet" }),
    mk('div', { style: 'margin-top:4px;color:#5F5E5A', text: 'Nothing was run and nothing was sent. For now this workspace can generate a welcome message and register an applicant.' })
  ], 'card');
}

function draftBlock(text){
  return mk('div', { style: 'white-space:pre-wrap;margin-top:8px', text });
}

async function runWelcomeFromText(surf, text){
  showTyping(surf);
  const r = await postJSON('/bot/welcome-from-text', { text });
  hideTyping(surf);
  if (r.status === 401) return;
  const d = r.data || {};
  if (r.ok && d.status === 'ok' && d.message_draft) {
    const kids = [];
    if (d.extracted) {
      const x = d.extracted;
      let line = ' Client = ' + (x.client_name || '—') + ' · Source = ' + (x.source || '—');
      if (x.budget_gbp) line += ' · Budget = £' + Number(x.budget_gbp).toLocaleString('en-GB');
      if (x.timeline) line += ' · Timeline = ' + x.timeline;
      kids.push(mk('div', { style: 'font-size:10px;color:#5F5E5A' }, [mk('strong', { text: 'Extracted:' }), line]));
    }
    kids.push(draftBlock(d.message_draft));
    agentMsg(surf, 'Generate welcome · draft only, nothing sent', kids, 'card');
  } else {
    errorMsg(surf, 'Draft generation failed', d.message_draft || reasonFrom(d), 'Check the message and try again.');
  }
}

// ── form cards (built with DOM APIs, one per open) ────────────
let formSeq = 0;

function setErr(control, errEl, msg){
  errEl.textContent = msg;
  control.classList.toggle('wf-invalid', !!msg);
  control.setAttribute('aria-invalid', msg ? 'true' : 'false');
}

// Wraps a control with its label and an error line. required => "Required" on blur.
function formField(fid, key, labelText, control, required, errTarget){
  const id = fid + '-' + key;
  control.id = id;
  control.setAttribute('data-field', key);
  const err = mk('div', { class: 'wf-err', id: 'err-' + id, 'data-err': key });
  control.addEventListener('input', () => setErr(control, err, ''));
  control.addEventListener('change', () => setErr(control, err, ''));
  if (required) {
    control.addEventListener('blur', () => { if (!control.value.trim()) setErr(control, err, 'Required'); });
  }
  const label = mk('label', { class: 'wf-label', for: id, text: labelText });
  return { node: mk('div', { class: 'wf-group' }, [label, control, err]), control, err };
}

function textInput(type, placeholder, value){
  return mk('input', { type, placeholder, value, autocomplete: 'off' });
}
function selectOf(options){
  return mk('select', null, [mk('option', { value: '', text: 'Select…' })].concat(
    options.map(o => mk('option', { value: o[0], text: o[1] }))));
}

function openWelcomeForm(surf){
  const fid = 'wf' + (++formSeq);
  const name   = formField(fid, 'client_name', 'Client name *', textInput('text', 'e.g. James Hyde'), true);
  const source = formField(fid, 'source', 'Source *', selectOf(['Rightmove', 'Zoopla', 'Referral', 'Direct', 'Other'].map(s => [s, s])), true);
  const agent  = formField(fid, 'agent_name', 'Agent name *', textInput('text', 'Your name'), true);
  const budget = formField(fid, 'budget_gbp', 'Budget (£)', textInput('number', 'Optional — e.g. 2000000'), false);
  const submit = mk('button', { type: 'submit', class: 'wf-submit', text: 'Generate welcome' });

  let formRow = null;
  const form = mk('form', { class: 'wf', 'data-form': 'welcome', novalidate: true }, [
    mk('div', { class: 'wf-title', text: 'Generate welcome' }),
    name.node, source.node, agent.node, budget.node,
    mk('div', { class: 'wf-note', text: 'Draft only. Nothing is sent.' }),
    submit
  ]);

  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    if (submit.disabled) return;
    [name, source, agent, budget].forEach(f => setErr(f.control, f.err, ''));
    const nm = name.control.value.trim();
    const src = source.control.value;
    const ag = agent.control.value.trim();
    const bud = budget.control.value;
    let valid = true;
    if (!nm) { setErr(name.control, name.err, 'Client name is required'); valid = false; }
    else if (nm.length < 2) { setErr(name.control, name.err, 'Client name must be at least 2 characters'); valid = false; }
    if (!src) { setErr(source.control, source.err, 'Source is required'); valid = false; }
    if (!ag) { setErr(agent.control, agent.err, 'Agent name is required'); valid = false; }
    if (bud && parseInt(bud, 10) < 100000) { setErr(budget.control, budget.err, 'Budget must be at least £100,000'); valid = false; }
    if (!valid) return;

    const body = { client_name: nm, source: src, agent_name: ag, dispatch: false };
    if (bud) body.budget_gbp = parseInt(bud, 10);

    submit.disabled = true;
    try {
      userMsg(surf, 'Generate welcome for ' + nm + ' (' + src + ')');
      showTyping(surf);
      const r = await postJSON('/bot/welcome', body);
      hideTyping(surf);
      if (r.status === 401) return;
      if (r.ok && r.data.message_draft) {
        formRow.remove();                       // the form collapses into the result
        agentMsg(surf, 'Generate welcome · draft only, nothing sent', [draftBlock(r.data.message_draft)], 'card');
      } else {
        errorMsg(surf, 'Could not generate the welcome', reasonFrom(r.data), 'Check the details above and try again.');
      }
    } finally {
      hideTyping(surf);
      submit.disabled = false;
    }
  });

  formRow = agentMsg(surf, 'Generate welcome', [form], 'card', true);
  name.control.focus();
}

function openRegisterForm(surf){
  const fid = 'rf' + (++formSeq);
  const fullName = formField(fid, 'full_name', 'Full name *', textInput('text', 'e.g. Tom Baker'), true);
  const email    = formField(fid, 'email', 'Email *', textInput('email', 'tom@example.com'), true);
  const phone    = formField(fid, 'phone', 'Phone *', textInput('text', '+44 7700 900123'), true);
  const budget   = formField(fid, 'budget', 'Budget (£) *', textInput('number', 'e.g. 2500000'), true);
  const bedMin   = formField(fid, 'bedrooms_min', 'Bedrooms min *', textInput('number', 'e.g. 3', '2'), true);
  const bedMax   = formField(fid, 'bedrooms_max', 'Bedrooms max', textInput('number', 'Optional'), false);
  const financing = formField(fid, 'financing', 'Financing *', selectOf([
    ['cash', 'Cash'], ['mortgage_aip', 'Mortgage (AIP)'], ['mortgage_no_aip', 'Mortgage (no AIP)'], ['unknown', 'Unknown']]), true);
  const channel  = formField(fid, 'preferred_channel', 'Preferred channel *', selectOf([
    ['email', 'Email'], ['phone', 'Phone'], ['whatsapp', 'WhatsApp']]), true);
  const source   = formField(fid, 'source', 'Source *', textInput('text', 'Rightmove, Referral, etc.'), true);
  const timeline = formField(fid, 'timeline_weeks', 'Timeline (weeks)', textInput('number', 'Optional'), false);
  const mustHave = formField(fid, 'must_have', 'Must-have', mk('textarea', { rows: '2', placeholder: 'Optional — e.g. garden, parking, near tube' }), false);

  // property types: a group of checkboxes with its own error line
  const typeBoxes = [['house', 'House'], ['flat', 'Flat'], ['maisonette', 'Maisonette'], ['any', 'Any']].map(t =>
    mk('label', null, [mk('input', { type: 'checkbox', value: t[0], 'data-field': 'property_types' }), ' ' + t[1]]));
  const typesBox = mk('div', { class: 'wf-types', id: fid + '-property_types', role: 'group', 'aria-label': 'Property types' }, typeBoxes);
  const typesErr = mk('div', { class: 'wf-err', id: 'err-' + fid + '-property_types', 'data-err': 'property_types' });
  typesBox.addEventListener('change', () => { typesErr.textContent = ''; });
  const typesNode = mk('div', { class: 'wf-group' }, [
    mk('div', { class: 'wf-label', text: 'Property types * (select one or more)' }), typesBox, typesErr]);

  const submit = mk('button', { type: 'submit', class: 'wf-submit', text: 'Register applicant' });
  let formRow = null;
  const form = mk('form', { class: 'wf', 'data-form': 'register', novalidate: true }, [
    mk('div', { class: 'wf-title', text: 'Register applicant' }),
    fullName.node, email.node, phone.node,
    mk('div', { class: 'wf-row' }, [budget.node, bedMin.node]),
    mk('div', { class: 'wf-row' }, [bedMax.node, timeline.node]),
    mk('div', { class: 'wf-row' }, [financing.node, channel.node]),
    source.node, typesNode, mustHave.node,
    mk('div', { class: 'wf-note', text: 'Creates the applicant and suggests matches. No email is created or sent.' }),
    submit
  ]);

  const all = [fullName, email, phone, budget, bedMin, bedMax, financing, channel, source, timeline, mustHave];

  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    if (submit.disabled) return;
    all.forEach(f => setErr(f.control, f.err, ''));
    typesErr.textContent = '';
    const v = f => f.control.value.trim();
    const full_name = v(fullName), emailV = v(email), phoneV = v(phone);
    const budgetV = parseInt(budget.control.value, 10), bedMinV = parseInt(bedMin.control.value, 10);
    const bedMaxRaw = bedMax.control.value, timelineRaw = timeline.control.value;
    const financingV = financing.control.value, channelV = channel.control.value;
    const sourceV = v(source), mustV = v(mustHave);
    const property_types = Array.from(typesBox.querySelectorAll('input:checked')).map(x => x.value);

    let valid = true;
    const bad = (f, msg) => { setErr(f.control, f.err, msg); valid = false; };
    if (!full_name) bad(fullName, 'Full name is required');
    if (!emailV) bad(email, 'Email is required');
    else if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailV)) bad(email, 'Invalid email');
    if (!phoneV) bad(phone, 'Phone is required');
    if (!budgetV) bad(budget, 'Budget is required');
    if (!bedMinV) bad(bedMin, 'Bedrooms min is required');
    if (!financingV) bad(financing, 'Financing is required');
    if (!channelV) bad(channel, 'Channel is required');
    if (!sourceV) bad(source, 'Source is required');
    if (property_types.length === 0) { typesErr.textContent = 'Pick at least one'; valid = false; }
    if (!valid) return;

    const body = {
      full_name, email: emailV, phone: phoneV, budget: budgetV, bedrooms_min: bedMinV,
      property_types, financing: financingV, preferred_channel: channelV, source: sourceV,
      dispatch: false
    };
    if (bedMaxRaw) body.bedrooms_max = parseInt(bedMaxRaw, 10);
    if (timelineRaw) body.timeline_weeks = parseInt(timelineRaw, 10);
    if (mustV) body.must_have = mustV;

    submit.disabled = true;
    try {
      userMsg(surf, 'Register applicant ' + full_name + ' (' + emailV + ')');
      showTyping(surf);
      const r = await postJSON('/bot/register-applicant', body);
      hideTyping(surf);
      if (r.status === 401) return;
      if (renderRegisterResult(surf, r)) formRow.remove();   // success: the form collapses into the result
    } finally {
      hideTyping(surf);
      submit.disabled = false;
    }
  });

  formRow = agentMsg(surf, 'Register applicant', [form], 'card', true);
  fullName.control.focus();
}

// Subject and plain-text body only, as text. The HTML body is never rendered.
function welcomePreview(draft){
  if (!draft || (!draft.subject && !draft.text_body)) return null;
  const details = mk('details', { style: 'margin-top:8px' }, [
    mk('summary', { style: 'cursor:pointer;font-size:11px;font-weight:500', text: 'Welcome email preview (not sent)' })
  ]);
  if (draft.subject) {
    details.appendChild(mk('div', { style: 'margin:6px 0' }, [mk('strong', { text: 'Subject: ' }), String(draft.subject)]));
  }
  if (draft.text_body) details.appendChild(mk('div', { style: 'white-space:pre-wrap', text: String(draft.text_body) }));
  return details;
}

// Returns true when the applicant was registered or already existed (the form
// can collapse), false when the request failed (the form stays for another go).
function renderRegisterResult(surf, r){
  const data = r.data || {};
  if (!(r.ok && data.status === 'ok' && data.applicant_id)) {
    errorMsg(surf, 'Failed to create contact', reasonFrom(data), 'Check the details above and try again.');
    return false;
  }
  // first_matches: the count only, as the current chat page does.
  const n = Array.isArray(data.first_matches) ? data.first_matches.length : 0;
  const matchNote = n ? ' — ' + n + ' suggested ' + (n === 1 ? 'match' : 'matches') : '';
  if (data.created) {
    agentMsg(surf, 'Register applicant', [
      mk('div', null, ['✓ New applicant registered in HubSpot — ID ', mk('strong', { text: String(data.applicant_id) }), matchNote])
    ], 'ok');
    const preview = welcomePreview(data.welcome_draft);
    if (preview) agentMsg(surf, 'Welcome draft', [preview], 'card', true);
  } else {
    // Existing applicant: NOT overwritten. Show what we hold against what was just typed.
    const diff = (data.diff && typeof data.diff === 'object') ? data.diff : {};
    const kids = [mk('div', null, ['ℹ️ This applicant already exists in HubSpot — ID ', mk('strong', { text: String(data.applicant_id) }), matchNote + '. Their existing record was left unchanged.'])];
    const fields = Object.keys(diff);
    if (fields.length) {
      kids.push(mk('div', { style: 'margin-top:6px', text: 'Differences (not applied — existing record is preserved):' }));
      fields.forEach(field => {
        const d = diff[field] || {};
        const submitted = Array.isArray(d.submitted) ? d.submitted.join('; ') : (d.submitted === null || d.submitted === undefined ? '' : String(d.submitted));
        const existing = Array.isArray(d.existing) ? d.existing.join('; ') : (d.existing === null || d.existing === undefined ? '—' : String(d.existing));
        kids.push(mk('div', { 'data-diff-field': field }, ['• ', mk('strong', { text: field }), ': we hold “' + existing + '”, you entered “' + submitted + '”']));
      });
    } else {
      kids.push(mk('div', { style: 'margin-top:6px', text: 'Nothing differs from what we already hold.' }));
    }
    agentMsg(surf, 'Register applicant', kids, 'info');
  }
  if (Array.isArray(data.errors) && data.errors.length) {
    note(surf, 'Registered, with warnings: ' + data.errors.join(', '), 'warn');
  }
  return true;
}

// ── entry points used by the page ─────────────────────────────
function sendFrom(surf, inputId){
  const input = document.getElementById(inputId);
  const text = input.value.trim();
  if (!text || busy[surf.key]) return;
  input.value = '';
  sendCommand(surf, text);
}
function sendAgent(){ sendFrom(SURF.desk, 'agent-input'); }
function runChip(text){ sendCommand(SURF.desk, text); }

// Action Flows > Run flow: the two wired flows open their form in the Command
// Centre thread; every other flow says it is not connected yet.
function runSelectedFlow(){
  showPage('cc');
  if (currentFlow === 'welcome') { openWelcomeForm(SURF.desk); return; }
  if (currentFlow === 'applicant') { openRegisterForm(SURF.desk); return; }
  const nameEl = document.querySelector('#fc-' + currentFlow + ' .fn');
  notConnected(SURF.desk, nameEl ? nameEl.textContent : 'That flow');
}

function clearAgent() {
  const body = document.getElementById('agent-body');
  while (body.firstChild) body.removeChild(body.firstChild);
  toThread(SURF.desk, mk('div', { style: 'display:flex;align-items:flex-start;gap:8px' }, [
    mk('div', { style: AVATAR_CSS, text: 'AI' }),
    mk('div', { style: 'background:#F5F4F0;border-radius:2px 10px 10px 10px;padding:9px 12px;font-size:12px;color:#1a1a18;line-height:1.55;max-width:90%', text: 'Ready. Type a command or use the chips above to run a flow.' })
  ]));
}


function showMobPage(id) {
  document.querySelectorAll('.mob-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.mob-nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('mob-' + id).classList.add('active');
  document.getElementById('mnav-' + id).classList.add('active');
}

function mobRunChip(text) { sendCommand(SURF.mob, text); }
function mobSendAgent() { sendFrom(SURF.mob, 'mob-agent-input'); }


// ── MODEL SWITCHER ────────────────────────────────────────────
const MODELS = {
  sonnet: { label:'Claude Sonnet', dot:'#7F77DD', tag:'Claude Sonnet · KB loaded' },
  opus:   { label:'Claude Opus',   dot:'#BA7517', tag:'Claude Opus · KB loaded' },
  haiku:  { label:'Claude Haiku',  dot:'#1D9E75', tag:'Claude Haiku · KB loaded' },
  gpt4o:  { label:'GPT-4o',        dot:'#185FA5', tag:'GPT-4o · KB loaded' }
};
let activeModel = 'sonnet';

function toggleModelDD(e){
  e.stopPropagation();
  const dd = document.getElementById('model-dropdown');
  const isOpen = dd.classList.contains('open');
  closeAllDropdowns();
  if(!isOpen) dd.classList.add('open');
}

function selectModel(key, e){
  e.stopPropagation();
  activeModel = key;
  const m = MODELS[key];
  // Update switcher label and dot
  document.getElementById('model-label').textContent = m.label;
  document.getElementById('model-dot').style.background = m.dot;
  // Update active state on options
  Object.keys(MODELS).forEach(k=>{
    document.getElementById('mopt-'+k).classList.toggle('active', k===key);
  });
  // Update agent header tag
  const agentTag = document.getElementById('agent-model-tag');
  if(agentTag) agentTag.textContent = m.tag;
  // Close dropdown
  document.getElementById('model-dropdown').classList.remove('open');
}

function closeAllDropdowns(){
  document.getElementById('model-dropdown').classList.remove('open');
  const ud = document.getElementById('user-dropdown');
  if(ud) ud.classList.remove('open');
}

// ── USER PANEL ────────────────────────────────────────────────
const UP_CONTENT = {
  dashboard: `
    <div class="up-section">
      <div class="up-section-label">Workspace — Curtis Sloane · W11</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:2px">
        <div style="background:#F5F4F0;border-radius:8px;padding:11px 13px">
          <div style="font-size:10px;color:#888780;margin-bottom:6px;font-weight:500">Pipeline</div>
          <div style="display:flex;flex-direction:column;gap:5px">
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">Active buyers</span><span style="font-weight:500;color:#1a1a18">18 <span style="font-size:9px;font-weight:400;color:#0F6E56">↑ target 15 ✓</span></span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">Active clients</span><span style="font-weight:500;color:#1a1a18">7 <span style="font-size:9px;font-weight:400;color:#888780">of 35</span></span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">On market</span><span style="font-weight:500;color:#1a1a18">2</span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">KYC in progress</span><span style="font-weight:500;color:#A32D2D">3 <span style="font-size:9px">⚠</span></span></div>
          </div>
        </div>
        <div style="background:#F5F4F0;border-radius:8px;padding:11px 13px">
          <div style="font-size:10px;color:#888780;margin-bottom:6px;font-weight:500">Operational Intelligence</div>
          <div style="display:flex;flex-direction:column;gap:5px">
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">KB entries</span><span style="font-weight:500;color:#1a1a18">24 <span style="font-size:9px;font-weight:400;color:#0F6E56">+4 this week</span></span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">Context coverage</span><span style="font-weight:500;color:#1D9E75">91%</span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">Agent commands</span><span style="font-weight:500;color:#1a1a18">247</span></div>
            <div style="display:flex;justify-content:space-between;font-size:11px"><span style="color:#5F5E5A">Flows run</span><span style="font-weight:500;color:#1a1a18">18</span></div>
          </div>
        </div>
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Active flows this session</div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <div style="display:flex;align-items:center;gap:9px;padding:7px 10px;background:#F5F4F0;border-radius:7px">
          <span style="width:7px;height:7px;border-radius:50%;background:#7F77DD;flex-shrink:0;display:inline-block"></span>
          <span style="font-size:11px;font-weight:500;color:#1a1a18;flex:1">Register Applicant</span>
          <span style="font-size:9px;color:#5F5E5A">S. Chen · running</span>
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#EEEDFE;color:#3C3489">Live</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px;padding:7px 10px;background:#F5F4F0;border-radius:7px">
          <span style="width:7px;height:7px;border-radius:50%;background:#1D9E75;flex-shrink:0;display:inline-block"></span>
          <span style="font-size:11px;font-weight:500;color:#1a1a18;flex:1">Match Applicants</span>
          <span style="font-size:9px;color:#5F5E5A">14 Ladbroke Rd · 4m ago</span>
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#E1F5EE;color:#085041">Done</span>
        </div>
        <div style="display:flex;align-items:center;gap:9px;padding:7px 10px;background:#FFF8F8;border-radius:7px;border:1px solid #F5DADA">
          <span style="width:7px;height:7px;border-radius:50%;background:#E24B4A;flex-shrink:0;display:inline-block"></span>
          <span style="font-size:11px;font-weight:500;color:#A32D2D;flex:1">KYC / AML Status</span>
          <span style="font-size:9px;color:#888780">Mrs Patterson · blocked</span>
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#FCEBEB;color:#A32D2D">Blocked</span>
        </div>
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Red signals</div>
      <div style="display:flex;flex-direction:column;gap:4px">
        <div style="display:flex;align-items:flex-start;gap:8px;padding:8px 10px;background:#FFF8F8;border:1px solid #F5DADA;border-radius:7px">
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#FCEBEB;color:#A32D2D;flex-shrink:0;margin-top:1px">KYC</span>
          <span style="font-size:11px;color:#791F1F;flex:1">Mrs Patterson — proof of funds, day 6 overdue</span>
        </div>
        <div style="display:flex;align-items:flex-start;gap:8px;padding:8px 10px;background:#FFF8F8;border:1px solid #F5DADA;border-radius:7px">
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#FCEBEB;color:#A32D2D;flex-shrink:0;margin-top:1px">Calls</span>
          <span style="font-size:11px;color:#791F1F;flex:1">94 Portland Rd — outreach calls not started</span>
        </div>
        <div style="display:flex;align-items:flex-start;gap:8px;padding:8px 10px;background:#FFFAF0;border:1px solid #EFD5A5;border-radius:7px">
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#FAEEDA;color:#633806;flex-shrink:0;margin-top:1px">Social</span>
          <span style="font-size:11px;color:#633806;flex:1">7 social posts awaiting your approval</span>
        </div>
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Connections</div>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px">
        ${[['🟠','HubSpot','1,298 contacts','#085041'],['N','Notion','6 docs synced','#085041'],['⚡','Make.com','Social pipeline','#085041'],['✓','Claude API','94 calls today','#085041'],['G','OpenAI','47 drafts','#085041'],['G','Google','Calendar · Drive','#085041']
        ].map(([ic,nm,st,c])=>`<div style="display:flex;align-items:center;gap:6px;padding:7px 9px;background:#F5F4F0;border-radius:7px">
          <span style="font-size:13px;flex-shrink:0">${ic}</span>
          <div style="min-width:0"><div style="font-size:11px;font-weight:500;color:#1a1a18;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${nm}</div><div style="font-size:9px;color:${c}">${st}</div></div>
        </div>`).join('')}
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Plan &amp; billing</div>
      <div style="display:flex;align-items:center;justify-content:space-between;padding:11px 13px;background:#F9FFFB;border:1px solid #5DCAA5;border-radius:9px">
        <div>
          <div style="font-size:12px;font-weight:500;color:#1a1a18">Growth <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#E1F5EE;color:#085041;margin-left:4px">Current</span></div>
          <div style="font-size:10px;color:#5F5E5A;margin-top:2px">£490/month · next billing 1 July 2026</div>
        </div>
        <button class="btn-g" style="font-size:11px" onclick="switchUpTab('settings')">Manage →</button>
      </div>
    </div>`,

  documentation: `
    <div class="up-section">
      <div class="up-section-label">Getting started</div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${[['Agent commands','How to write natural language commands that trigger flows','→'],
           ['Action flows','How each of the 7 flows works, inputs, outputs, and KYC gates','→'],
           ['Knowledge base','How chat captures and flow outputs are stored and retrieved','→'],
           ['HubSpot integration','Lifecycle stages, KYC fields, and automatic activity logging','→'],
           ['Make.com pipeline','How approved social posts are routed to Instagram and LinkedIn','→'],
        ].map(([t,d])=>`<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:#F5F4F0;border-radius:8px;cursor:pointer" onmouseover="this.style.background='#F1EFE8'" onmouseout="this.style.background='#F5F4F0'">
          <div style="flex:1"><div style="font-size:12px;font-weight:500;color:#1a1a18">${t}</div><div style="font-size:10px;color:#888780;margin-top:2px">${d}</div></div>
          <span style="font-size:12px;color:#888780">→</span>
        </div>`).join('')}
      </div>
    </div>
    <div class="up-section">
      <div class="up-section-label">Technical reference</div>
      <div style="display:flex;flex-direction:column;gap:6px">
        ${[['API endpoints','POST /api/bot/* — full request and response schemas'],
           ['Gherkin behaviour spec','BDD scenarios for every interactive element'],
           ['HTML & CSS layout spec','Semantic structure and CSS for Claude Code'],
        ].map(([t,d])=>`<div style="display:flex;align-items:center;gap:10px;padding:10px 12px;background:#F5F4F0;border-radius:8px;cursor:pointer" onmouseover="this.style.background='#F1EFE8'" onmouseout="this.style.background='#F5F4F0'">
          <div style="flex:1"><div style="font-size:12px;font-weight:500;color:#1a1a18">${t}</div><div style="font-size:10px;color:#888780;margin-top:2px">${d}</div></div>
          <span style="font-size:12px;color:#888780">↗</span>
        </div>`).join('')}
      </div>
    </div>`,

  team: `
    <div class="up-section">
      <div class="up-section-label">Team members</div>
      <div class="up-team-row">
        <div class="up-team-av" style="background:#1D9E75;color:#E1F5EE">OK</div>
        <div class="up-team-info"><div class="up-team-name">Olesya Kovalskaya</div><div class="up-team-role">ok@futuresynch.com</div></div>
        <span class="up-team-badge" style="background:#EEEDFE;color:#3C3489">Owner</span>
      </div>
      <div class="up-team-row">
        <div class="up-team-av" style="background:#E1F5EE;color:#085041">CS</div>
        <div class="up-team-info"><div class="up-team-name">Curtis Sloane</div><div class="up-team-role">Principal</div></div>
        <span class="up-team-badge" style="background:#E1F5EE;color:#085041">Admin</span>
      </div>
      <div class="up-team-row">
        <div class="up-team-av" style="background:#EEEDFE;color:#3C3489">M</div>
        <div class="up-team-info"><div class="up-team-name">Marta</div><div class="up-team-role">Applicant Manager</div></div>
        <span class="up-team-badge" style="background:#F1EFE8;color:#444441">Member</span>
      </div>
      <div class="up-team-row">
        <div class="up-team-av" style="background:#FAEEDA;color:#633806">S</div>
        <div class="up-team-info"><div class="up-team-name">Sebastian</div><div class="up-team-role">Property Negotiator</div></div>
        <span class="up-team-badge" style="background:#F1EFE8;color:#444441">Member</span>
      </div>
    </div>
    <div class="up-section">
      <div class="up-section-label">Invite a team member</div>
      <div class="up-field"><label>Email address</label><input type="email" placeholder="name@curtissloane.co.uk"></div>
      <div class="up-field"><label>Role</label><select><option>Member</option><option>Admin</option></select></div>
      <button class="up-save-btn">Send invitation</button>
    </div>`,

  profile: `
    <div class="up-section">
      <div class="up-section-label">Your profile</div>
      <div style="display:flex;align-items:center;gap:14px;margin-bottom:16px">
        <div style="width:48px;height:48px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:600;color:#E1F5EE;flex-shrink:0">OK</div>
        <div><div style="font-size:13px;font-weight:500;color:#1a1a18">Olesya Kovalskaya</div><div style="font-size:11px;color:#888780">ok@futuresynch.com</div></div>
        <button class="btn-g" style="margin-left:auto;font-size:10px">Change photo</button>
      </div>
      <div class="up-row">
        <div class="up-field"><label>First name</label><input type="text" value="Olesya"></div>
        <div class="up-field"><label>Last name</label><input type="text" value="Kovalskaya"></div>
      </div>
      <div class="up-field"><label>Email</label><input type="email" value="ok@futuresynch.com"></div>
    </div>
    <div class="up-section">
      <div class="up-section-label">About you</div>
      <div class="up-field"><label>Your role</label><input type="text" placeholder="e.g. Founder, Principal, Operations Lead"></div>
      <div class="up-field"><label>Description</label><textarea placeholder="A short bio visible to your team. Describe your focus, experience, or anything useful context for the AI to know about you."></textarea></div>
    </div>
    <div class="up-section">
      <div class="up-section-label">Preferences</div>
      <div class="up-field"><label>Default AI model</label><select><option selected>Claude Sonnet (recommended)</option><option>Claude Opus (deeper reasoning)</option><option>Claude Haiku (fastest)</option><option>GPT-4o</option></select></div>
      <div class="up-field"><label>Workspace greeting name</label><input type="text" placeholder="e.g. Curtis — used in agent greeting"></div>
    </div>
    <button class="up-save-btn">Save profile</button>`,

  settings: `
    <div class="up-section">
      <div class="up-section-label">Subscription plan</div>
      <div style="display:flex;flex-direction:column;gap:8px;margin-bottom:10px">

        <div class="up-plan-row" id="plan-starter" onclick="selectPlan('starter')">
          <div class="up-plan-row-left">
            <div class="up-plan-row-name">Starter</div>
            <div class="up-plan-row-feat">Core intake and matching flows — welcome, applicant registration, applicant matching</div>
          </div>
          <div class="up-plan-row-price">£290<span>/mo</span></div>
          <div class="up-plan-row-check" id="pc-starter"></div>
        </div>

        <div class="up-plan-row current" id="plan-growth" onclick="selectPlan('growth')">
          <div class="up-plan-row-left">
            <div class="up-plan-row-name">Growth <span class="up-plan-badge">Current</span></div>
            <div class="up-plan-row-feat">Starter flows + valuation intelligence + KYC / AML compliance tracking</div>
          </div>
          <div class="up-plan-row-price">£490<span>/mo</span></div>
          <div class="up-plan-row-check current" id="pc-growth">✓</div>
        </div>

        <div class="up-plan-row" id="plan-growth-social" onclick="selectPlan('growth-social')">
          <div class="up-plan-row-left">
            <div class="up-plan-row-name">Retainer</div>
            <div class="up-plan-row-feat">Growth flows + social media management, content automation, and brand voice enforcement</div>
          </div>
          <div class="up-plan-row-price">£990<span>/mo</span></div>
          <div class="up-plan-row-check" id="pc-growth-social"></div>
        </div>

        <div class="up-plan-row" id="plan-scale" onclick="selectPlan('scale')">
          <div class="up-plan-row-left">
            <div class="up-plan-row-name">Scale</div>
            <div class="up-plan-row-feat">Retainer flows + financial operations or Business Development Synch module</div>
          </div>
          <div class="up-plan-row-price">£1,490<span>/mo</span></div>
          <div class="up-plan-row-check" id="pc-scale"></div>
        </div>

        <div class="up-plan-row" id="plan-enterprise" onclick="selectPlan('enterprise')" style="border-style:dashed">
          <div class="up-plan-row-left">
            <div class="up-plan-row-name">Enterprise</div>
            <div class="up-plan-row-feat">Full-stack Operational Intelligence — white-label, portfolio reporting, API access, accelerators, VCs, ecosystem operators</div>
          </div>
          <div class="up-plan-row-price" style="font-size:13px;color:#888780;font-weight:400">Custom</div>
          <div class="up-plan-row-check" id="pc-enterprise"></div>
        </div>

      </div>
      <div id="plan-upgrade-bar" style="display:none;padding:10px 12px;background:#F9FFFB;border:1px solid #5DCAA5;border-radius:8px;margin-bottom:8px;font-size:11px;color:#085041;display:flex;align-items:center;gap:10px">
        <span id="plan-upgrade-text" style="flex:1"></span>
        <button class="up-save-btn" style="width:auto;padding:6px 16px;margin-top:0" onclick="confirmPlanChange()">Confirm change</button>
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Payment method</div>
      <div class="up-card-row" style="margin-bottom:12px">
        <span class="up-card-icon">💳</span>
        <div style="flex:1">
          <div style="font-size:12px;font-weight:500;color:#1a1a18">Visa ending 4242</div>
          <div style="font-size:10px;color:#888780;margin-top:1px">Expires 09/27 · Default</div>
        </div>
        <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#E1F5EE;color:#085041">Active</span>
        <button class="btn-g" style="font-size:10px" onclick="toggleAddCard()">+ Add card</button>
      </div>

      <!-- Stripe-style card entry — hidden by default -->
      <div id="stripe-card-form" style="display:none;background:#F9F9F7;border:1px solid #D3D1C7;border-radius:9px;padding:14px;margin-bottom:4px">
        <div style="font-size:10px;font-weight:600;color:#888780;letter-spacing:.5px;text-transform:uppercase;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between">
          Add new card
          <div style="display:flex;gap:5px">
            <span style="font-size:18px" title="Visa">💳</span>
            <span style="font-size:18px" title="Mastercard">🏦</span>
            <span style="font-size:18px" title="Amex">🔐</span>
          </div>
        </div>

        <div class="up-field" style="margin-bottom:12px">
          <label>Card details</label>
          <div id="stripe-card-element"></div>
          <div id="stripe-card-error" role="alert"></div>
        </div>

        <div style="display:flex;align-items:center;gap:7px;margin-bottom:12px;font-size:10px;color:#888780">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 1L2 4v4c0 3 2.5 4.7 5 5.5 2.5-.8 5-2.5 5-5.5V4L8 1z" stroke="#1D9E75" stroke-width="1.3"/><path d="M5.5 8l1.5 1.5L10.5 6" stroke="#1D9E75" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Payments are secured and processed by Stripe. Card details are never stored on My Team AI servers.
        </div>

        <div style="display:flex;gap:8px">
          <button class="up-save-btn" disabled title="Card payments are not connected yet" style="flex:1;margin-top:0">Save card</button>
          <button class="btn-g" onclick="toggleAddCard()" style="padding:9px 16px">Cancel</button>
        </div>
      </div>

      <div id="card-saved-confirm" style="display:none;padding:8px 12px;background:#E1F5EE;border:1px solid #5DCAA5;border-radius:7px;font-size:11px;color:#085041">
        ✓ Card saved and set as default payment method.
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Billing history</div>
      <div style="display:flex;flex-direction:column">
        ${[['1 May 2026','Growth — £490.00','Paid'],
           ['1 Apr 2026','Growth — £490.00','Paid'],
           ['1 Mar 2026','Growth — £490.00','Paid'],
        ].map(([d,desc,s])=>`<div style="display:flex;align-items:center;gap:10px;font-size:11px;padding:8px 0;border-bottom:1px solid #F5F4F0">
          <span style="color:#888780;min-width:78px">${d}</span>
          <span style="flex:1;color:#1a1a18">${desc}</span>
          <span style="font-size:9px;font-weight:600;padding:1px 6px;border-radius:3px;background:#E1F5EE;color:#085041">${s}</span>
          <button class="btn-g" style="font-size:9px;padding:2px 8px">PDF ↓</button>
        </div>`).join('')}
      </div>
    </div>

    <div class="up-section">
      <div class="up-section-label">Danger zone</div>
      <button class="up-danger-btn">Cancel subscription</button>
      <button class="up-danger-btn" style="margin-top:6px">Delete workspace</button>
    </div>`
};

const UP_TITLES = {dashboard:'Dashboard',documentation:'Documentation',team:'Team',profile:'Profile',settings:'Settings'};
let currentUpTab = 'dashboard';

function toggleUserDD(e){
  e.stopPropagation();
  const dd = document.getElementById('user-dropdown');
  const isOpen = dd.classList.contains('open');
  closeAllDropdowns();
  if(!isOpen) dd.classList.add('open');
}
function closeUserDD(){
  document.getElementById('user-dropdown').classList.remove('open');
}
function openUserPanel(tab){
  closeUserDD();
  currentUpTab = tab;
  document.getElementById('up-overlay').classList.add('open');
  renderUpPanel(tab);
}
function closeUserPanel(){
  document.getElementById('up-overlay').classList.remove('open');
}
function overlayClick(e){
  if(e.target === document.getElementById('up-overlay')) closeUserPanel();
}
function switchUpTab(tab){
  currentUpTab = tab;
  renderUpPanel(tab);
}
function renderUpPanel(tab){
  document.getElementById('up-panel-title').textContent = UP_TITLES[tab];
  document.getElementById('up-body').innerHTML = UP_CONTENT[tab] || '';
  document.querySelectorAll('.up-tab').forEach(t=>{
    t.classList.toggle('active', t.textContent.toLowerCase() === tab);
  });
}
// Close all dropdowns on outside click
document.addEventListener('click', ()=> closeAllDropdowns());

// ── SETTINGS — PLAN SELECTION ─────────────────────────────────
const PLAN_LABELS = {
  'starter':      'Starter — £290/mo',
  'growth':       'Growth — £490/mo',
  'growth-social':'Retainer — £990/mo',
  'scale':        'Scale — £1,490/mo',
  'enterprise':   'Enterprise — Custom pricing'
};
let pendingPlan = null;
let currentPlan = 'growth';

function selectPlan(key){
  if(key === currentPlan) return;
  // Clear all pending states
  document.querySelectorAll('.up-plan-row').forEach(r=>r.classList.remove('selected-pending'));
  document.querySelectorAll('.up-plan-row-check').forEach(c=>{c.textContent='';c.classList.remove('current');c.style.background='';c.style.borderColor='';});
  // Mark current
  const curEl = document.getElementById('pc-'+currentPlan);
  if(curEl){curEl.classList.add('current');curEl.textContent='✓';curEl.style.background='#1D9E75';curEl.style.borderColor='#1D9E75';}
  document.getElementById('plan-'+currentPlan)?.classList.add('current');
  // Mark selected pending
  pendingPlan = key;
  document.getElementById('plan-'+key)?.classList.add('selected-pending');
  const sel = document.getElementById('pc-'+key);
  if(sel){sel.textContent='○';sel.style.background='#7F77DD';sel.style.borderColor='#7F77DD';sel.style.color='#fff';}
  // Show upgrade bar
  const bar = document.getElementById('plan-upgrade-bar');
  const txt = document.getElementById('plan-upgrade-text');
  if(bar && txt){
    const isUp = ['growth','growth-social','scale','enterprise'].indexOf(key) > ['growth','growth-social','scale','enterprise'].indexOf(currentPlan);
    txt.textContent = (isUp ? '↑ Upgrade to ' : '↓ Change to ') + PLAN_LABELS[key] + ' — change takes effect on next billing date.';
    bar.style.display='flex';
  }
}

function confirmPlanChange(){
  if(!pendingPlan) return;
  // Clear all
  document.querySelectorAll('.up-plan-row').forEach(r=>r.classList.remove('selected-pending','current'));
  document.querySelectorAll('.up-plan-row-check').forEach(c=>{c.textContent='';c.classList.remove('current');c.style.background='';c.style.borderColor='';});
  currentPlan = pendingPlan;
  pendingPlan = null;
  // Set new current
  document.getElementById('plan-'+currentPlan)?.classList.add('current');
  const el = document.getElementById('pc-'+currentPlan);
  if(el){el.classList.add('current');el.textContent='✓';el.style.background='#1D9E75';el.style.borderColor='#1D9E75';el.style.color='#fff';}
  // Hide bar, show confirmation
  const bar = document.getElementById('plan-upgrade-bar');
  if(bar) bar.style.display='none';
  // Flash text
  const txt = document.getElementById('plan-upgrade-text');
  if(txt){bar.style.display='flex';bar.style.borderColor='#5DCAA5';bar.style.background='#E1F5EE';txt.textContent='✓ Plan updated. Change takes effect on your next billing date.';}
}

// ── SETTINGS — CARD FORM ──────────────────────────────────────
function toggleAddCard(){
  const form = document.getElementById('stripe-card-form');
  const confirm = document.getElementById('card-saved-confirm');
  if(!form) return;
  const isOpen = form.style.display !== 'none';
  form.style.display = isOpen ? 'none' : 'block';
  if(confirm) confirm.style.display = 'none';
}
