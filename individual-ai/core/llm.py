from __future__ import annotations
import math, requests
from .config import settings

def _post(path: str, payload: dict, timeout=180):
    r=requests.post(settings.ollama_url.rstrip("/") + path, json=payload, timeout=timeout)
    r.raise_for_status()
    return r.json()

def chat(messages: list[dict], model: str | None=None, temperature: float=0.7, json_mode: bool=False) -> str:
    payload={"model":model or settings.ollama_model,"messages":messages,"stream":False,"options":{"temperature":temperature}}
    if json_mode: payload["format"]="json"
    data=_post("/api/chat",payload)
    return data["message"]["content"]

def generate(prompt: str, system: str="", **kw) -> str:
    msgs=[]
    if system: msgs.append({"role":"system","content":system})
    msgs.append({"role":"user","content":prompt})
    return chat(msgs,**kw)

def embed(text: str) -> list[float]:
    try:
        data=_post("/api/embed",{"model":settings.embed_model,"input":text},timeout=120)
        e=data.get("embeddings") or []
        return e[0] if e else []
    except Exception:
        vec=[0.0]*256
        for tok in text.lower().split():
            vec[hash(tok)%256]+=1.0
        n=math.sqrt(sum(x*x for x in vec)) or 1.0
        return [x/n for x in vec]

def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b: return 0.0
    n=min(len(a),len(b))
    dot=sum(a[i]*b[i] for i in range(n))
    na=math.sqrt(sum(a[i]*a[i] for i in range(n))) or 1.0
    nb=math.sqrt(sum(b[i]*b[i] for i in range(n))) or 1.0
    return dot/(na*nb)
