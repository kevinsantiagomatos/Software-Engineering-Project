import os
from pathlib import Path

import pymysql

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000"))
DEV_AUTOLOGIN_EMAIL = (os.getenv("DEV_AUTOLOGIN_EMAIL") or "").strip().lower()
DEV_AUTOLOGIN_ROLE = (os.getenv("DEV_AUTOLOGIN_ROLE") or "hr").strip().lower()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "palogroup"),
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": True,
}
DB_AUTO_INIT = os.getenv("DB_AUTO_INIT", "true").strip().lower() not in {"0", "false", "no"}

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]
FRONT_END_DIR = BASE_DIR / "front_end"
STYLE_DIR = BASE_DIR / "style"
DATA_DIR = BASE_DIR / "data_store"
UPLOAD_DIR = BASE_DIR / "uploads"
PROFILE_DIR = UPLOAD_DIR / "profile"
HIRES_DIR = UPLOAD_DIR / "hires"
PLACEHOLDER_DIR = UPLOAD_DIR / "placeholders"
SCHEMA_PATH = BACKEND_DIR / "sql" / "paolischema.sql"
