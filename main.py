import asyncio
import json
import os
import hashlib
import secrets
import time
import aiofiles
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# ====================== رمز ثابت تست (بدون هیچ متغیر) ======================
ADMIN_PASSWORD = "369147"   # فقط برای تست، بعداً عوض می‌کنی
# ============================================================================

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("X4G-Gateway")

IRAN_TZ = ZoneInfo("Asia/Tehran")

app = FastAPI(title="X4G Gateway", docs_url=None, redoc_url=None)

# ── Persistence ─────────────────────────────────────────────────────────────
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DATA_FILE = DATA_DIR / "x4g_state.json"
SAVE_LOCK = asyncio.Lock()

async def load_state():
    global LINKS, SUBS, AUTH
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DATA_FILE.exists():
            async with aiofiles.open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
            LINKS.update(data.get("links", {}))
            SUBS.update(data.get("subs", {}))
            if "password_hash" in data:
                AUTH["password_hash"] = data["password_hash"]
            logger.info(f"State loaded: {len(LINKS)} links, {len(SUBS)} subs")
    except Exception as e:
        logger.warning(f"Could not load state: {e}")

async def save_state():
    async with SAVE_LOCK:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                "links": dict(LINKS),
                "subs": dict(SUBS),
                "password_hash": AUTH["password_hash"],
                "saved_at": datetime.now().isoformat(),
            }
            tmp = DATA_FILE.with_suffix(".tmp")
            async with aiofiles.open(tmp, "w", encoding="utf-8") as f:
                await f.write(json.dumps(data, ensure_ascii=False, indent=2))
            tmp.replace(DATA_FILE)
        except Exception as e:
            logger.warning(f"Could not save state: {e}")

# ── In-memory state ───────────────────────────────────────────────────────────
LINKS: dict = {}
LINKS_LOCK = asyncio.Lock()
SUBS: dict = {}
SUBS_LOCK = asyncio.Lock()

# ── Auth (رمز ثابت 369147 - بدون هیچ متغیر) ────────────────────────────────
SESSION_COOKIE = "x4g_session"
SESSION_TTL = 60 * 60 * 24 * 7

def hash_password(pw: str) -> str:
    return hashlib.sha256(f"{pw}369147".encode()).hexdigest()

AUTH = {"password_hash": hash_password(ADMIN_PASSWORD)}
SESSIONS: dict = {}
SESSIONS_LOCK = asyncio.Lock()

async def create_session():
    token = secrets.token_urlsafe(32)
    async with SESSIONS_LOCK:
        SESSIONS[token] = time.time() + SESSION_TTL
    return token

async def is_valid_session(token: str | None) -> bool:
    if not token:
        return False
    async with SESSIONS_LOCK:
        exp = SESSIONS.get(token)
        if exp is None or exp < time.time():
            SESSIONS.pop(token, None)
            return False
        return True

async def require_auth(request: Request):
    token = request.cookies.get(SESSION_COOKIE)
    if not await is_valid_session(token):
        raise HTTPException(status_code=401, detail="unauthorized")
    return token

# ── Startup / Shutdown ────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await load_state()
    logger.info(f"X4G Gateway v9.2 started on port {PORT}")

@app.on_event("shutdown")
async def shutdown():
    await save_state()

# ── Health & Simple Page (صفحه اول مستقیم باز می‌شه) ───────────────────────
@app.get("/")
async def root():
    return HTMLResponse("<h1 style='text-align:center;margin-top:100px'>X4G Gateway v9.2<br>Deployed on livemy.app</h1>")

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

# ── Login Page (صفحه داشبورد اول) ───────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/dashboard")
    return HTMLResponse("""
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <title>X4G Gateway - Login</title>
    <style>
        body { font-family: Tahoma, Arial; background:#0f0f0f; color:#fff; text-align:center; padding:80px 20px; }
        .card { background:#1a1a1a; padding:40px; border-radius:12px; width:320px; margin:0 auto; box-shadow:0 0 20px rgba(0,0,0,0.5); }
        input { width:100%; padding:15px; margin:10px 0; border-radius:8px; border:none; background:#222; color:white; }
        button { width:100%; padding:15px; background:#00c853; color:white; border:none; border-radius:8px; font-size:16px; }
    </style>
</head>
<body>
<div class="card">
    <h1>X4G Gateway v9.2</h1>
    <form action="/login" method="post">
        <input type="password" name="password" placeholder="رمز ادمین" required>
        <button type="submit">ورود</button>
    </form>
</div>
</body>
</html>
    """)

@app.post("/login")
async def login_post(request: Request):
    form = await request.form()
    password = form.get("password")
    if hash_password(password) == AUTH["password_hash"]:
        token = await create_session()
        response = RedirectResponse(url="/dashboard")
        response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_TTL, httponly=True)
        return response
    return HTMLResponse("<h2>رمز اشتباه است</h2>")

# ── Dashboard Page (صفحه اول بعد از ورود) ───────────────────────────────────
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not await is_valid_session(request.cookies.get(SESSION_COOKIE)):
        return RedirectResponse(url="/login")
    return HTMLResponse(f"""
<!DOCTYPE html>
<html lang="fa">
<head>
    <meta charset="UTF-8">
    <title>داشبورد X4G Gateway</title>
    <style>body {{ font-family: Tahoma; background:#0f0f0f; color:#fff; text-align:center; padding:50px; }}</style>
</head>
<body>
<h1>خوش آمدید به X4G Gateway v9.2</h1>
<p>پروژه با موفقیت روی livemy.app deploy شد.</p>
<p>رمز تست: 369147 (بعداً عوض می‌کنی)</p>
</body>
</html>
    """)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="info")
