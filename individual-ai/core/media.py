from __future__ import annotations
import base64, json, time
from pathlib import Path
import requests
from .config import settings
from . import db

def generate_image(prompt: str, negative: str="", width=1024, height=1024, steps=28):
    payload={"prompt":prompt,"negative_prompt":negative,"width":width,"height":height,"steps":steps}
    r=requests.post(settings.a1111_url.rstrip("/")+"/sdapi/v1/txt2img",json=payload,timeout=300)
    r.raise_for_status()
    img=base64.b64decode(r.json()["images"][0])
    path=Path("data/generated")/f"image-{int(time.time())}.png"
    path.write_bytes(img)
    db.log_event("image_generated",{"path":str(path)})
    return str(path)

def queue_comfy_video(prompt: str):
    if not settings.comfyui_video_workflow:
        raise RuntimeError("Set COMFYUI_VIDEO_WORKFLOW to a JSON workflow file exported for API use.")
    wf=json.loads(Path(settings.comfyui_video_workflow).read_text(encoding="utf-8"))
    def repl(v):
        if isinstance(v,dict): return {k:repl(x) for k,x in v.items()}
        if isinstance(v,list): return [repl(x) for x in v]
        if isinstance(v,str): return v.replace("{{PROMPT}}",prompt)
        return v
    wf=repl(wf)
    r=requests.post(settings.comfyui_url.rstrip("/")+"/prompt",json={"prompt":wf},timeout=60)
    r.raise_for_status()
    data=r.json()
    db.log_event("video_queued",data)
    return data
