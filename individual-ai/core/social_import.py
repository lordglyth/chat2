from __future__ import annotations
import requests
from .config import settings
from .ingest import ingest_social_export

class SocialImportError(RuntimeError): pass

def _join(items, platform):
    chunks=[]
    for x in items:
        text=(x.get("message") or x.get("caption") or x.get("text") or x.get("record",{}).get("text") or x.get("video_description") or x.get("title") or "").strip()
        if text:
            stamp=x.get("created_time") or x.get("timestamp") or x.get("create_time") or x.get("indexedAt") or ""
            chunks.append(f"[{stamp}] {text}")
    if not chunks: raise SocialImportError(f"No text posts were returned from {platform}.")
    text="\n\n".join(chunks)
    ingest_social_export(platform,text)
    return {"platform":platform,"count":len(chunks),"characters":len(text)}

def facebook(limit=50):
    if not settings.facebook_page_id or not settings.meta_access_token: raise SocialImportError("Facebook credentials missing")
    url=f"https://graph.facebook.com/{settings.meta_api_version}/{settings.facebook_page_id}/feed"
    r=requests.get(url,params={"fields":"message,created_time,permalink_url","limit":limit,"access_token":settings.meta_access_token},timeout=60)
    r.raise_for_status(); return _join(r.json().get("data",[]),"Facebook")

def instagram(limit=50):
    if not settings.instagram_user_id or not settings.meta_access_token: raise SocialImportError("Instagram credentials missing")
    url=f"https://graph.facebook.com/{settings.meta_api_version}/{settings.instagram_user_id}/media"
    r=requests.get(url,params={"fields":"caption,media_type,timestamp,permalink","limit":limit,"access_token":settings.meta_access_token},timeout=60)
    r.raise_for_status(); return _join(r.json().get("data",[]),"Instagram")

def mastodon(limit=40):
    if not settings.mastodon_base_url or not settings.mastodon_access_token: raise SocialImportError("Mastodon credentials missing")
    h={"Authorization":f"Bearer {settings.mastodon_access_token}"}
    me=requests.get(settings.mastodon_base_url.rstrip("/")+"/api/v1/accounts/verify_credentials",headers=h,timeout=30)
    me.raise_for_status(); aid=me.json()["id"]
    r=requests.get(settings.mastodon_base_url.rstrip("/")+f"/api/v1/accounts/{aid}/statuses",headers=h,params={"limit":limit,"exclude_reblogs":True},timeout=60)
    r.raise_for_status()
    items=[]
    from bs4 import BeautifulSoup
    for x in r.json():
        items.append({"text":BeautifulSoup(x.get("content",''),"html.parser").get_text(" "),"created_time":x.get("created_at")})
    return _join(items,"Mastodon")

def bluesky(limit=50):
    if not settings.bluesky_handle: raise SocialImportError("BLUESKY_HANDLE missing")
    r=requests.get("https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed",params={"actor":settings.bluesky_handle,"limit":min(limit,100),"filter":"posts_no_replies"},timeout=60)
    r.raise_for_status()
    items=[]
    for entry in r.json().get("feed",[]):
        post=entry.get("post",{}); rec=post.get("record",{})
        items.append({"record":{"text":rec.get("text","")},"indexedAt":post.get("indexedAt")})
    return _join(items,"Bluesky")

def tiktok(limit=20):
    if not settings.tiktok_access_token: raise SocialImportError("TikTok access token missing")
    h={"Authorization":f"Bearer {settings.tiktok_access_token}","Content-Type":"application/json"}
    r=requests.post("https://open.tiktokapis.com/v2/video/list/?fields=id,title,video_description,create_time,share_url",headers=h,json={"max_count":min(limit,20)},timeout=60)
    r.raise_for_status(); return _join(r.json().get("data",{}).get("videos",[]),"TikTok")

def connection_status():
    return {
      "facebook":{"configured":bool(settings.facebook_page_id and settings.meta_access_token)},
      "instagram":{"configured":bool(settings.instagram_user_id and settings.meta_access_token)},
      "linkedin":{"configured":bool(settings.linkedin_author_urn and settings.linkedin_access_token)},
      "mastodon":{"configured":bool(settings.mastodon_base_url and settings.mastodon_access_token)},
      "bluesky":{"configured":bool(settings.bluesky_handle and settings.bluesky_app_password)},
      "tiktok":{"configured":bool(settings.tiktok_access_token)},
      "youtube":{"configured":bool(settings.youtube_client_secret_file)},
    }

IMPORTERS={"facebook":facebook,"instagram":instagram,"mastodon":mastodon,"bluesky":bluesky,"tiktok":tiktok}

def import_recent(platform: str, limit=50):
    key=platform.lower()
    if key not in IMPORTERS: raise SocialImportError(f"Automatic import is not implemented for {platform}; use the social export capture box instead.")
    return IMPORTERS[key](limit)
