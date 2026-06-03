import hashlib
import os
import logging
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware

from bot import database as db

logger = logging.getLogger(__name__)

ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "changeme123")
TOKEN = hashlib.sha256(ADMIN_SECRET.encode()).hexdigest()

app = FastAPI(docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True


@app.get("/", response_class=HTMLResponse)
async def serve_panel():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()


@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    if data.get("password") == ADMIN_SECRET:
        return {"token": TOKEN, "success": True}
    raise HTTPException(status_code=401, detail="Wrong password")


@app.get("/api/stats")
async def get_stats(authorized=Depends(verify_token)):
    stats = await db.get_stats()
    return dict(stats)


@app.get("/api/users")
async def get_users(page: int = 1, search: str = "", authorized=Depends(verify_token)):
    pool = await db.get_pool()
    offset = (page - 1) * 20
    if search:
        rows = await pool.fetch(
            """SELECT * FROM users WHERE (username ILIKE $1 OR first_name ILIKE $1
               OR CAST(user_id AS TEXT) LIKE $1) ORDER BY join_date DESC LIMIT 20 OFFSET $2""",
            f"%{search}%", offset
        )
        total = await pool.fetchval(
            "SELECT COUNT(*) FROM users WHERE (username ILIKE $1 OR first_name ILIKE $1 OR CAST(user_id AS TEXT) LIKE $1)",
            f"%{search}%"
        )
    else:
        rows = await pool.fetch("SELECT * FROM users ORDER BY join_date DESC LIMIT 20 OFFSET $1", offset)
        total = await pool.fetchval("SELECT COUNT(*) FROM users")

    users = []
    for r in rows:
        d = dict(r)
        if d.get("join_date"):
            d["join_date"] = d["join_date"].isoformat()
        users.append(d)
    return {"users": users, "total": total, "page": page}


@app.post("/api/users/{user_id}/ban")
async def ban_user_api(user_id: int, authorized=Depends(verify_token)):
    await db.ban_user(user_id)
    return {"success": True}


@app.post("/api/users/{user_id}/unban")
async def unban_user_api(user_id: int, authorized=Depends(verify_token)):
    await db.unban_user(user_id)
    return {"success": True}


@app.post("/api/users/{user_id}/premium")
async def set_premium(user_id: int, authorized=Depends(verify_token)):
    pool = await db.get_pool()
    await pool.execute("UPDATE users SET is_premium = TRUE WHERE user_id = $1", user_id)
    return {"success": True}


@app.delete("/api/users/{user_id}/premium")
async def remove_premium(user_id: int, authorized=Depends(verify_token)):
    pool = await db.get_pool()
    await pool.execute("UPDATE users SET is_premium = FALSE WHERE user_id = $1", user_id)
    return {"success": True}


@app.get("/api/files")
async def get_files(page: int = 1, search: str = "", authorized=Depends(verify_token)):
    pool = await db.get_pool()
    offset = (page - 1) * 20
    if search:
        rows = await pool.fetch(
            """SELECT f.*, u.username, u.first_name FROM files f
               LEFT JOIN users u ON f.uploader_id = u.user_id
               WHERE f.file_name ILIKE $1 ORDER BY f.upload_date DESC LIMIT 20 OFFSET $2""",
            f"%{search}%", offset
        )
        total = await pool.fetchval("SELECT COUNT(*) FROM files WHERE file_name ILIKE $1", f"%{search}%")
    else:
        rows = await pool.fetch(
            """SELECT f.*, u.username, u.first_name FROM files f
               LEFT JOIN users u ON f.uploader_id = u.user_id
               ORDER BY f.upload_date DESC LIMIT 20 OFFSET $1""",
            offset
        )
        total = await pool.fetchval("SELECT COUNT(*) FROM files")

    files = []
    for r in rows:
        d = dict(r)
        if d.get("upload_date"):
            d["upload_date"] = d["upload_date"].isoformat()
        files.append(d)
    return {"files": files, "total": total, "page": page}


@app.delete("/api/files/{unique_code}")
async def delete_file_api(unique_code: str, authorized=Depends(verify_token)):
    await db.delete_file(unique_code)
    return {"success": True}


@app.get("/api/channels")
async def get_channels(authorized=Depends(verify_token)):
    rows = await db.get_force_join_channels()
    return {"channels": [dict(r) for r in rows]}


@app.post("/api/channels")
async def add_channel_api(request: Request, authorized=Depends(verify_token)):
    data = await request.json()
    channel_id = data.get("channel_id", "").strip()
    channel_username = data.get("channel_username", "").strip() or None
    if not channel_id:
        raise HTTPException(status_code=400, detail="channel_id is required")
    await db.add_force_join_channel(channel_id, channel_username)
    return {"success": True}


@app.delete("/api/channels/{channel_id:path}")
async def remove_channel_api(channel_id: str, authorized=Depends(verify_token)):
    await db.remove_force_join_channel(channel_id)
    return {"success": True}


@app.get("/api/texts")
async def get_texts(authorized=Depends(verify_token)):
    pool = await db.get_pool()
    rows = await pool.fetch("SELECT * FROM bot_texts ORDER BY key")
    return {"texts": {r["key"]: r["value"] for r in rows}}


@app.put("/api/texts/{key}")
async def update_text(key: str, request: Request, authorized=Depends(verify_token)):
    data = await request.json()
    value = data.get("value", "")
    await db.set_bot_text(key, value)
    return {"success": True}


@app.post("/api/broadcast")
async def queue_broadcast(request: Request, authorized=Depends(verify_token)):
    data = await request.json()
    message = data.get("message", "").strip()
    target = data.get("target", "all")
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    pool = await db.get_pool()
    await pool.execute(
        "INSERT INTO broadcast_queue (message, target_group, status) VALUES ($1, $2, 'pending')",
        message, target
    )
    return {"success": True, "message": "Broadcast queued and will be sent shortly"}


@app.get("/api/broadcast/history")
async def get_broadcast_history_api(authorized=Depends(verify_token)):
    rows = await db.get_broadcast_history()
    history = []
    for r in rows:
        d = dict(r)
        if d.get("sent_at"):
            d["sent_at"] = d["sent_at"].isoformat()
        history.append(d)
    return {"history": history}
