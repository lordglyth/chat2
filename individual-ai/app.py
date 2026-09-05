from __future__ import annotations
import json
from datetime import datetime
import streamlit as st
from core.config import settings
from core import db
from core.ingest import ingest_file, ingest_text, ingest_url, ingest_social_export, capture_voice_transcript
from core.audio import transcribe_audio
from core.social_import import connection_status, import_recent
from core.persona import ask_as_self, rebuild_hlm
from core.content import create
from core.media import generate_image, queue_comfy_video
from core.publisher import publish
from core.scheduler import schedule_content, start
from core.tools import tool_manifest

st.set_page_config(page_title=settings.app_name,page_icon="🧬",layout="wide")
start()
st.title("🧬 "+settings.app_name)
st.caption("Local-first personal AI • capture → model → create → publish")

with st.sidebar:
    page=st.radio("Workspace",["Dashboard","Connections","Capture","Human Life Model","Chat as Me","Create","Publish","Skills & Services","Data & Privacy"])
    st.write("**Mode:**", "DRY RUN" if settings.dry_run else "LIVE POSTING")
    st.json(tool_manifest(),expanded=False)

if page=="Dashboard":
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Memories",len(db.list_memories(10000)))
    c2.metric("Content",len(db.list_content(10000)))
    with db.connect() as con:
        c3.metric("Posts",con.execute("SELECT COUNT(*) FROM posts").fetchone()[0])
        c4.metric("Events",con.execute("SELECT COUNT(*) FROM analytics").fetchone()[0])
    st.subheader("Recent content")
    for item in db.list_content(10):
        st.markdown(f"**{item['kind']} — {item.get('title') or 'Untitled'}**")
        st.code(item["body"][:1200])

elif page=="Connections":
    st.subheader("Social connections")
    st.caption("Credentials stay in your local .env. Nothing here asks for your normal account password.")
    status=connection_status()
    for name,info in status.items():
        left,right=st.columns([3,2])
        left.write(("✅ " if info["configured"] else "⚪ ")+name.title())
        if name in ("facebook","instagram","mastodon","bluesky","tiktok"):
            if right.button(f"Import recent {name} posts",key=f"import-{name}",disabled=not info["configured"]):
                try:
                    with st.spinner(f"Importing {name}…"):
                        result=import_recent(name)
                    st.success(f"Captured {result['count']} recent {name} posts into your personal model.")
                except Exception as e:
                    st.error(str(e))
    st.info("Facebook/Instagram, LinkedIn, TikTok and YouTube require developer-app authorization from those platforms. Fill the matching values in .env.example → .env, then restart the app.")
    if st.button("Rebuild Human Life Model from imported social material"):
        with st.spinner("Modeling your voice and patterns…"):
            rebuild_hlm()
        st.success("Personal model rebuilt.")

elif page=="Capture":
    st.subheader("Upload documents")
    ups=st.file_uploader("TXT, MD, CSV, JSON, SRT, PDF, DOCX",accept_multiple_files=True,type=["txt","md","csv","json","srt","pdf","docx"])
    if st.button("Ingest uploaded files",disabled=not ups):
        for f in ups:
            ingest_file(f.name,f.read())
        st.success(f"Ingested {len(ups)} file(s).")

    st.subheader("Website")
    url=st.text_input("Public webpage URL")
    if st.button("Ingest website",disabled=not url):
        ingest_url(url)
        st.success("Website captured.")

    st.subheader("Social history / export")
    platform=st.selectbox("Platform",["Facebook","Instagram","LinkedIn","TikTok","YouTube","Bluesky","Mastodon","Other"])
    social=st.text_area("Paste your exported posts, captions, transcript, or profile archive text",height=180)
    if st.button("Ingest social material",disabled=not social):
        ingest_social_export(platform,social)
        st.success("Social material captured.")

    st.subheader("Voice capture")
    recording=st.audio_input("Record a voice sample",sample_rate=16000)
    voice_model=st.selectbox("Local Whisper model",["tiny","base","small","medium","large-v3"],index=2)
    if st.button("Transcribe recording + learn my voice",disabled=recording is None):
        try:
            with st.spinner("Transcribing locally and learning your speech style…"):
                result=transcribe_audio("voice.wav",recording.getvalue(),voice_model)
            st.text_area("Transcript",result["transcript"],height=160)
            st.code(result["style"])
            st.success("Voice sample captured.")
        except Exception as e:
            st.error(str(e))

    transcript=st.text_area("Or paste a voice memo transcript",height=160)
    if st.button("Learn from pasted transcript",disabled=not transcript):
        _,style=capture_voice_transcript(transcript)
        st.success("Voice style learned.")
        st.code(style)

    st.subheader("Anything else")
    text=st.text_area("Memory, story, preference, background, knowledge",height=160,key="manual")
    if st.button("Capture text",disabled=not text):
        ingest_text(text,"manual","Manual capture")
        st.success("Captured.")

elif page=="Human Life Model":
    st.caption("Seven dimensions: Identity • World • Story • Mindset • Drive • Pattern • Growth")
    if st.button("Rebuild model from my captured material"):
        with st.spinner("Modeling…"):
            rebuild_hlm()
    hlm=db.get_hlm()
    for d in ["identity","world","story","mindset","drive","pattern","growth"]:
        with st.expander(d.title(),expanded=True):
            v=hlm.get(d,{})
            st.write(v.get("summary","Not modeled yet."))
            if v.get("evidence"):
                st.caption("Evidence: "+" • ".join(v["evidence"]))

