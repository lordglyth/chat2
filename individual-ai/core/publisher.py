from __future__ import annotations
import time, uuid
from pathlib import Path
import requests
from .config import settings
from . import db

class PublishError(RuntimeError): pass

def _dry(platform, payload):
    if settings.dry_run:
        return {"dry_run":True,"platform":platform,"payload":payload}
    return None

def facebook(text: str, media_url: str | None=None):
    if d:=_dry("facebook",{"text":text,"media_url":media_url}): return d
    if not settings.facebook_page_id or not settings.meta_access_token: raise PublishError("Facebook credentials missing")
    base=f"https://graph.facebook.com/{settings.meta_api_version}/{settings.facebook_page_id}"
    if media_url:
        r=requests.post(base+"/photos",data={"url":media_url,"caption":text,"access_token":settings.meta_access_token},timeout=60)
    else:
        r=requests.post(base+"/feed",data={"message":text,"access_token":settings.meta_access_token},timeout=60)
    r.raise_for_status(); return r.json()

def instagram(text: str, media_url: str):
    if d:=_dry("instagram",{"text":text,"media_url":media_url}): return d
    if not settings.instagram_user_id or not settings.meta_access_token: raise PublishError("Instagram credentials missing")
    base=f"https://graph.facebook.com/{settings.meta_api_version}/{settings.instagram_user_id}"
    c=requests.post(base+"/media",data={"image_url":media_url,"caption":text,"access_token":settings.meta_access_token},timeout=60)
    c.raise_for_status(); cid=c.json()["id"]
    p=requests.post(base+"/media_publish",data={"creation_id":cid,"access_token":settings.meta_access_token},timeout=60)
    p.raise_for_status(); return p.json()

def linkedin(text: str, media_url: str | None=None):
    payload={"author":settings.linkedin_author_urn,"commentary":text,"visibility":"PUBLIC","distribution":{"feedDistribution":"MAIN_FEED","targetEntities":[],"thirdPartyDistributionChannels":[]},"lifecycleState":"PUBLISHED","isReshareDisabledByAuthor":False}
    if d:=_dry("linkedin",payload): return d
    if not settings.linkedin_access_token or not settings.linkedin_author_urn: raise PublishError("LinkedIn credentials missing")
    headers={"Authorization":f"Bearer {settings.linkedin_access_token}","Content-Type":"application/json","X-Restli-Protocol-Version":"2.0.0","Linkedin-Version":settings.linkedin_version}
    r=requests.post("https://api.linkedin.com/rest/posts",headers=headers,json=payload,timeout=60)
    if r.status_code>=400: raise PublishError(f"LinkedIn {r.status_code}: {r.text[:500]}")
    return {"id":r.headers.get("x-restli-id"),"status":r.status_code}

def mastodon(text: str, media_url: str | None=None):
    payload={"status":text}
    if d:=_dry("mastodon",payload): return d
    if not settings.mastodon_base_url or not settings.mastodon_access_token: raise PublishError("Mastodon credentials missing")
    r=requests.post(settings.mastodon_base_url.rstrip("/")+"/api/v1/statuses",headers={"Authorization":f"Bearer {settings.mastodon_access_token}","Idempotency-Key":str(uuid.uuid4())},data=payload,timeout=60)
    r.raise_for_status(); return r.json()

def bluesky(text: str, media_url: str | None=None):
    if d:=_dry("bluesky",{"text":text}): return d
    if not settings.bluesky_handle or not settings.bluesky_app_password: raise PublishError("Bluesky credentials missing")
    sess=requests.post("https://bsky.social/xrpc/com.atproto.server.createSession",json={"identifier":settings.bluesky_handle,"password":settings.bluesky_app_password},timeout=30)
    sess.raise_for_status(); s=sess.json()
    record={"$type":"app.bsky.feed.post","text":text,"createdAt":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat().replace("+00:00","Z")}
    r=requests.post("https://bsky.social/xrpc/com.atproto.repo.createRecord",headers={"Authorization":f"Bearer {s['accessJwt']}"},json={"repo":s["did"],"collection":"app.bsky.feed.post","record":record},timeout=30)
    r.raise_for_status(); return r.json()

def tiktok(text: str, media_url: str):
    payload={"post_info":{"title":text[:2200],"privacy_level":"SELF_ONLY","disable_duet":False,"disable_comment":False,"disable_stitch":False},"source_info":{"source":"PULL_FROM_URL","video_url":media_url}}
    if d:=_dry("tiktok",payload): return d
    if not settings.tiktok_access_token: raise PublishError("TikTok access token missing")
    h={"Authorization":f"Bearer {settings.tiktok_access_token}","Content-Type":"application/json; charset=UTF-8"}
    creator=requests.post("https://open.tiktokapis.com/v2/post/publish/creator_info/query/",headers=h,json={},timeout=30)
    creator.raise_for_status()
    opts=creator.json().get("data",{}).get("privacy_level_options",[])
    if "PUBLIC_TO_EVERYONE" in opts: payload["post_info"]["privacy_level"]="PUBLIC_TO_EVERYONE"
    r=requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/",headers=h,json=payload,timeout=60)
    r.raise_for_status(); return r.json()

def youtube(title: str, description: str, file_path: str, privacy="private"):
    if d:=_dry("youtube",{"title":title,"description":description,"file":file_path,"privacy":privacy}): return d
    if not settings.youtube_client_secret_file: raise PublishError("YOUTUBE_CLIENT_SECRET_FILE missing")
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
    token=Path(settings.youtube_token_file); creds=None
    if token.exists(): creds=Credentials.from_authorized_user_file(str(token),scopes)
    if creds and creds.expired and creds.refresh_token: creds.refresh(Request())
    if not creds or not creds.valid:
        flow=InstalledAppFlow.from_client_secrets_file(settings.youtube_client_secret_file,scopes)
        creds=flow.run_local_server(port=0)
        token.parent.mkdir(parents=True,exist_ok=True); token.write_text(creds.to_json())
    service=build("youtube","v3",credentials=creds)
    req=service.videos().insert(part="snippet,status",body={"snippet":{"title":title[:100],"description":description},"status":{"privacyStatus":privacy}},media_body=MediaFileUpload(file_path,resumable=True))
    return req.execute()

PUBLISHERS={"facebook":facebook,"instagram":instagram,"linkedin":linkedin,"mastodon":mastodon,"bluesky":bluesky,"tiktok":tiktok}

def publish(platform: str, text: str, media_url: str | None=None, **kwargs):
    platform=platform.lower()
    if platform=="youtube":
        return youtube(kwargs.get("title","Video"),text,kwargs["file_path"],kwargs.get("privacy","private"))
    if platform not in PUBLISHERS: raise PublishError(f"Unsupported platform: {platform}")
    if platform in ("instagram","tiktok") and not media_url: raise PublishError(f"{platform} requires media_url")
    result=PUBLISHERS[platform](text,media_url)
    db.log_event("published",{"platform":platform,"dry_run":bool(result.get("dry_run")) if isinstance(result,dict) else False})
    return result
