from __future__ import annotations
from .persona import system_prompt, retrieve
from .llm import generate
from . import db

FORMATS={
"social":"a platform-ready social post with a strong opening, natural body, optional hashtags only when useful",
"article":"a complete article with a title and readable sections",
"newsletter":"a newsletter with subject line, opening, body, and CTA",
"script":"a spoken video/audio script with beats and delivery notes",
"image_prompt":"a detailed image-generation prompt with composition, subject, lighting, lens/style cues, and negatives",
"video_prompt":"a shot-by-shot video-generation prompt including motion, camera, duration cues, and continuity",
"reply":"a concise authentic reply in the owner's voice",
"document":"a polished document suited to the requested purpose",
}

def create(kind: str, idea: str, platform: str="", length: str="medium", extra: str=""):
    spec=FORMATS.get(kind,FORMATS["social"])
    context=retrieve(idea,8)
    evidence="\n".join(m["text"][:1800] for m in context)
    prompt=f"""Create {spec}.
IDEA/GOAL: {idea}
TARGET PLATFORM: {platform or 'general'}
LENGTH: {length}
EXTRA INSTRUCTIONS: {extra}
RELEVANT OWNER MATERIAL:
{evidence}

Keep personal claims grounded in the supplied material. Return only the finished content."""
    body=generate(prompt,system=system_prompt("Write as the owner, not as a generic assistant."),temperature=0.75)
    cid=db.save_content(kind,body,title=idea[:120],metadata={"platform":platform,"length":length,"extra":extra})
    db.log_event("content_created",{"id":cid,"kind":kind,"platform":platform})
    return cid,body
