# =============================================
# ════ X4G Gateway v9.2 - متغیرهای محیطی Render ════
# =============================================

import os
from pathlib import Path
from dotenv import load_dotenv  # فقط برای تست محلی، در Render حذف کن

load_dotenv()  # برای تست محلی (اختیاری)

# ── متغیرهای اصلی پنل ─────────────────────
PORT = int(os.environ.get("PORT", 8000))
SECRET_KEY = os.environ.get("SECRET_KEY", "x4g-default-secret-2026")  # برای تست محلی
RAILWAY_PUBLIC_DOMAIN = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "localhost")
DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))

# ── رمز ادمین (در پنل تغییر می‌کنی) ────────
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123456")  # تغییر در Render Settings

# ── متغیرهای اضافی (در Render اضافه کن) ─────
X4G_SECRET = os.environ.get("X4G_SECRET", SECRET_KEY)  # برای compatibility قدیمی
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# استفاده از رمز ادمین در AUTH
AUTH["password_hash"] = hash_password(ADMIN_PASSWORD)
