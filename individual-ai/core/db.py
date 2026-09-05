from __future__ import annotations
import json, sqlite3, time, uuid
from contextlib import contextmanager
from typing import Any
from .config import settings

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY, source TEXT NOT NULL, title TEXT, text TEXT NOT NULL,
  metadata TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS hlm (
  dimension TEXT PRIMARY KEY, summary TEXT NOT NULL DEFAULT '', evidence TEXT NOT NULL DEFAULT '[]', updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS preferences (
  key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS skills (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, instructions TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS services (
  id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL, price_cents INTEGER NOT NULL DEFAULT 0, intake TEXT NOT NULL DEFAULT '[]', enabled INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS content (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT, body TEXT NOT NULL, media_path TEXT,
  status TEXT NOT NULL DEFAULT 'draft', metadata TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
  id TEXT PRIMARY KEY, content_id TEXT, platform TEXT NOT NULL, scheduled_for REAL,
  posted_at REAL, status TEXT NOT NULL, remote_id TEXT, response TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS analytics (
  id INTEGER PRIMARY KEY AUTOINCREMENT, event TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS subscribers (
  id TEXT PRIMARY KEY, email TEXT, stripe_customer_id TEXT, active INTEGER NOT NULL DEFAULT 0, created_at REAL NOT NULL
);
"""

@contextmanager
def connect():
    con = sqlite3.connect(settings.db_path)
    con.row_factory = sqlite3.Row
    try:
        con.executescript(SCHEMA)
        yield con
        con.commit()
    finally:
        con.close()

def uid() -> str: return str(uuid.uuid4())
def now() -> float: return time.time()
def jdump(v: Any) -> str: return json.dumps(v, ensure_ascii=False)
def jload(v: str | None, default=None):
    if not v: return default
    try: return json.loads(v)
    except Exception: return default

def add_memory(source: str, text: str, title: str = "", metadata: dict | None = None) -> str:
    i=uid()
    with connect() as con:
        con.execute("INSERT INTO memories VALUES(?,?,?,?,?,?)",(i,source,title,text,jdump(metadata or {}),now()))
    return i

def list_memories(limit: int = 200):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()]

def upsert_hlm(dimension: str, summary: str, evidence: list[str] | None = None):
    with connect() as con:
        con.execute("""INSERT INTO hlm(dimension,summary,evidence,updated_at) VALUES(?,?,?,?)
        ON CONFLICT(dimension) DO UPDATE SET summary=excluded.summary,evidence=excluded.evidence,updated_at=excluded.updated_at""",
        (dimension,summary,jdump(evidence or []),now()))

def get_hlm():
    with connect() as con:
        return {r["dimension"]: {"summary":r["summary"],"evidence":jload(r["evidence"],[])} for r in con.execute("SELECT * FROM hlm")}

def set_pref(key: str, value: Any):
    with connect() as con:
        con.execute("""INSERT INTO preferences(key,value,updated_at) VALUES(?,?,?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",(key,jdump(value),now()))

def get_prefs():
    with connect() as con:
        return {r["key"]: jload(r["value"],r["value"]) for r in con.execute("SELECT * FROM preferences")}

def save_content(kind: str, body: str, title: str = "", media_path: str | None = None, metadata: dict | None = None, status: str="draft") -> str:
    i=uid()
    with connect() as con:
        con.execute("INSERT INTO content VALUES(?,?,?,?,?,?,?,?,?)",(i,kind,title,body,media_path,status,jdump(metadata or {}),now()))
    return i

def get_content(content_id: str):
    with connect() as con:
        r=con.execute("SELECT * FROM content WHERE id=?",(content_id,)).fetchone()
        return dict(r) if r else None

def list_content(limit=100):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM content ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()]

def log_event(event: str, payload: dict | None = None):
    with connect() as con:
        con.execute("INSERT INTO analytics(event,payload,created_at) VALUES(?,?,?)",(event,jdump(payload or {}),now()))

def log_post(content_id: str | None, platform: str, status: str, scheduled_for: float | None=None, posted_at: float | None=None, remote_id: str | None=None, response: dict | None=None) -> str:
    i=uid()
    with connect() as con:
        con.execute("INSERT INTO posts VALUES(?,?,?,?,?,?,?,?)",(i,content_id,platform,scheduled_for,posted_at,status,remote_id,jdump(response or {})))
    return i

def update_post(post_id: str, **fields):
    allowed={"scheduled_for","posted_at","status","remote_id","response"}
    bits=[]; vals=[]
    for k,v in fields.items():
        if k not in allowed: continue
        bits.append(f"{k}=?")
        vals.append(jdump(v) if k=="response" and isinstance(v,(dict,list)) else v)
    if not bits: return
    vals.append(post_id)
    with connect() as con:
        con.execute(f"UPDATE posts SET {', '.join(bits)} WHERE id=?", vals)

def due_posts(ts: float):
    with connect() as con:
        return [dict(r) for r in con.execute("SELECT * FROM posts WHERE status='scheduled' AND scheduled_for<=? ORDER BY scheduled_for",(ts,)).fetchall()]

def export_all():
    with connect() as con:
        out={}
        for table in ("memories","hlm","preferences","skills","services","content","posts","analytics","subscribers"):
            out[table]=[dict(r) for r in con.execute(f"SELECT * FROM {table}").fetchall()]
        return out

def delete_all():
    with connect() as con:
        for table in ("memories","hlm","preferences","skills","services","content","posts","analytics","subscribers"):
            con.execute(f"DELETE FROM {table}")
