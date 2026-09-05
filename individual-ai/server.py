from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from core.persona import ask_as_self
from core.content import create
from core import db
from core.scheduler import start
from core.config import settings
from core.billing import create_checkout, handle_event

app=FastAPI(title=settings.app_name)
start()

class ChatIn(BaseModel):
    message: str
class CreateIn(BaseModel):
    kind: str="social"
    idea: str
    platform: str=""
    length: str="medium"
    extra: str=""
class ScheduleIn(BaseModel):
    content_id: str
    platform: str
    when_ts: float
class SubscribeIn(BaseModel):
    email: str | None=None

@app.get("/",response_class=HTMLResponse)
def public_ai():
    title=settings.app_name.replace("<","&lt;").replace(">","&gt;")
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>body{{font-family:system-ui;max-width:760px;margin:40px auto;padding:0 18px;background:#111;color:#eee}}textarea,button,input{{font:inherit}}textarea{{width:100%;min-height:110px;padding:12px;box-sizing:border-box}}button{{padding:10px 16px;margin-top:8px;cursor:pointer}}#answer{{white-space:pre-wrap;background:#1d1d1d;padding:16px;border-radius:12px;margin-top:18px}}</style></head><body><h1>{title}</h1><p>Chat with my Individual AI.</p><textarea id="q" placeholder="Ask something…"></textarea><br><button onclick="ask()">Ask</button><div id="answer"></div><hr><p>Optional subscriber access:</p><input id="email" type="email" placeholder="email"><button onclick="subscribe()">Subscribe</button><script>async function ask(){{const q=document.getElementById('q').value;const box=document.getElementById('answer');box.textContent='Thinking…';const r=await fetch('/chat',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{message:q}})}});const j=await r.json();box.textContent=j.answer||j.detail||'No response';}}async function subscribe(){{const email=document.getElementById('email').value;const r=await fetch('/subscribe',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{email}})}});const j=await r.json();if(j.url) location.href=j.url;else alert(j.detail||'Stripe is not configured');}}</script></body></html>'''

@app.get("/health")
def health(): return {"ok":True,"app":settings.app_name,"dry_run":settings.dry_run}

@app.post("/chat")
def chat(req: ChatIn): return {"answer":ask_as_self(req.message)}

@app.post("/create")
def create_content(req: CreateIn):
    cid,body=create(req.kind,req.idea,req.platform,req.length,req.extra)
    return {"id":cid,"body":body}

@app.get("/content")
def content(): return db.list_content()

@app.post("/schedule")
def schedule(req: ScheduleIn):
    from core.scheduler import schedule_content
    return {"post_id":schedule_content(req.content_id,req.platform,req.when_ts)}

@app.post("/subscribe")
def subscribe(req: SubscribeIn):
    try: return create_checkout(req.email)
    except Exception as e: raise HTTPException(503,str(e))

@app.get("/export")
def export(): return db.export_all()

@app.delete("/me")
def delete_me():
    db.delete_all()
    return {"deleted":True}

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    if not settings.stripe_webhook_secret: raise HTTPException(503,"Stripe not configured")
    import stripe
    payload=await request.body()
    sig=request.headers.get("stripe-signature","")
    try: event=stripe.Webhook.construct_event(payload,sig,settings.stripe_webhook_secret)
    except Exception as e: raise HTTPException(400,str(e))
    handle_event(event)
    return {"received":True}
