from __future__ import annotations
import time
from apscheduler.schedulers.background import BackgroundScheduler
from . import db
from .publisher import publish

_sched=None

def run_due():
    for p in db.due_posts(time.time()):
        content=db.get_content(p["content_id"]) if p.get("content_id") else None
        if not content:
            db.update_post(p["id"],status="failed",response={"error":"content missing"}); continue
        meta=db.jload(content.get("metadata"),{}) or {}
        try:
            result=publish(p["platform"],content["body"],meta.get("media_url"),title=content.get("title") or "Post",file_path=content.get("media_path"),privacy=meta.get("privacy","private"))
            remote=None
            if isinstance(result,dict): remote=str(result.get("id") or result.get("uri") or result.get("publish_id") or "")
            db.update_post(p["id"],status="posted",posted_at=time.time(),remote_id=remote,response=result)
        except Exception as e:
            db.update_post(p["id"],status="failed",response={"error":str(e)})

def schedule_content(content_id: str, platform: str, when_ts: float):
    pid=db.log_post(content_id,platform,"scheduled",scheduled_for=when_ts)
    return pid

def start():
    global _sched
    if _sched: return _sched
    _sched=BackgroundScheduler(timezone=__import__("core.config",fromlist=["settings"]).settings.timezone)
    _sched.add_job(run_due,"interval",seconds=30,id="publish_due",replace_existing=True)
    _sched.start()
    return _sched
