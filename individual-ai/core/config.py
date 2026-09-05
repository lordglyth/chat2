from __future__ import annotations
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Soji Individual AI"
    db_path: str = "data/individual_ai.db"
    master_key: str = ""
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "huihui_ai/devstral-small-2-24b-instruct"
    embed_model: str = "nomic-embed-text"
    dry_run: bool = True
    public_base_url: str = "http://127.0.0.1:8787"
    timezone: str = "America/New_York"

    a1111_url: str = "http://127.0.0.1:7860"
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_video_workflow: str = ""

    meta_api_version: str = "v24.0"
    meta_access_token: str = ""
    facebook_page_id: str = ""
    instagram_user_id: str = ""

    linkedin_access_token: str = ""
    linkedin_author_urn: str = ""
    linkedin_version: str = "202608"

    mastodon_base_url: str = ""
    mastodon_access_token: str = ""

    bluesky_handle: str = ""
    bluesky_app_password: str = ""
    tiktok_access_token: str = ""

    youtube_client_secret_file: str = ""
    youtube_token_file: str = "tokens/youtube_token.json"

    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_id: str = ""

    automation_webhook_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def ensure_dirs(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        Path("data/uploads").mkdir(parents=True, exist_ok=True)
        Path("data/generated").mkdir(parents=True, exist_ok=True)
        Path("tokens").mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_dirs()
