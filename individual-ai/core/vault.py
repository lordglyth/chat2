from __future__ import annotations
import base64, hashlib, os
from pathlib import Path
from cryptography.fernet import Fernet
from .config import settings
from . import db

KEY_FILE=Path("data/.vault.key")

def _key() -> bytes:
    if settings.master_key:
        return base64.urlsafe_b64encode(hashlib.sha256(settings.master_key.encode("utf-8")).digest())
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes().strip()
    KEY_FILE.parent.mkdir(parents=True,exist_ok=True)
    key=Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    try: os.chmod(KEY_FILE,0o600)
    except OSError: pass
    return key

def _fernet(): return Fernet(_key())

def ensure_table():
    with db.connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS secrets (key TEXT PRIMARY KEY, value BLOB NOT NULL, updated_at REAL NOT NULL)")

def set_secret(key: str, value: str):
    ensure_table()
    enc=_fernet().encrypt((value or "").encode("utf-8"))
    with db.connect() as con:
        con.execute("INSERT INTO secrets(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at",(key,enc,db.now()))

def get_secret(key: str, fallback: str="") -> str:
    ensure_table()
    with db.connect() as con:
        row=con.execute("SELECT value FROM secrets WHERE key=?",(key,)).fetchone()
    if not row: return fallback
    try: return _fernet().decrypt(row["value"]).decode("utf-8")
    except Exception: return fallback

def has_secret(key: str, fallback: str="") -> bool:
    return bool(get_secret(key,fallback))

def delete_secret(key: str):
    ensure_table()
    with db.connect() as con: con.execute("DELETE FROM secrets WHERE key=?",(key,))