elif page=="Chat as Me":
    if "chat" not in st.session_state:
        st.session_state.chat=[]
    for m in st.session_state.chat:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    q=st.chat_input("Ask your Individual AI…")
    if q:
        st.session_state.chat.append({"role":"user","content":q})
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            a=ask_as_self(q,st.session_state.chat[:-1])
            st.markdown(a)
        st.session_state.chat.append({"role":"assistant","content":a})

elif page=="Create":
    kind=st.selectbox("Create",["social","article","newsletter","script","image_prompt","video_prompt","reply","document"])
    idea=st.text_area("Idea / goal",height=120)
    platform=st.selectbox("Target",["","Facebook","Instagram","LinkedIn","TikTok","YouTube","Bluesky","Mastodon","Blog"])
    length=st.select_slider("Length",["short","medium","long"],value="medium")
    extra=st.text_area("Extra instructions")
    if st.button("Generate",disabled=not idea):
        with st.spinner("Creating in your learned voice…"):
            cid,body=create(kind,idea,platform,length,extra)
        st.session_state["last_content_id"]=cid
        st.session_state["last_body"]=body
    if st.session_state.get("last_body"):
        st.text_area("Result",st.session_state["last_body"],height=380)

    st.divider()
    st.subheader("Generate media locally")
    mp=st.text_area("Image/video prompt",key="media_prompt")
    c1,c2=st.columns(2)
    if c1.button("Generate image with local A1111 / Stability Matrix",disabled=not mp):
        try:
            p=generate_image(mp)
            st.success(p)
            st.image(p)
        except Exception as e:
            st.error(str(e))
    if c2.button("Queue ComfyUI video workflow",disabled=not mp):
        try:
            st.json(queue_comfy_video(mp))
        except Exception as e:
            st.error(str(e))

elif page=="Publish":
    items=db.list_content(100)
    options={f"{x['kind']} | {x.get('title') or x['id'][:8]}":x for x in items}
    if not options:
        st.info("Create some content first.")
    else:
        label=st.selectbox("Content",list(options))
        item=options[label]
        text=st.text_area("Post text",item["body"],height=260)
        platform=st.selectbox("Platform",["facebook","instagram","linkedin","mastodon","bluesky","tiktok","youtube"])
        media_url=st.text_input("Public media URL (required for Instagram/TikTok pull-from-URL)")
        media_path=st.text_input("Local video path (YouTube)")
        yt_privacy=st.selectbox("YouTube privacy",["private","unlisted","public"],index=0)
        st.caption("DRY_RUN=true prevents network posting. Set it false in your local .env when credentials are ready.")
        c1,c2=st.columns(2)
        if c1.button("Post now"):
            try:
                result=publish(platform,text,media_url or None,title=item.get("title") or "Video",file_path=media_path,privacy=yt_privacy)
                db.log_post(item["id"],platform,"posted",posted_at=db.now(),remote_id=str(result.get("id") or result.get("uri") or result.get("publish_id") or "") if isinstance(result,dict) else None,response=result if isinstance(result,dict) else {"result":str(result)})
                st.json(result)
            except Exception as e:
                st.error(str(e))
        when=st.datetime_input("Schedule for",value=datetime.now())
        if c2.button("Schedule"):
            meta=db.jload(item.get("metadata"),{}) or {}
            if media_url:
                meta["media_url"]=media_url
            if media_path:
                with db.connect() as con:
                    con.execute("UPDATE content SET media_path=? WHERE id=?",(media_path,item["id"]))
            meta["privacy"]=yt_privacy
            with db.connect() as con:
                con.execute("UPDATE content SET metadata=? WHERE id=?",(db.jdump(meta),item["id"]))
            pid=schedule_content(item["id"],platform,when.timestamp())
            st.success(f"Scheduled: {pid}")

elif page=="Skills & Services":
    st.subheader("Preferences")
    prefs=db.get_prefs()
    raw=st.text_area("Preference JSON",json.dumps(prefs,indent=2,ensure_ascii=False),height=220)
    if st.button("Save preferences"):
        try:
            for k,v in json.loads(raw).items():
                db.set_pref(k,v)
            st.success("Saved.")
        except Exception as e:
            st.error(str(e))

    st.subheader("Skills")
    with db.connect() as con:
        skills=[dict(r) for r in con.execute("SELECT * FROM skills").fetchall()]
    st.dataframe(skills,use_container_width=True)
    name=st.text_input("Skill name")
    instructions=st.text_area("Skill instructions")
    if st.button("Add skill",disabled=not name or not instructions):
        with db.connect() as con:
            con.execute("INSERT INTO skills VALUES(?,?,?,1)",(db.uid(),name,instructions))
        st.success("Skill added.")

    st.subheader("Services")
    sname=st.text_input("Service name")
    desc=st.text_area("Service description")
    price=st.number_input("Price in dollars",0.0,10000.0,0.0,1.0)
    if st.button("Add service",disabled=not sname):
        with db.connect() as con:
            con.execute("INSERT INTO services VALUES(?,?,?,?,?,1)",(db.uid(),sname,desc,int(price*100),"[]"))
        st.success("Service added.")

elif page=="Data & Privacy":
    st.write("Your local database:",settings.db_path)
    data=db.export_all()
    st.download_button("Export everything",json.dumps(data,indent=2,ensure_ascii=False),file_name="individual-ai-export.json",mime="application/json")
    st.warning("Delete everything removes local model data, drafts, post logs, skills, services, and subscriber records from this database.")
    confirm=st.text_input("Type DELETE EVERYTHING")
    if st.button("Delete everything",type="primary",disabled=confirm!="DELETE EVERYTHING"):
        db.delete_all()
        st.success("Local database cleared.")
