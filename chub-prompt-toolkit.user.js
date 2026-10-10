// ==UserScript==
// @name         Chub Master Toolkit (Vault + HUD + Reply Gen + ACTI)
// @namespace    https://github.com/Kattalassien
// @version      3.0.0
// @description  One Chub.ai userscript: preset vault (import/export vault, SillyTavern and chub-vault formats), composer injection, roleplay HUD chips, {{user}} reply generator, prompt fixer, token reducer, ACTI/iOS Shortcuts bridge, OpenRouter model quick-picks, error log, optional Supabase sync.
// @author       Preston
// @match        https://chub.ai/*
// @match        https://*.chub.ai/*
// @match        https://venus.chub.ai/*
// @grant        GM_addStyle
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_setClipboard
// @grant        GM_xmlhttpRequest
// @connect      openrouter.ai
// @connect      *.supabase.co
// @run-at       document-idle
// ==/UserScript==
(function () {
  'use strict';
  if (window.__chubMaster) return;

  // ---------- storage ----------
  const NS = 'chubMaster.v3.';
  const store = {
    get(k, d) { try { if (typeof GM_getValue === 'function') return GM_getValue(NS + k, d); } catch (e) {} try { const v = localStorage.getItem(NS + k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } },
    set(k, v) { try { if (typeof GM_setValue === 'function') return GM_setValue(NS + k, v); } catch (e) {} try { localStorage.setItem(NS + k, JSON.stringify(v)); } catch (e) {} }
  };
  const uid = () => 'p_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  const clone = o => JSON.parse(JSON.stringify(o));
  const $ = (s, r) => (r || document).querySelector(s);

  // ---------- error log ----------
  const log = (level, msg) => { const l = store.get('log', []); l.push({ t: new Date().toISOString(), level, msg: String(msg) }); store.set('log', l.slice(-100)); };
  window.addEventListener('error', e => log('error', e.message));
  window.addEventListener('unhandledrejection', e => log('error', e.reason));

  // ---------- defaults (generated from the master presets) ----------
  const DEFAULTS = {
  "app": "chub-master",
  "version": 3,
  "gen": {
    "model": "deepseek/deepseek-v4-flash:floor",
    "temperature": 0.9,
    "top_p": 0.95,
    "min_p": 0.03,
    "repetition_penalty": 1.05
  },
  "presets": [
    {
      "id": "master-rp",
      "name": "Master Roleplay (Lexi/Robin)",
      "modules": [
        {
          "id": "main",
          "label": "Main prompt",
          "enabled": true,
          "text": "You are the Game Master and lead writer of an immersive, slow-burn family drama with a supernatural secret. Voice {{char}} and every NPC in the scene (Lexi, Robin, Lil Bro). Never speak, act, think, or decide for {{user}}; treat {{user}}'s actions as attempts, narrate outcomes, and end on a moment {{user}} can respond to.\nKNOWLEDGE: characters know only what they have seen, heard, or could reasonably infer. They are ignorant of {{user}}'s private thoughts, secrets, and anything outside their world, and they misread things realistically.\nREALISM: natural, imperfect speech: interruptions, hesitation, deflection, subtext. Reactions fit personality, mood, and history; nobody is overly agreeable or convenient. Show emotion through behavior, not labels.\nPACING: be proactive. Give NPCs goals and small complications; advance one or two beats per reply; no cliches, repeated openings, filler, or abrupt time skips. Track positions, items, injuries, time, and established facts; never invent canon for the user.\nFORMAT: third person, \"speech in double quotes\", *actions in italics*, 2-4 paragraphs scaled to the scene. Everyone here is family or household: keep the story free of romance and sexual content."
        },
        {
          "id": "mech",
          "label": "Mechanics footer",
          "enabled": true,
          "text": "After every reply, append exactly this footer (no deviations):\n```\nINTERNAL MONOLOGUE: <2-3 lines of {{char}}'s private thoughts that may contradict her words>\nFATE ROLL: d20 = <n> (<Critical Fail 1 | Fail 2-9 | Mixed 10-14 | Success 15-19 | Critical Success 20>)\nHUD: [Location] | [Time] | [Mood: Lexi/Robin/Lil Bro] | [Secret Meter: <0-5>/5]\nDynamic Continuation Branches:\n1. <short option>\n2. <short option>\n3. <short option>\nOOC Director Note: <one line on pacing or what is being seeded>\n```\nFATE ROLL rules: roll fresh each reply, only for uncertain outcomes (a risky action, a social gamble, a power slipping out). Never roll for {{user}}'s choices, only for how the world responds. Low rolls bring complications, not dead ends. Never reroll or fudge.\nSECRET METER: starts at 0. +1 when {{user}}'s hidden powers visibly slip in front of family; -1 when they successfully cover it. At 3, Lexi gets suspicious. At 5, the secret is exposed and the family must react."
        },
        {
          "id": "post",
          "label": "Post-history",
          "enabled": true,
          "text": "[Stay in character. Never write {{user}}'s actions. Keep the footer format exactly: INTERNAL MONOLOGUE, FATE ROLL, HUD, Dynamic Continuation Branches, OOC Director Note. Update the Secret Meter honestly. Do not repeat phrases from earlier replies.]"
        }
      ]
    },
    {
      "id": "lowcost-or",
      "name": "Low-Cost OpenRouter",
      "modules": [
        {
          "id": "main",
          "label": "Main prompt",
          "enabled": true,
          "text": "Write {{char}}'s next reply in a slow-burn roleplay with {{user}}, voicing {{char}} and every NPC present. Never write {{user}}'s words, actions, thoughts, or choices; end on an opening for them. Characters know only what they have seen or heard; they misread, hesitate, deflect, and speak imperfectly. Show emotion through behavior, not labels. Advance the story one small step per reply with an NPC choice or complication. Third person, \"speech\" in quotes, *actions* in italics, 2-3 paragraphs. Keep it free of romance and sexual content. Output the reply and footer directly; never show reasoning or notes."
        },
        {
          "id": "mech",
          "label": "Footer",
          "enabled": true,
          "text": "After the reply append exactly:\nINTERNAL MONOLOGUE: <2-3 lines of {{char}}'s private thoughts; may contradict her words>\nFATE ROLL: d20 = <n> (<Fail 1-9 | Mixed 10-14 | Success 15-19 | Crit 20>)\nHUD: [Location] | [Time] | [Mood: names] | [Secret Meter: <0-5>/5]\nDynamic Continuation Branches:\n1. <short>\n2. <short>\n3. <short>\nOOC Director Note: <one line>\nRoll fresh only for uncertain outcomes, never for {{user}}'s choices; low rolls bring complications. Secret Meter: +1 when {{user}}'s hidden powers slip in front of family, -1 when covered, exposure at 5 (ignore if the scenario has no secret)."
        },
        {
          "id": "post",
          "label": "Post-history",
          "enabled": true,
          "text": "[Stay in character. Never write {{user}}'s actions. Keep the footer exactly. No repeated phrases.]"
        }
      ],
      "sampling": {
        "temperature": 0.9,
        "top_p": 0.95,
        "min_p": 0.03,
        "frequency_penalty": 0.2,
        "presence_penalty": 0.2,
        "repetition_penalty": 1.05,
        "max_tokens": 700,
        "context": 32000
      }
    },
    {
      "id": "modular",
      "name": "Modular Add-ons",
      "modules": [
        {
          "id": "director",
          "label": "Director engine",
          "enabled": true,
          "text": "Pacing: if the story drags, introduce a sudden event (weather change, arrival, accident). Plant one subtle unexplained detail per reply."
        },
        {
          "id": "psych",
          "label": "Inner thoughts",
          "enabled": true,
          "text": "Reveal {{char}}'s hidden fears, doubts, and plans as short first-person thoughts in backticks that can contradict spoken words."
        },
        {
          "id": "rpg",
          "label": "RPG mechanics",
          "enabled": false,
          "text": "If a difficult feat is attempted, weigh the odds and describe complications when they are low. Strictly track inventory."
        },
        {
          "id": "hud",
          "label": "Status HUD",
          "enabled": false,
          "text": "End each reply with: [Location] | [Time] | [Status] | [Current Goal: short text]"
        },
        {
          "id": "injury",
          "label": "Injury realism",
          "enabled": false,
          "text": "Describe injuries concretely and physically, without gore for its own sake. Pain has sensation, not just emotion."
        },
        {
          "id": "slowburn",
          "label": "Slow-burn pace",
          "enabled": true,
          "text": "Let trust, suspicion, and revelations build gradually across many replies; never resolve a secret in one scene."
        }
      ]
    }
  ],
  "sel": "master-rp"
};
  const MODELS = [
    ['deepseek/deepseek-v4-flash:floor', 'DeepSeek V4 Flash (cheapest paid, :floor)'],
    ['nvidia/nemotron-3-ultra-550b-a55b:free', 'Nemotron 3 Ultra (free)'],
    ['google/gemma-4-31b-it:free', 'Gemma 4 31B (free)'],
    ['z-ai/glm-5.3-flash', 'GLM 5.3 Flash'],
    ['xiaomi/mimo-v2.6-flash', 'MiMo V2.6 Flash']
  ];
  const getDB = () => store.get('db', null) || (store.set('db', clone(DEFAULTS)), clone(DEFAULTS));
  const setDB = db => store.set('db', db);

  // ---------- import / export converters (pure) ----------
  const SAMPLER_KEYS = ['temperature', 'top_p', 'top_k', 'top_a', 'min_p', 'frequency_penalty', 'presence_penalty', 'repetition_penalty'];
  function fromChubVault(o) {
    return o.presets.map(p => {
      const f = p.fields || {};
      const modules = [];
      if (f.main_prompt) modules.push({ id: 'main', label: 'Main prompt', enabled: true, text: f.main_prompt });
      if (f.jailbreak_prompt) modules.push({ id: 'post', label: 'Post-history', enabled: true, text: f.jailbreak_prompt });
      (p.modules || []).forEach(m => {
        const t = m.patch && m.patch.main_prompt;
        if (t) modules.push({ id: m.id || uid(), label: m.name || m.id || 'Module', enabled: !!m.enabled, text: t });
      });
      const sampling = {}; SAMPLER_KEYS.forEach(k => { if (f[k] != null) sampling[k] = f[k]; });
      return { id: p.id || uid(), name: p.name || 'Imported', modules, sampling, impersonation: f.impersonation_prompt || '' };
    });
  }
  function fromST(o, name) {
    const order = (((o.prompt_order || [])[0] || {}).order) || [];
    const on = {}; order.forEach(x => { on[x.identifier] = x.enabled !== false; });
    const modules = (o.prompts || []).filter(p => !p.marker && typeof p.content === 'string' && p.content.trim())
      .map(p => ({ id: p.identifier || uid(), label: p.name || p.identifier || 'Prompt', enabled: on[p.identifier] !== false, text: p.content }));
    const sampling = {}; SAMPLER_KEYS.forEach(k => { if (o[k] != null) sampling[k] = o[k]; });
    if (o.openai_max_tokens != null) sampling.max_tokens = o.openai_max_tokens;
    if (o.openai_max_context != null) sampling.context = o.openai_max_context;
    return [{ id: uid(), name: name || 'ST preset', modules, sampling, impersonation: o.impersonation_prompt || '' }];
  }
  function normalizeImport(o, fname) {
    if (!o || typeof o !== 'object') throw new Error('Not a JSON object');
    if (o.app === 'acti-chub' && Array.isArray(o.presets)) return { presets: o.presets, gen: o.gen };
    if (o.app === 'chub-master' && Array.isArray(o.presets)) return { presets: o.presets, gen: o.gen };
    if (o.app === 'chub-vault' && Array.isArray(o.presets)) return { presets: fromChubVault(o) };
    if (Array.isArray(o.prompts)) return { presets: fromST(o, (fname || 'ST preset').replace(/\.json$/i, '')) };
    throw new Error('Unknown format (expected vault, chub-vault, or SillyTavern preset)');
  }
  function toST(p, gen) {
    const s = Object.assign({}, p.sampling || {});
    const out = {
      temperature: s.temperature != null ? s.temperature : gen.temperature, frequency_penalty: s.frequency_penalty || 0, presence_penalty: s.presence_penalty || 0,
      top_p: s.top_p != null ? s.top_p : gen.top_p, top_k: s.top_k || 0, top_a: s.top_a || 0, min_p: s.min_p != null ? s.min_p : gen.min_p,
      repetition_penalty: s.repetition_penalty != null ? s.repetition_penalty : gen.repetition_penalty,
      openai_max_context: s.context || 64000, openai_max_tokens: s.max_tokens || 900, stream_openai: true, names_behavior: 0, squash_system_messages: true,
      max_context_unlocked: true, impersonation_prompt: p.impersonation || '[Write one suggested reply from the point of view of {{user}}, matching their style. Do not write dialogue or actions for {{char}}.]',
      new_chat_prompt: '[Start a new Chat]', continue_nudge_prompt: '[Continue your last message without repeating its original content.]',
      wi_format: '{0}', scenario_format: '[Scenario: {{scenario}}]', personality_format: '[{{char}}\'s personality: {{personality}}]', prompts: [], prompt_order: [{ character_id: 100001, order: [] }]
    };
    const markers = ['worldInfoBefore', 'personaDescription', 'charDescription', 'charPersonality', 'scenario', 'worldInfoAfter', 'dialogueExamples', 'chatHistory'];
    const mk = id => ({ identifier: id, name: id, system_prompt: true, marker: true });
    const first = p.modules.filter(m => !/post/i.test(m.id + m.label)), post = p.modules.filter(m => /post/i.test(m.id + m.label));
    const mp = m => ({ identifier: m.id, name: m.label, system_prompt: true, role: 'system', marker: false, content: m.text });
    first.forEach(m => out.prompts.push(mp(m))); markers.forEach(id => out.prompts.push(mk(id))); post.forEach(m => out.prompts.push(mp(m)));
    const seq = first.map(m => m.id).concat(markers, post.map(m => m.id));
    const en = {}; p.modules.forEach(m => { en[m.id] = m.enabled; });
    out.prompt_order[0].order = seq.map(id => ({ identifier: id, enabled: en[id] !== false }));
    return out;
  }
  const compile = p => p.modules.filter(m => m.enabled).map(m => m.text).join('\n\n');
  window.__chubMaster = { normalizeImport, toST, fromST, fromChubVault, compile };

  // ---------- composer helpers ----------
  const composer = () => $('textarea') || $('[contenteditable="true"]');
  function setText(el, text) {
    if (!el) return false;
    if (el.isContentEditable) { el.focus(); document.execCommand('selectAll', false); document.execCommand('insertText', false, text); return true; }
    const setter = Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set;
    setter.call(el, text); el.dispatchEvent(new Event('input', { bubbles: true })); el.focus(); return true;
  }
  const getText = el => el ? (el.isContentEditable ? el.innerText : el.value) : '';
  const insertText = t => { const el = composer(); if (!el) return toast('No input found', 1); const cur = getText(el); setText(el, cur ? cur + (cur.endsWith('\n') ? '' : '\n') + t : t); };
  function copyText(t) { if (typeof GM_setClipboard === 'function') { GM_setClipboard(t); return Promise.resolve(); } return navigator.clipboard.writeText(t); }

  // ---------- prompt fixer ----------
  function fixPrompt(s) {
    return s.replace(/\r\n?/g, '\n').replace(/[\u200B-\u200D\uFEFF]/g, '').replace(/[\u201C\u201D]/g, '"').replace(/[\u2018\u2019]/g, "'")
      .replace(/[ \t]+$/gm, '').replace(/\n{3,}/g, '\n\n').replace(/ {2,}/g, ' ')
      .replace(/\{\{\s*(user|char)\s*\}\}/gi, (m, k) => '{{' + k.toLowerCase() + '}}').trim();
  }

  // ---------- token reducer ----------
  function distill(root, max) {
    root = root || document.body; max = max || 6000;
    const c = root.cloneNode(true);
    c.querySelectorAll('script,style,noscript,svg,img,video,audio,iframe,nav,footer,header,form,button,[aria-hidden="true"],#chub-master-root').forEach(n => n.remove());
    let t = (c.innerText || c.textContent || '').replace(/\s+\n/g, '\n').replace(/\n{3,}/g, '\n\n').replace(/[ \t]{2,}/g, ' ').trim();
    const seen = new Set(); t = t.split('\n').filter(l => { const k = l.trim(); if (k.length < 3 || seen.has(k)) return false; seen.add(k); return true; }).join('\n');
    return t.length > max ? t.slice(-max) : t; // keep the END (latest messages)
  }
  const selectionText = () => (window.getSelection() || '').toString().trim();

  // ---------- ACTI bridge ----------
  function dispatch(actions) {
    const payload = JSON.stringify({ actions });
    const base = location.href.split('#')[0];
    location.href = 'shortcuts://x-callback-url/run-shortcut?name=' + encodeURIComponent('AgentRunner') + '&input=text&text=' + encodeURIComponent(payload) +
      '&x-success=' + encodeURIComponent(base + '#acti=ok') + '&x-error=' + encodeURIComponent(base + '#acti=err');
    log('info', 'dispatch ' + payload.slice(0, 120));
  }
  function checkReturn() {
    const m = location.hash.match(/acti=(ok|err)/); if (!m) return;
    toast(m[1] === 'ok' ? 'Shortcut finished' : 'Shortcut failed', m[1] === 'err');
    history.replaceState(null, '', location.pathname + location.search);
  }

  // ---------- OpenRouter ----------
  function llm(messages, overrides) {
    const key = store.get('orKey', ''); const db = getDB();
    if (!key) return Promise.reject(new Error('Set OpenRouter key in Settings'));
    const g = Object.assign({}, db.gen, overrides || {});
    const body = JSON.stringify({ model: g.model, temperature: g.temperature, top_p: g.top_p, min_p: g.min_p, repetition_penalty: g.repetition_penalty, max_tokens: g.max_tokens || 400, messages });
    return new Promise((res, rej) => {
      const done = txt => { try { const j = JSON.parse(txt); if (j.error) throw new Error(j.error.message || 'API error'); res(j.choices[0].message.content); } catch (e) { rej(new Error(e.message || 'Bad LLM response')); } };
      const hdr = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key, 'X-Title': 'Chub Master Toolkit' };
      if (typeof GM_xmlhttpRequest === 'function') GM_xmlhttpRequest({ method: 'POST', url: 'https://openrouter.ai/api/v1/chat/completions', headers: hdr, data: body, onload: r => done(r.responseText), onerror: () => rej(new Error('Network error')) });
      else fetch('https://openrouter.ai/api/v1/chat/completions', { method: 'POST', headers: hdr, body }).then(r => r.text()).then(done).catch(rej);
    });
  }
  const PLAN_SYS = 'Return ONLY JSON: {"actions":[{"type":"reminder|calendar|clipboard|notify|url","title":"","notes":"","dueDate":"ISO","startDate":"ISO","endDate":"ISO","text":"","message":"","url":""}]}. Use ISO 8601 dates.';
  async function planAndRun(prompt) {
    const raw = await llm([{ role: 'system', content: PLAN_SYS }, { role: 'user', content: prompt }]);
    const j = JSON.parse(raw.replace(/^```json|```$/gim, '').trim());
    if (!Array.isArray(j.actions)) throw new Error('No actions');
    dispatch(j.actions);
  }
  // {{user}} reply generator: mini-prompt -> full in-voice reply
  async function genReply(mini) {
    const db = getDB(); const cur = db.presets.find(p => p.id === db.sel) || db.presets[0];
    const chat = distill(document.body, 5000);
    const sys = (cur.impersonation || 'Write one reply from the point of view of {{user}}, matching their established voice, length and style. Never write dialogue or actions for {{char}}. Output only the reply.') +
      '\nOutput only the reply text, no notes. Use *italics* for actions.';
    return llm([{ role: 'system', content: sys }, { role: 'user', content: 'Recent chat (latest at the bottom):\n' + chat + '\n\nWrite {{user}}\'s next reply. Intent: ' + mini }], { max_tokens: 350 });
  }

  // ---------- Supabase ----------
  async function sbCall(method, path, body) {
    const url = store.get('sbUrl', ''), key = store.get('sbKey', '');
    if (!url || !key) throw new Error('Set Supabase URL + anon key in Settings');
    const r = await fetch(url.replace(/\/$/, '') + '/rest/v1/' + path, { method, headers: { apikey: key, Authorization: 'Bearer ' + key, 'Content-Type': 'application/json', Prefer: 'resolution=merge-duplicates,return=representation' }, body: body ? JSON.stringify(body) : undefined });
    if (!r.ok) throw new Error('Supabase ' + r.status); return r.json();
  }
  const pushCloud = () => sbCall('POST', 'chub_presets?on_conflict=id', getDB().presets.map(p => ({ id: p.id, data: p })));
  const pullCloud = async () => { const rows = await sbCall('GET', 'chub_presets?select=*'); mergeImport({ app: 'chub-master', presets: rows.map(r => r.data) }); };

  // ---------- vault ----------
  function mergeImport(o, fname) {
    const n = normalizeImport(o, fname); const db = getDB(); let add = 0, upd = 0;
    n.presets.forEach(p => {
      if (!p || typeof p.name !== 'string' || !Array.isArray(p.modules)) throw new Error('Bad preset entry');
      p.id = p.id || uid();
      const i = db.presets.findIndex(x => x.id === p.id || x.name === p.name);
      if (i >= 0) { p.id = db.presets[i].id; db.presets[i] = p; upd++; } else { db.presets.push(p); add++; }
    });
    if (n.gen) db.gen = Object.assign(db.gen, n.gen);
    setDB(db); render(); toast('Imported: +' + add + ' / ~' + upd);
  }
  function download(name, text) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' })); a.download = name; document.body.appendChild(a); a.click(); a.remove();
  }

  // ---------- roleplay HUD ----------
  function enhance(node) {
    if (!node || node.nodeType !== 1 || node.dataset.mHud) return;
    const t = node.innerText || '';
    if (!/INTERNAL MONOLOGUE|FATE ROLL|Dynamic Continuation Branches/i.test(t) || t.length > 20000) return;
    if (node.querySelector('[data-m-hud]')) return;
    node.dataset.mHud = '1';
    const m = t.match(/Dynamic Continuation Branches:?\s*([\s\S]*?)(?:OOC Director Note|$)/i);
    const fate = t.match(/FATE ROLL:?\s*([^\n]+)/i);
    const meter = t.match(/Secret Meter:?\s*(\d)\s*\/\s*5/i);
    const wrap = document.createElement('div'); wrap.className = 'm-hud'; wrap.dataset.mHud = '1';
    if (fate) { const b = document.createElement('span'); b.className = 'm-fate'; b.textContent = '🎲 ' + fate[1].trim().slice(0, 60); wrap.appendChild(b); }
    if (meter) { const b = document.createElement('span'); b.className = 'm-fate'; b.textContent = '🔍 ' + meter[1] + '/5'; wrap.appendChild(b); }
    if (m) {
      const box = document.createElement('div'); box.className = 'm-chips';
      m[1].split(/\n|\u2022|\d+[.)]/).map(s => s.trim()).filter(s => s.length > 5).slice(0, 5).forEach(s => {
        const c = document.createElement('button'); c.className = 'm-chip'; c.textContent = s.length > 50 ? s.slice(0, 48) + '…' : s; c.title = s;
        c.onclick = e => { e.preventDefault(); insertText(s); }; box.appendChild(c);
      }); wrap.appendChild(box);
    }
    if (wrap.childNodes.length) node.appendChild(wrap);
  }
  const mo = new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n => { if (n.nodeType === 1 && !n.closest('#chub-master-root')) enhance(n); })));

  // ---------- UI ----------
  const CSS = `
#chub-master-root{position:fixed;right:12px;bottom:calc(env(safe-area-inset-bottom,0px) + 90px);z-index:2147483000;font:14px -apple-system,system-ui,sans-serif;color:#e2e8f0}
#m-fab{width:52px;height:52px;border-radius:50%;border:1px solid rgba(255,255,255,.25);background:rgba(30,27,75,.75);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);color:#fff;font-size:22px}
#m-panel{display:none;position:fixed;left:8px;right:8px;bottom:calc(env(safe-area-inset-bottom,0px) + 150px);max-height:70vh;overflow:auto;background:rgba(15,15,25,.94);border:1px solid rgba(139,92,246,.4);border-radius:14px;padding:12px;backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px)}
#m-panel.open{display:block}
#m-panel h4{margin:10px 0 6px;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:#94a3b8}
#m-panel button,#m-panel select,#m-panel input,#m-panel textarea{font:inherit;color:#e2e8f0;background:rgba(99,102,241,.18);border:1px solid #6366f1;border-radius:10px;padding:8px 10px;margin:2px 2px 2px 0;min-height:36px}
#m-panel textarea,#m-panel input[type=text],#m-panel input[type=password]{width:100%;box-sizing:border-box;background:rgba(0,0,0,.35)}
#m-panel textarea{min-height:90px}
.m-row{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.m-mod{border-left:2px solid #6366f1;padding-left:8px;margin:6px 0}
.m-toast{position:fixed;left:50%;top:calc(env(safe-area-inset-top,0px) + 12px);transform:translateX(-50%);z-index:2147483647;background:#312e81;color:#fff;padding:8px 14px;border-radius:12px;font:13px -apple-system,sans-serif}
.m-toast.err{background:#7f1d1d}
.m-hud{margin-top:10px}.m-fate{display:inline-block;background:#4c1d95;color:#e9d5ff;padding:2px 8px;border-radius:6px;font-weight:700;font-size:11px;margin:0 4px 4px 0}
.m-chips{display:flex;flex-wrap:wrap;gap:6px}.m-chip{background:rgba(99,102,241,.2);border:1px solid #6366f1;color:#c7d2fe;padding:5px 10px;border-radius:14px;font-size:12px;cursor:pointer}
.m-chip:hover{background:#6366f1;color:#fff}
.m-log{font:11px ui-monospace,monospace;white-space:pre-wrap;max-height:120px;overflow:auto;background:rgba(0,0,0,.4);padding:6px;border-radius:8px}`;
  if (typeof GM_addStyle === 'function') GM_addStyle(CSS); else { const s = document.createElement('style'); s.textContent = CSS; document.head.appendChild(s); }

  function toast(msg, err) {
    const d = document.createElement('div'); d.className = 'm-toast' + (err ? ' err' : ''); d.textContent = msg;
    document.body.appendChild(d); setTimeout(() => d.remove(), 2600);
  }
  const esc = s => String(s == null ? '' : s).replace(/[&<>\"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  let tab = 'vault';
  const root = document.createElement('div'); root.id = 'chub-master-root';
  root.innerHTML = '<button id="m-fab" aria-label="Chub Master">⚡</button><div id="m-panel"></div>';

  function render() {
    const P = $('#m-panel'); if (!P) return; const db = getDB();
    const cur = db.presets.find(p => p.id === db.sel) || db.presets[0];
    const tabs = ['vault', 'reply', 'tools', 'acti', 'settings'].map(t => `<button data-tab="${t}" ${t === tab ? 'style="background:#6366f1"' : ''}>${t}</button>`).join('');
    let h = `<div class="m-row">${tabs}</div>`;
    if (tab === 'vault') {
      h += `<h4>Preset</h4><div class="m-row"><select id="m-sel">${db.presets.map(p => `<option value="${esc(p.id)}" ${p.id === cur.id ? 'selected' : ''}>${esc(p.name)}</option>`).join('')}</select>
      <button data-a="new">New</button><button data-a="dup">Duplicate</button><button data-a="ren">Rename</button><button data-a="del">Delete</button></div>
      <h4>Modules</h4>${cur.modules.map((m, i) => `<div class="m-mod"><label><input type="checkbox" data-mod="${i}" ${m.enabled ? 'checked' : ''}> ${esc(m.label)}</label>
      <textarea data-txt="${i}">${esc(m.text)}</textarea></div>`).join('')}
      <div class="m-row"><button data-a="addmod">+ Module</button><button data-a="insert">Insert into chat</button><button data-a="replace">Replace chat text</button><button data-a="copy">Copy compiled</button><button data-a="applysamp">Apply sampler</button></div>
      <h4>Import / Export</h4><div class="m-row"><button data-a="exp1">Export selected</button><button data-a="expall">Export all</button><button data-a="expst">Export as ST preset</button><button data-a="impfile">Import file</button><button data-a="imppaste">Import paste</button></div>
      <textarea id="m-paste" placeholder="Paste JSON (vault, chub-vault, or SillyTavern preset)" style="display:none"></textarea><input type="file" id="m-file" accept=".json,application/json" style="display:none">`;
    } else if (tab === 'reply') {
      h += `<h4>{{user}} reply generator</h4><textarea id="m-mini" placeholder="Mini-prompt, e.g. agree and walk away"></textarea>
      <div class="m-row"><button data-a="genreply">Generate &amp; insert</button><button data-a="mic2">🎤 Dictate</button></div>
      <p style="color:#94a3b8;font-size:12px">Reads the visible chat, uses the selected model in Settings/Tools, and drops the result into the input box.</p>`;
    } else if (tab === 'tools') {
      h += `<h4>Prompt fixer</h4><div class="m-row"><button data-a="fix">Fix chat text</button><button data-a="fixsel">Fix selection</button></div>
      <h4>Model</h4><div class="m-row"><select id="m-model">${MODELS.map(m => `<option value="${esc(m[0])}" ${db.gen.model === m[0] ? 'selected' : ''}>${esc(m[1])}</option>`).join('')}<option value="__custom" ${MODELS.some(m => m[0] === db.gen.model) ? '' : 'selected'}>Custom (type below)</option></select></div>
      <h4>Generation settings</h4><div class="m-row">${['model', 'temperature', 'top_p', 'min_p', 'repetition_penalty', 'max_tokens'].map(k => `<label>${k}<input type="text" data-gen="${k}" value="${esc(db.gen[k])}"></label>`).join('')}</div>
      <h4>Page tools</h4><div class="m-row"><button data-a="distill">Distill page → clipboard</button><button data-a="refresh">Re-scan HUD</button></div>`;
    } else if (tab === 'acti') {
      h += `<h4>1-tap chips</h4><div class="m-row">
      <button data-a="c-later">⏰ Read later</button><button data-a="c-event">📅 Event</button><button data-a="c-copy">📋 Copy text</button><button data-a="c-speak">🗣️ Speak</button><button data-a="c-notify">🔔 Notify</button></div>
      <h4>Prompt → iOS action</h4><textarea id="m-prompt" placeholder="e.g. Remind me tomorrow 9am to continue this chat"></textarea>
      <div class="m-row"><button data-a="plan">Plan + run</button><button data-a="mic">🎤 Dictate</button></div>
      <p style="color:#94a3b8;font-size:12px">Needs Shortcut "AgentRunner" → Scriptable "AgentDispatcher".</p>`;
    } else {
      h += `<h4>Keys (stored on this device only)</h4>
      <input type="password" id="s-or" placeholder="OpenRouter key" value="${esc(store.get('orKey', ''))}">
      <input type="text" id="s-sbu" placeholder="Supabase URL" value="${esc(store.get('sbUrl', ''))}">
      <input type="password" id="s-sbk" placeholder="Supabase anon key" value="${esc(store.get('sbKey', ''))}">
      <div class="m-row"><button data-a="save">Save</button><button data-a="push">Push presets</button><button data-a="pull">Pull presets</button></div>
      <h4>Error log</h4><div class="m-log">${esc(store.get('log', []).slice(-15).map(l => l.t.slice(11, 19) + ' ' + l.level + ' ' + l.msg).join('\n') || 'empty')}</div>
      <div class="m-row"><button data-a="clog">Clear log</button><button data-a="reset">Reset defaults</button></div>`;
    }
    P.innerHTML = h;
  }

  async function act(a) {
    const db = getDB(); const cur = db.presets.find(p => p.id === db.sel) || db.presets[0]; const save = () => { setDB(db); render(); };
    const wrapExport = (presets) => JSON.stringify({ app: 'chub-master', version: 3, gen: db.gen, presets }, null, 2);
    try {
      switch (a) {
        case 'new': { const n = prompt('Preset name'); if (!n) return; const p = { id: uid(), name: n, modules: [{ id: uid(), label: 'Main', enabled: true, text: '' }] }; db.presets.push(p); db.sel = p.id; return save(); }
        case 'dup': { const p = clone(cur); p.id = uid(); p.name = cur.name + ' copy'; db.presets.push(p); db.sel = p.id; return save(); }
        case 'ren': { const n = prompt('New name', cur.name); if (!n) return; if (db.presets.some(p => p.name === n && p.id !== cur.id)) return toast('Name exists', 1); cur.name = n; return save(); }
        case 'del': { if (db.presets.length < 2) return toast('Keep one preset', 1); if (!confirm('Delete "' + cur.name + '"?')) return; db.presets = db.presets.filter(p => p.id !== cur.id); db.sel = db.presets[0].id; return save(); }
        case 'addmod': { const n = prompt('Module label'); if (!n) return; cur.modules.push({ id: uid(), label: n, enabled: true, text: '' }); return save(); }
        case 'insert': return insertText(compile(cur));
        case 'replace': return setText(composer(), compile(cur));
        case 'copy': await copyText(compile(cur)); return toast('Copied compiled prompt');
        case 'applysamp': { if (!cur.sampling) return toast('No sampler in this preset', 1); ['temperature', 'top_p', 'min_p', 'repetition_penalty', 'max_tokens'].forEach(k => { if (cur.sampling[k] != null) db.gen[k] = cur.sampling[k]; }); save(); return toast('Sampler applied'); }
        case 'exp1': return download('chub-preset-' + cur.name.replace(/\W+/g, '_') + '.json', wrapExport([cur]));
        case 'expall': return download('chub-presets-all.json', wrapExport(db.presets));
        case 'expst': return download('st-preset-' + cur.name.replace(/\W+/g, '_') + '.json', JSON.stringify(toST(cur, db.gen), null, 2));
        case 'impfile': return $('#m-file').click();
        case 'imppaste': { const t = $('#m-paste'); if (t.style.display === 'none') { t.style.display = 'block'; return; } return mergeImport(JSON.parse(t.value), 'Pasted preset'); }
        case 'genreply': { const mini = ($('#m-mini').value || '').trim(); if (!mini) return toast('Type a mini-prompt', 1); toast('Generating…'); const r = await genReply(mini); insertText(r.trim()); return toast('Reply inserted'); }
        case 'mic2': { const R = window.SpeechRecognition || window.webkitSpeechRecognition; if (!R) return toast('No speech API', 1); const r = new R(); r.onresult = e => { $('#m-mini').value += e.results[0][0].transcript; }; r.start(); return; }
        case 'fix': { const el = composer(); setText(el, fixPrompt(getText(el))); return toast('Prompt fixed'); }
        case 'fixsel': { const el = composer(); const s = el && el.selectionStart != null ? getText(el).slice(el.selectionStart, el.selectionEnd) : ''; if (!s) return toast('Select text first', 1); const v = getText(el); setText(el, v.slice(0, el.selectionStart) + fixPrompt(s) + v.slice(el.selectionEnd)); return toast('Selection fixed'); }
        case 'distill': { const t = distill(); try { await copyText(t); toast('Copied ' + t.length + ' chars'); } catch (e) { prompt('Copy:', t.slice(0, 2000)); } return; }
        case 'refresh': document.querySelectorAll('[data-m-hud]').forEach(n => n.remove()); document.querySelectorAll('div,p,article').forEach(enhance); return toast('HUD rescanned');
        case 'c-later': return dispatch([{ type: 'reminder', title: 'Read: ' + document.title.slice(0, 80), notes: location.href, dueDate: new Date(Date.now() + 3600e3).toISOString() }]);
        case 'c-event': return dispatch([{ type: 'calendar', title: document.title.slice(0, 80), notes: location.href, startDate: new Date(Date.now() + 86400e3).toISOString() }]);
        case 'c-copy': return dispatch([{ type: 'clipboard', text: selectionText() || distill(document.body, 1500) }]);
        case 'c-notify': return dispatch([{ type: 'notify', title: 'ACTI', message: document.title }]);
        case 'c-speak': { const t = selectionText() || distill(document.body, 800); speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(t)); return; }
        case 'plan': { const p = $('#m-prompt').value.trim(); if (!p) return; toast('Planning…'); return planAndRun(p + '\nPage: ' + document.title + ' ' + location.href); }
        case 'mic': { const R = window.SpeechRecognition || window.webkitSpeechRecognition; if (!R) return toast('No speech API', 1); const r = new R(); r.onresult = e => { $('#m-prompt').value += e.results[0][0].transcript; }; r.start(); return; }
        case 'save': store.set('orKey', $('#s-or').value.trim()); store.set('sbUrl', $('#s-sbu').value.trim()); store.set('sbKey', $('#s-sbk').value.trim()); return toast('Saved');
        case 'push': await pushCloud(); return toast('Pushed to Supabase');
        case 'pull': await pullCloud(); return;
        case 'clog': store.set('log', []); return render();
        case 'reset': if (confirm('Reset all presets to the built-in masters?')) { store.set('db', clone(DEFAULTS)); render(); } return;
      }
    } catch (e) { log('error', e.message); toast(e.message, 1); }
  }

  root.addEventListener('click', e => {
    const t = e.target;
    if (t.id === 'm-fab') { $('#m-panel').classList.toggle('open'); render(); return; }
    if (t.dataset.tab) { tab = t.dataset.tab; return render(); }
    if (t.dataset.a) act(t.dataset.a);
  });
  root.addEventListener('change', e => {
    const t = e.target, db = getDB(), cur = db.presets.find(p => p.id === db.sel) || db.presets[0];
    if (t.id === 'm-sel') { db.sel = t.value; setDB(db); return render(); }
    if (t.id === 'm-model') { if (t.value !== '__custom') { db.gen.model = t.value; setDB(db); render(); } return; }
    if (t.dataset.mod != null) { cur.modules[t.dataset.mod].enabled = t.checked; setDB(db); }
    if (t.dataset.txt != null) { cur.modules[t.dataset.txt].text = t.value; setDB(db); }
    if (t.dataset.gen) { const v = t.value; db.gen[t.dataset.gen] = t.dataset.gen === 'model' ? v : (parseFloat(v) || 0); setDB(db); }
    if (t.id === 'm-file' && t.files[0]) { const f = t.files[0]; const r = new FileReader(); r.onload = () => { try { mergeImport(JSON.parse(r.result), f.name); } catch (er) { toast(er.message, 1); } }; r.readAsText(f); }
  });

  function boot() {
    if (!document.body) return setTimeout(boot, 200);
    document.body.appendChild(root); mo.observe(document.body, { childList: true, subtree: true });
    checkReturn(); window.addEventListener('hashchange', checkReturn);
    log('info', 'booted ' + location.href);
  }
  boot();
})();
