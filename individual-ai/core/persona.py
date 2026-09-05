from __future__ import annotations
import json
from . import db
from .llm import generate, embed, cosine

DIMENSIONS=["identity","world","story","mindset","drive","pattern","growth"]

def retrieve(query: str, k: int=8):
    q=embed(query)
    scored=[]
    for m in db.list_memories(500):
        v=embed((m.get("title") or "")+"\n"+m["text"])
        scored.append((cosine(q,v),m))
    return [m for _,m in sorted(scored,key=lambda x:x[0],reverse=True)[:k]]

def rebuild_hlm():
    memories=db.list_memories(300)
    if not memories: return {}
    corpus="\n\n".join(f"[{m['source']}] {m.get('title','')}\n{m['text'][:3500]}" for m in memories)[:60000]
    prompt=f"""Analyze this person's own material. Build a seven-dimension personal model.
Return strict JSON with keys {DIMENSIONS}. Each value must have "summary" and "evidence" (short list).
Do not invent facts not supported by the material.

MATERIAL:
{corpus}"""
    raw=generate(prompt,system="You are a careful personal-knowledge modeler. Separate observations from speculation.",temperature=0.2,json_mode=True)
    data=json.loads(raw)
    for d in DIMENSIONS:
        v=data.get(d,{})
        db.upsert_hlm(d,str(v.get("summary","")),list(v.get("evidence",[]))[:12])
    db.log_event("hlm_rebuilt",{"dimensions":list(data)})
    return db.get_hlm()

def system_prompt(extra: str=""):
    hlm=db.get_hlm(); prefs=db.get_prefs()
    dimensions="\n".join(f"- {k}: {v['summary']}" for k,v in hlm.items())
    return f"""You are the owner's local Individual AI. Your job is to reason and write in the owner's learned voice without pretending to possess memories that are not in the supplied context.
PERSON MODEL:
{dimensions or '(not trained yet)'}

PREFERENCES:
{json.dumps(prefs,ensure_ascii=False)}

Rules:
- Preserve the owner's tone, vocabulary, values, and recurring preferences when evidence supports them.
- Never fabricate personal history.
- When asked to create content, produce publication-ready copy.
- Distinguish the owner's views from uncertain inference.
{extra}"""

def ask_as_self(question: str, history: list[dict] | None=None):
    ctx=retrieve(question,8)
    context="\n\n".join(f"[{m['source']}] {m['text']}" for m in ctx)
    msgs=[{"role":"system","content":system_prompt()+f"\n\nRELEVANT OWNER MATERIAL:\n{context}"}]
    msgs.extend((history or [])[-12:])
    msgs.append({"role":"user","content":question})
    from .llm import chat
    answer=chat(msgs,temperature=0.55)
    db.log_event("chat",{"question":question[:500]})
    return answer
