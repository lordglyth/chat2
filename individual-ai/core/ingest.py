from __future__ import annotations
from pathlib import Path
from io import BytesIO
import re, requests, trafilatura
from bs4 import BeautifulSoup
from pypdf import PdfReader
from docx import Document
from . import db
from .llm import generate

def clean(text: str) -> str:
    return re.sub(r"\n{3,}","\n\n",text or "").strip()

def ingest_text(text: str, source="manual", title=""):
    text=clean(text)
    if text: return db.add_memory(source,text,title)
    return None

def ingest_file(name: str, data: bytes):
    ext=Path(name).suffix.lower()
    text=""
    if ext in (".txt",".md",".csv",".json",".srt"):
        text=data.decode("utf-8",errors="ignore")
    elif ext==".pdf":
        reader=PdfReader(BytesIO(data))
        text="\n\n".join((p.extract_text() or "") for p in reader.pages)
    elif ext==".docx":
        doc=Document(BytesIO(data)); text="\n".join(p.text for p in doc.paragraphs)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    return ingest_text(text,"file",name)

def ingest_url(url: str):
    r=requests.get(url,timeout=30,headers={"User-Agent":"SojiIndividualAI/1.0"})
    r.raise_for_status()
    text=trafilatura.extract(r.text,include_links=False,include_comments=False) or BeautifulSoup(r.text,"html.parser").get_text("\n")
    return ingest_text(text,"website",url)

def ingest_social_export(platform: str, text: str):
    return ingest_text(text,f"social:{platform}",f"{platform} export")

def capture_voice_transcript(transcript: str):
    mid=ingest_text(transcript,"voice","Voice capture")
    style=generate(f"""Extract writing/speaking style from this transcript. Return a compact practical style guide: sentence rhythm, vocabulary, humor, directness, emotional markers, formatting habits, and things to avoid. Do not infer biography.\n\n{transcript[:18000]}""",temperature=0.2)
    db.set_pref("voice_style",style)
    return mid,style
