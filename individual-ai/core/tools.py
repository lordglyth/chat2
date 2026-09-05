from __future__ import annotations
import requests
from .config import settings
from . import db

def call_webhook(action: str, payload: dict):
    if not settings.automation_webhook_url:
        raise RuntimeError("AUTOMATION_WEBHOOK_URL is not configured")
    r=requests.post(settings.automation_webhook_url,json={"action":action,"payload":payload},timeout=60)
    r.raise_for_status()
    db.log_event("automation_webhook",{"action":action})
    try: return r.json()
    except Exception: return {"text":r.text}

def tool_manifest():
    return {"social":["facebook","instagram","linkedin","mastodon","bluesky","tiktok","youtube"],"content":["social","article","newsletter","script","image_prompt","video_prompt","reply","document"],"local_ai":["ollama","ollama_embeddings"],"media":["automatic1111/stability-matrix compatible API","comfyui workflow API"],"automation":["generic webhook bridge"],"data":["documents","websites","voice transcripts","social exports"]}
