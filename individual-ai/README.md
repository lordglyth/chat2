# Soji Individual AI

A local-first, auditable **feature-equivalent personal-AI workspace** inspired by the public capabilities of Uare.ai, without copying Uare.ai code, branding, proprietary models, or private APIs.

It is built to live in your GitHub, run on your computer, use **Ollama** for the personal AI, and post through each social network's official API when you provide your own developer credentials.

## What it covers

### Capture
- Upload TXT, Markdown, CSV, JSON, SRT, PDF and DOCX.
- Capture website text.
- Paste/import social history.
- Capture voice-memo transcripts and learn a practical speaking/writing style guide.
- Store memories locally in SQLite.

### Model you
- Seven-dimension personal model: **Identity, World, Story, Mindset, Drive, Pattern, Growth**.
- Retrieval over your own material.
- Ollama chat that answers and creates with your own captured context.
- Explicit preferences.
- Skills and service definitions.
- No fake personal memories: the prompt tells the model to stay grounded in captured material.

### Create
- Social posts, articles, newsletters, scripts, replies and documents.
- Image prompts and video prompts.
- Local image generation using an AUTOMATIC1111-compatible endpoint (works with many Stability Matrix installs).
- ComfyUI video workflow queueing; provide an API-format workflow JSON containing `{{PROMPT}}`.

### Share / post
Implemented publisher adapters for:
- Facebook Pages.
- Instagram image publishing.
- LinkedIn posts.
- Mastodon.
- Bluesky.
- TikTok video Direct Post via pull-from-URL.
- YouTube video uploads.
- Scheduled publishing using APScheduler.
- Generic automation webhook for anything else you want to bridge through n8n, Make, Zapier, a local script, or your own service.

`DRY_RUN=true` is the default, so the dashboard can be tested without accidentally posting. Set it to `false` locally when credentials are ready.

### Public AI / API
`server.py` exposes chat, creation, content listing, scheduling, export, delete-my-data and Stripe webhook endpoints. That gives you a backend for a public "chat with my AI" page, mobile client, bot, or other frontend.

### Monetization foundation
- Subscriber table.
- Service definitions and prices.
- Stripe webhook endpoint and config.
- Public API surface for a subscriber-facing frontend.

### Ownership / privacy
- Local SQLite database.
- Local Ollama by default.
- `.env` is gitignored.
- Export everything.
- Delete everything.
- No telemetry code in this project.

## What "connect my socials" actually requires

Social networks require developer apps and authorization through official OAuth/API flows. Some require review before public auto-posting works. This project does not scrape passwords, store browser cookies, or bypass platform controls.

## Install

```powershell
cd individual-ai
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
ollama pull huihui_ai/devstral-small-2-24b-instruct
ollama pull nomic-embed-text
streamlit run app.py
```

Run the API in a second terminal:

```powershell
uvicorn server:app --host 127.0.0.1 --port 8787 --reload
```

## Connect social accounts

Edit **your local `.env` only**. Never commit access tokens. Fill in the corresponding Meta, LinkedIn, Mastodon, Bluesky, TikTok and/or YouTube values from `.env.example`.

## Local image/video generation

For Stability Matrix/A1111, start a WebUI with API enabled and point `A1111_URL` at it. For ComfyUI, export an API workflow, put `{{PROMPT}}` where the generated prompt belongs, and set `COMFYUI_VIDEO_WORKFLOW` to that JSON file.

## Going live

1. Capture your documents/posts/transcripts and rebuild the Human Life Model.
2. Generate drafts and check the learned voice.
3. Register social developer apps and add credentials to local `.env`.
4. Keep `DRY_RUN=true` while testing.
5. Switch `DRY_RUN=false`.
6. Post immediately or schedule from the Publish page.
7. Put `server.py` behind HTTPS + authentication before exposing it publicly.

## Architecture

```text
app.py                  Streamlit control center
server.py               FastAPI public/private API
core/
  config.py             .env settings
  db.py                 SQLite data layer + export/delete
  ingest.py             documents/web/social/voice transcript capture
  llm.py                Ollama chat + embeddings
  persona.py            seven-dimension model + retrieval + chat-as-you
  content.py            content generation
  media.py              local image/video backends
  publisher.py          official social posting adapters
  scheduler.py          scheduled posts
  tools.py              automation bridge + capability manifest
```

## Deliberate limits

This repository is a clean-room implementation from public feature descriptions. It does **not** contain Uare.ai source code, its proprietary implementation, private integration code, or trademarked UI.

"1,000+ tools" is handled as an extensible automation bridge rather than hard-coding 1,000 vendor SDKs. Add another provider in `core/publisher.py`, or point `AUTOMATION_WEBHOOK_URL` at your automation hub.

## Next engineering upgrades

- Real OAuth callback screens instead of placing tokens in `.env`.
- Encrypted OAuth token vault.
- Chunk-level embedding cache/vector index.
- Authorized social importers that pull your post history.
- Public subscriber frontend.
- Per-platform approval queues.
- Full Stripe Checkout/subscription creation flow.
- Background worker separated from Streamlit for always-on posting.
- Local voice cloning/TTS backend.
