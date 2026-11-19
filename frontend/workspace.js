
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

function selectFlow(id){
  document.querySelectorAll('.fc').forEach(c=>c.classList.remove('sel'));
  const card=document.getElementById('fc-'+id);if(card)card.classList.add('sel');
  const f=FD[id];if(!f)return;
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
// The workspace needs the token the login page stored. No token: back to login.
const TOKEN = localStorage.getItem('token');
if (!TOKEN) window.location.replace('/');

function signOut(){
  localStorage.clear();
  window.location.href = '/';
}

// ── AGENT COMMAND WINDOW ──────────────────────────────────────
const AGENT_RESPONSES = {
  match: {
    fn: 'Match Applicants · Buyers: Active · 18 searched · 1.4s · W11 criteria from KB',
    html: `<div style="font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:7px">Top matches — 14 Ladbroke Road W11</div>
      <div class="mr"><span class="ma">Sarah Chen · £3.8M · cash</span><span class="sh">0.94</span><span class="mky kyo">KYC ✓</span></div>
      <div class="mr"><span class="ma">James Hyde · £3.2M · AIP</span><span class="sh">0.81</span><span class="mky kyo">KYC ✓</span></div>
      <div class="mr" style="margin-bottom:8px"><span class="ma">Tom Baker · £2.9M · AIP pend.</span><span class="sm">0.72</span><span class="mky kyw">KYC blocked</span></div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8">
        <button class="cab" onclick="agentAction('draft-intros')">Draft intros</button>
        <button class="cab" onclick="agentAction('hubspot')">Log to HubSpot</button>
        <button class="cab" onclick="agentAction('set-task')">Set viewing task</button>
        <button class="cab" style="border-color:#AFA9EC;color:#3C3489" onclick="agentAction('save-kb')">Save to KB</button>
      </div>`
  },
  register: {
    fn: 'Register Applicant · HubSpot · KYC initiated · 2.1s',
    html: `<div style="font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:7px">Applicant registered — James Hyde</div>
      <div style="font-size:11px;color:#5F5E5A;line-height:1.6">£3.2M · 4 bed · AIP held · Email preferred<br>HubSpot record created · Lifecycle Stage: Registered & Profiled<br>KYC checklist initiated · pof_received: false · id_received: false</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8;margin-top:8px">
        <button class="cab" onclick="agentAction('send-welcome')">Send welcome email</button>
        <button class="cab" onclick="agentAction('first-match')">Run first match</button>
        <button class="cab" onclick="agentAction('kyc-chase')">Set KYC task</button>
      </div>`
  },
  valuation: {
    fn: 'Valuation Brief · Land Registry + Zoopla · Claude Opus · 3.8s · KB: W11 methodology loaded',
    html: `<div style="font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:7px">Valuation brief — 22 Abbotsbury Road W11</div>
      <div style="font-size:11px;color:#5F5E5A;line-height:1.7">Guide price range: <strong style="color:#1a1a18">£3.6M – £3.9M</strong><br>Price per sq ft: <strong style="color:#1a1a18">£1,420 – £1,540</strong><br>5 comparables · recency weighted · spring 2026<br>South-facing garden premium applied (+9%)</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8;margin-top:8px">
        <button class="cab" onclick="agentAction('save-kb')">Save to KB</button>
        <button class="cab" onclick="agentAction('send-brief')">Send to client</button>
      </div>`
  },
  kyc: {
    fn: 'KYC / AML Status · HubSpot · Claude Haiku · 0.6s',
    html: `<div style="font-size:11px;font-weight:500;color:#A32D2D;margin-bottom:7px">KYC blocked — Mrs Patterson</div>
      <div style="font-size:11px;color:#5F5E5A;line-height:1.7">pof_received: <strong style="color:#A32D2D">false</strong> · Day 6 overdue<br>id_received: ✓ &nbsp; address_received: ✓<br>can_progress: <strong style="color:#A32D2D">false</strong> — no property introductions until clear</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8;margin-top:8px">
        <button class="cab" onclick="agentAction('whatsapp-chase')">Draft WhatsApp chase</button>
        <button class="cab" onclick="agentAction('escalate')">Escalate to manager</button>
        <button class="cab" onclick="agentAction('set-task')">Set follow-up task</button>
      </div>`
  },
  outreach: {
    fn: 'Draft Outreach · GPT-4o mini · Long-term W11 residents · 1.1s',
    html: `<div style="font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:7px">Outreach draft — 30-year W11 residents</div>
      <div style="font-size:11px;color:#5F5E5A;font-style:italic;line-height:1.7;background:#F9F9F7;padding:8px 10px;border-radius:6px;margin-bottom:8px">"Dear [Name], Spring on Portland Road is always a good moment to pause and think about what's next. If you've ever wondered what your home might achieve in today's market, I'd love to walk you through it — no pressure, just a conversation. Curtis."</div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8">
        <button class="cab" onclick="agentAction('approve-send')">Approve &amp; send</button>
        <button class="cab" onclick="agentAction('save-kb')">Save pattern to KB</button>
        <button class="cab" onclick="agentAction('regenerate')">Regenerate</button>
      </div>`
  },
  social: {
    fn: 'Social Content Draft · Claude Sonnet · Abundance pillar · brand voice from KB · 1.8s',
    html: `<div style="font-size:11px;font-weight:500;color:#1a1a18;margin-bottom:7px">Social draft — CS-04 · Wisteria season</div>
      <div style="font-size:11px;color:#5F5E5A;font-style:italic;line-height:1.7;background:#F9F9F7;padding:8px 10px;border-radius:6px;margin-bottom:8px"><strong style="font-style:normal;font-size:10px;color:#888780">Instagram · 127 words</strong><br>"The wisteria on Addison Road has come back. It does this every year — quietly, extravagantly — and every year it stops people on the pavement. This is what we mean when we say Holland Park is not just a postcode. It is a place that gives something back."<br><span style="font-size:10px;color:#888780">#HollandPark #W11 #CurtisSloane</span></div>
      <div style="display:flex;gap:5px;flex-wrap:wrap;padding-top:8px;border-top:1px solid #F1EFE8">
        <button class="cab" onclick="agentAction('approve-post')" style="background:#1D9E75;border-color:#1D9E75;color:#E1F5EE">Approve &amp; schedule</button>
        <button class="cab" onclick="agentAction('save-kb')">Save to KB</button>
        <button class="cab" onclick="agentAction('regenerate')">Regenerate</button>
      </div>`
  },
  default: {
    fn: 'Claude Sonnet · KB context loaded',
    html: `<div style="font-size:11px;color:#5F5E5A;line-height:1.65">I can run these flows from a natural language command:<br><br>
      <span style="font-weight:500;color:#1a1a18">Match applicants</span> — "match for [address]"<br>
      <span style="font-weight:500;color:#1a1a18">Register applicant</span> — "register [name], [budget], [beds]"<br>
      <span style="font-weight:500;color:#1a1a18">Valuation brief</span> — "valuation brief [address]"<br>
      <span style="font-weight:500;color:#1a1a18">KYC check</span> — "KYC status [name]"<br>
      <span style="font-weight:500;color:#1a1a18">Draft outreach</span> — "draft outreach for [segment]"<br>
      <span style="font-weight:500;color:#1a1a18">Social draft</span> — "draft social [pillar/theme]"<br>
      <span style="font-weight:500;color:#1a1a18">Set task</span> — "set task [description] for [person]"<br><br>
      Or use the chips above to start any flow instantly.</div>`
  }
};

function detectIntent(text) {
  const t = text.toLowerCase();
  if (t.includes('match') || t.includes('ladbroke') || t.includes('abbotsbury') || t.includes('portland')) return 'match';
  if (t.includes('register') || t.includes('applicant') || t.includes('sign up')) return 'register';
  if (t.includes('valuation') || t.includes('brief') || t.includes('comparable') || t.includes('price')) return 'valuation';
  if (t.includes('kyc') || t.includes('patterson') || t.includes('compliance') || t.includes('aml')) return 'kyc';
  if (t.includes('outreach') || t.includes('resident') || t.includes('database') || t.includes('letter') || t.includes('handwritten')) return 'outreach';
  if (t.includes('social') || t.includes('instagram') || t.includes('linkedin') || t.includes('post') || t.includes('wisteria') || t.includes('caption')) return 'social';
  return 'default';
}

function appendUserMsg(text) {
  const body = document.getElementById('agent-body');
  const el = document.createElement('div');
  el.style.cssText = 'display:flex;justify-content:flex-end';
  el.innerHTML = `<div style="background:#F1EFE8;border-radius:12px 12px 2px 12px;padding:8px 12px;font-size:12px;color:#1a1a18;max-width:80%">${text}</div>`;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
}

function appendTyping() {
  const body = document.getElementById('agent-body');
  const el = document.createElement('div');
  el.id = 'agent-typing';
  el.style.cssText = 'display:flex;align-items:flex-start;gap:8px';
  el.innerHTML = `<div style="width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0">AI</div>
    <div style="background:#F5F4F0;border-radius:2px 10px 10px 10px;padding:9px 12px;font-size:12px;color:#888780">Running flow<span id="dots">.</span></div>`;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
  let d = 0;
  return setInterval(() => { const dots = document.getElementById('dots'); if(dots) dots.textContent = ['.','..',`...`][d++ % 3]; }, 400);
}

function appendAgentMsg(intent) {
  const body = document.getElementById('agent-body');
  const typing = document.getElementById('agent-typing');
  if (typing) typing.remove();
  const r = AGENT_RESPONSES[intent] || AGENT_RESPONSES.default;
  const el = document.createElement('div');
  el.style.cssText = 'display:flex;align-items:flex-start;gap:8px';
  el.innerHTML = `<div style="width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0">AI</div>
    <div style="max-width:92%">
      <div style="font-size:9px;color:#B4B2A9;margin-bottom:3px;padding-left:2px">${r.fn}</div>
      <div style="background:#fff;border:1px solid #D3D1C7;border-radius:2px 10px 10px 10px;padding:10px 12px">${r.html}</div>
    </div>`;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
}

function sendAgent() {
  const input = document.getElementById('agent-input');
  const text = input.value.trim();
  if (!text) return;
  appendUserMsg(text);
  input.value = '';
  const intent = detectIntent(text);
  const timer = appendTyping();
  setTimeout(() => { clearInterval(timer); appendAgentMsg(intent); }, 900 + Math.random() * 600);
}

function runChip(text) {
  appendUserMsg(text);
  const intent = detectIntent(text);
  const timer = appendTyping();
  setTimeout(() => { clearInterval(timer); appendAgentMsg(intent); }, 900 + Math.random() * 600);
}

function agentAction(action) {
  const body = document.getElementById('agent-body');
  const msgs = {
    'draft-intros': '✓ Introduction drafts ready for Sarah Chen and James Hyde — open Messenger to review and approve.',
    'hubspot': '✓ Match logged to HubSpot — 14 Ladbroke Road activity note added to all 3 contact records.',
    'set-task': '✓ Task set — Viewing: Sarah Chen · 14 Ladbroke Road · Thu 24 Apr · assigned to Marta · HubSpot task created.',
    'save-kb': '✓ Saved to Knowledge Base as playbook — available to Claude Sonnet, Opus, Haiku, and GPT-4o automatically.',
    'send-welcome': '✓ Welcome email sent via Gmail — HubSpot Lifecycle Stage updated to Welcome Sent.',
    'first-match': '✓ Running first match for James Hyde — results in a moment.',
    'kyc-chase': '✓ KYC follow-up task set — Marta notified · due today.',
    'whatsapp-chase': '✓ WhatsApp draft ready for Mrs Patterson in Messenger — KYC day 6 escalation tone.',
    'escalate': '✓ Escalated — Curtis notified. Pipeline stage held. KYC log updated.',
    'send-brief': '✓ Valuation brief sent to client — Google Drive copy archived.',
    'approve-send': '✓ Approved and sent — HubSpot activity logged. Next follow-up task set for 7 days.',
    'approve-post': '✓ CS-04 approved — Make.com webhook fired. Instagram and LinkedIn scheduled for 14 Apr 09:00.',
    'regenerate': '↺ Regenerating — new draft in a moment.',
    'kyc-chase': '✓ KYC task created — Marta assigned · due today.'
  };
  const text = msgs[action] || '✓ Done.';
  const el = document.createElement('div');
  el.style.cssText = 'display:flex;align-items:flex-start;gap:8px';
  el.innerHTML = `<div style="width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0">AI</div>
    <div style="background:#E1F5EE;border:1px solid #5DCAA5;border-radius:2px 10px 10px 10px;padding:8px 12px;font-size:11px;color:#085041;max-width:90%">${text}</div>`;
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
}


function showMobPage(id) {
  document.querySelectorAll('.mob-page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.mob-nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('mob-' + id).classList.add('active');
  document.getElementById('mnav-' + id).classList.add('active');
}

function mobAppendMsg(who, html) {
  const body = document.getElementById('mob-agent-body');
  const el = document.createElement('div');
  el.style.cssText = 'display:flex;align-items:flex-start;gap:8px' + (who === 'user' ? ';justify-content:flex-end' : '');
  if (who === 'user') {
    el.innerHTML = `<div class="mob-msg-u">${html}</div>`;
  } else {
    el.innerHTML = `<div style="width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0">AI</div><div class="mob-msg-card" style="max-width:88%">${html}</div>`;
  }
  body.appendChild(el);
  body.scrollTop = body.scrollHeight;
}

function mobRunChip(text) {
  mobAppendMsg('user', text);
  const intent = detectIntent(text);
  setTimeout(() => {
    const r = AGENT_RESPONSES[intent] || AGENT_RESPONSES.default;
    mobAppendMsg('ai', r.html);
  }, 800 + Math.random() * 400);
}

function mobSendAgent() {
  const input = document.getElementById('mob-agent-input');
  const text = input.value.trim();
  if (!text) return;
  mobAppendMsg('user', text);
  input.value = '';
  const intent = detectIntent(text);
  setTimeout(() => {
    const r = AGENT_RESPONSES[intent] || AGENT_RESPONSES.default;
    mobAppendMsg('ai', r.html);
  }, 800 + Math.random() * 400);
}

function clearAgent() {
  const body = document.getElementById('agent-body');
  body.innerHTML = `<div style="display:flex;align-items:flex-start;gap:8px">
    <div style="width:22px;height:22px;border-radius:50%;background:#1D9E75;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:#E1F5EE;flex-shrink:0">AI</div>
    <div style="background:#F5F4F0;border-radius:2px 10px 10px 10px;padding:9px 12px;font-size:12px;color:#1a1a18;line-height:1.55;max-width:90%">Ready. Type a command or use the chips above to run a flow.</div>
  </div>`;
}


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

        <div class="up-field" style="margin-bottom:10px">
          <label>Name on card</label>
          <input type="text" id="cc-name" placeholder="Olesya Kovalskaya" autocomplete="cc-name">
        </div>

        <div class="up-field" style="margin-bottom:10px">
          <label>Card number</label>
          <div style="position:relative">
            <input type="text" id="cc-number" placeholder="1234 5678 9012 3456" maxlength="19" autocomplete="cc-number" oninput="formatCard(this)" style="padding-right:40px">
            <span id="cc-brand" style="position:absolute;right:10px;top:50%;transform:translateY(-50%);font-size:16px"></span>
          </div>
        </div>

        <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:12px">
          <div class="up-field" style="margin-bottom:0">
            <label>Expiry month</label>
            <select id="cc-month" autocomplete="cc-exp-month">
              <option value="">MM</option>
              ${Array.from({length:12},(_,i)=>{const m=String(i+1).padStart(2,'0');return`<option value="${m}">${m}</option>`}).join('')}
            </select>
          </div>
          <div class="up-field" style="margin-bottom:0">
            <label>Expiry year</label>
            <select id="cc-year" autocomplete="cc-exp-year">
              <option value="">YYYY</option>
              ${Array.from({length:10},(_,i)=>`<option value="${2026+i}">${2026+i}</option>`).join('')}
            </select>
          </div>
          <div class="up-field" style="margin-bottom:0">
            <label>CVC <span style="color:#888780;font-weight:300">(?)</span></label>
            <input type="text" id="cc-cvc" placeholder="•••" maxlength="4" autocomplete="cc-csc" style="letter-spacing:2px">
          </div>
        </div>

        <div style="display:flex;align-items:center;gap:7px;margin-bottom:12px;font-size:10px;color:#888780">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none"><path d="M8 1L2 4v4c0 3 2.5 4.7 5 5.5 2.5-.8 5-2.5 5-5.5V4L8 1z" stroke="#1D9E75" stroke-width="1.3"/><path d="M5.5 8l1.5 1.5L10.5 6" stroke="#1D9E75" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>
          Payments are secured and processed by Stripe. Card details are never stored on My Team AI servers.
        </div>

        <div style="display:flex;gap:8px">
          <button class="up-save-btn" onclick="saveCard()" style="flex:1;margin-top:0">Save card</button>
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

function formatCard(input){
  let v = input.value.replace(/\D/g,'').substring(0,16);
  input.value = v.replace(/(.{4})/g,'$1 ').trim();
  // Brand detection
  const brand = document.getElementById('cc-brand');
  if(brand){
    if(/^4/.test(v)) brand.textContent='💳';
    else if(/^5[1-5]/.test(v)) brand.textContent='🏦';
    else if(/^3[47]/.test(v)) brand.textContent='🔐';
    else brand.textContent='';
  }
}

function saveCard(){
  const name = document.getElementById('cc-name')?.value.trim();
  const num  = document.getElementById('cc-number')?.value.replace(/\s/g,'');
  const mon  = document.getElementById('cc-month')?.value;
  const yr   = document.getElementById('cc-year')?.value;
  const cvc  = document.getElementById('cc-cvc')?.value;
  if(!name || num.length < 13 || !mon || !yr || cvc.length < 3){
    alert('Please complete all card fields.');
    return;
  }
  // Show confirmation, hide form
  document.getElementById('stripe-card-form').style.display='none';
  const conf = document.getElementById('card-saved-confirm');
  if(conf) conf.style.display='block';
}
