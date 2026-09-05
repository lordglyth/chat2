from __future__ import annotations
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from core.persona import ask_as_self
from core.content import create
from core import db
from core.scheduler import start
from core.config import settings

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
    db.log_event("stripe",{"type":event["type"]})
    return {"received":True}
