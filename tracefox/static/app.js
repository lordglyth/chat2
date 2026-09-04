let currentJob=null, currentData=null, filter='found', pollTimer=null;
const $=id=>document.getElementById(id);

async function loadModels(){
  try{
    const r=await fetch('/api/models'); const d=await r.json();
    $('model').innerHTML='';
    if(d.models.length){
      d.models.forEach(m=>{const o=document.createElement('option');o.value=m;o.textContent=m;$('model').appendChild(o)});
      $('ollamaStatus').textContent=`Ollama online · ${d.models.length} model${d.models.length===1?'':'s'}`;
    }else{
      const o=document.createElement('option');o.textContent='No local models detected';o.value='';$('model').appendChild(o);
      $('ollamaStatus').textContent='Ollama not detected · scanner still works';
    }
  }catch{$('ollamaStatus').textContent='Ollama check failed'}
}

async function startScan(){
  const username=$('username').value.trim(); if(!username)return;
  $('searchBtn').disabled=true; $('results').innerHTML=''; $('summary').classList.add('hidden'); $('toolbar').classList.add('hidden'); $('analysisCard').classList.add('hidden');
  $('progressCard').classList.remove('hidden'); $('progressText').textContent=`Scanning @${username}…`; $('barFill').style.width='0%';
  const body={username,concurrency:Number($('concurrency').value)||30,refresh_sites:$('refresh').checked};
  const r=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  if(!r.ok){alert(await r.text());$('searchBtn').disabled=false;return}
  currentJob=(await r.json()).job_id; poll();
}

async function poll(){
  const r=await fetch(`/api/jobs/${currentJob}`); const d=await r.json(); currentData=d;
  const pct=d.total?Math.round(d.done/d.total*100):0;
  $('progressNum').textContent=`${d.done || 0} / ${d.total || '?'}`; $('barFill').style.width=`${pct}%`;
  $('liveFound').textContent=d.live_found?.length?`${d.live_found.length} possible profile${d.live_found.length===1?'':'s'} found so far`:'No matches yet';
  if(d.state==='complete'){finish(d);return}
  if(d.state==='failed'){ $('progressText').textContent=`Scan failed: ${d.error}`;$('searchBtn').disabled=false;return }
  pollTimer=setTimeout(poll,650);
}

function finish(d){
  $('searchBtn').disabled=false; $('progressText').textContent=`Complete · site definitions: ${d.site_source}`; $('barFill').style.width='100%';
  const c=d.counts||{}; $('summary').innerHTML=[['Found',c.found||0],['Uncertain',c.unknown||0],['Errors',c.error||0],['Checked',d.results?.length||0]].map(([k,v])=>`<div class="stat"><b>${v}</b><span>${k}</span></div>`).join('');
  $('summary').classList.remove('hidden'); $('toolbar').classList.remove('hidden'); $('analysisCard').classList.remove('hidden');
  $('exports').innerHTML=`<a href="/api/export/${d.id}.json">JSON</a><a href="/api/export/${d.id}.csv">CSV</a>`; renderResults(); if(d.analysis)renderAnalysis(d.analysis);
}

function esc(s){return String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function renderResults(){
  if(!currentData)return; const list=(currentData.results||[]).filter(r=>filter==='all'||r.status===filter);
  $('results').innerHTML=list.map(r=>{const m=r.metadata||{};return `<article class="result ${esc(r.status)}"><div class="top">${m.avatar?`<img class="avatar" src="${esc(m.avatar)}" referrerpolicy="no-referrer" onerror="this.style.display='none'">`:`<div class="avatar"></div>`}<div><h3>${esc(r.site)}</h3><div class="category">${esc(r.category)}</div></div></div><span class="badge">${esc(r.status)}</span>${m.title?`<p><strong>${esc(m.title)}</strong></p>`:''}${m.description?`<p>${esc(m.description.slice(0,420))}</p>`:''}<a target="_blank" rel="noopener noreferrer" href="${esc(r.profile_url)}">Open public profile ↗</a></article>`}).join('') || '<div class="muted">Nothing in this filter.</div>';
}

document.querySelectorAll('.filter').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.filter').forEach(x=>x.classList.remove('active'));b.classList.add('active');filter=b.dataset.filter;renderResults()}));

async function analyze(){
  const model=$('model').value;if(!model){alert('Start Ollama and install/select a model first.');return}
  $('analyzeBtn').disabled=true;$('analysis').innerHTML='<p class="muted">Your local model is chewing on the matches…</p>';
  const r=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({job_id:currentJob,model})});
  $('analyzeBtn').disabled=false;if(!r.ok){$('analysis').innerHTML=`<p>${esc(await r.text())}</p>`;return} const d=await r.json(); currentData.analysis=d;renderAnalysis(d);
}
function renderAnalysis(a){
  let html=`<div class="analysis-summary">${esc(a.summary||'No summary')} <span class="risk">collision risk: ${esc(a.collision_risk||'unknown')}</span></div>`;
  (a.clusters||[]).forEach(c=>{html+=`<div class="cluster"><h3>${esc(c.label)} · ${esc(c.confidence)}%</h3><small>${esc((c.sites||[]).join(', '))}</small>${c.evidence?.length?`<p><b>Evidence:</b> ${esc(c.evidence.join(' · '))}</p>`:''}${c.conflicts?.length?`<p><b>Conflicts:</b> ${esc(c.conflicts.join(' · '))}</p>`:''}</div>`});
  if(a.notes?.length)html+=`<p class="muted">${esc(a.notes.join(' · '))}</p>`;$('analysis').innerHTML=html;
}

$('searchBtn').addEventListener('click',startScan);$('username').addEventListener('keydown',e=>{if(e.key==='Enter')startScan()});$('analyzeBtn').addEventListener('click',analyze);loadModels();
