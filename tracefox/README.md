# TraceFox 🦊

TraceFox is a local Windows-friendly username archaeology tool: enter a handle, check publicly reachable profile URLs across the community-maintained **WhatsMyName** dataset, inspect the matches, and optionally ask one of your **local Ollama models** to cluster the results.

The important design rule is simple: **same username does not mean same person**. TraceFox separates profile discovery from identity correlation instead of gluing every matching handle into one giant dossier.

## What it does

- Searches the current WhatsMyName dataset (700+ public-site definitions when available).
- Runs concurrent HTTP checks locally; there is no TraceFox account, cloud backend, or search quota.
- Shows **Found / Uncertain / Errors** separately.
- Extracts public page metadata such as title, description, avatar/OG image, and canonical URL when a site allows it.
- Detects installed Ollama models automatically.
- Lets you select any installed Ollama model for local collision/cluster analysis.
- Stores completed scans locally under `data/history/`.
- Exports JSON and CSV.
- Includes Windows setup and launcher batch files.

## Windows install

1. Install **Python 3.11+**.
2. Install and run **Ollama** if you want local AI correlation. The username scanner itself works without Ollama.
3. Double-click `setup.bat` once.
4. Double-click `start.bat` whenever you want TraceFox.
5. Your browser opens to `http://127.0.0.1:8765`.

TraceFox asks Ollama's local API at `http://127.0.0.1:11434/api/tags` for installed models and uses `/api/chat` for analysis. No external AI API key is required.

## Data source and attribution

TraceFox downloads `wmn-data.json` at runtime from [WebBreacher/WhatsMyName](https://github.com/WebBreacher/WhatsMyName) and caches it locally. WhatsMyName is licensed separately under **CC BY-SA 4.0**. TraceFox's own source code is MIT licensed.

## Scope

TraceFox focuses on public username profiles. It does not perform breached-credential searches, password recovery, private-account access, or phone/email data-broker lookups.

## Development / test

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
python app.py
```
