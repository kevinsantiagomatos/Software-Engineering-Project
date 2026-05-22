import os
from pathlib import Path

import pymysql

BASE_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path):
    #carga archivo .env sin sobrescribir vars existentes
    if not path.exists() or not path.is_file():
        return
    
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()


        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ[key] = value


_load_env_file(BASE_DIR / ".env")
_load_env_file(BACKEND_DIR / ".env")

#configuracion base de red y entorno de desa
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "5000")) #o 5001
DEV_AUTOLOGIN_EMAIL = (os.getenv("DEV_AUTOLOGIN_EMAIL") or "").strip().lower()
DEV_AUTOLOGIN_ROLE = (os.getenv("DEV_AUTOLOGIN_ROLE") or "hr").strip().lower()

#configuracion central de conexion a mysql
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "palogroup"), #no cambien plis
    "cursorclass": pymysql.cursors.DictCursor,
    "charset": "utf8mb4",
    "autocommit": True,
}
#configuracion opcional de ssl para proveedores gestionados como aiven
db_ssl_mode = (os.getenv("DB_SSL_MODE") or "").strip().lower()
db_ssl_ca = (os.getenv("DB_SSL_CA") or "").strip()
if db_ssl_mode in {"required", "verify_ca", "verify_identity"} or db_ssl_ca:
    ssl_options = {}
    if db_ssl_mode == "required" and not db_ssl_ca:
        ssl_options["any_non_empty_dict"] = True
    if db_ssl_ca:
        ssl_options["ca"] = db_ssl_ca
    if db_ssl_mode == "verify_ca":
        ssl_options["check_hostname"] = False
    DB_CONFIG["ssl"] = ssl_options or {"any_non_empty_dict": True}
DB_AUTO_INIT = os.getenv("DB_AUTO_INIT", "true").strip().lower() not in {"0", "false", "no"}

#rutas principales de proyecto y recursos

FRONT_END_DIR = BASE_DIR / "front_end"
STYLE_DIR = BASE_DIR / "style"
DATA_DIR = BASE_DIR / "data_store"
UPLOAD_DIR = BASE_DIR / "uploads"
PROFILE_DIR = UPLOAD_DIR / "profile"
HIRES_DIR = UPLOAD_DIR / "hires"
PLACEHOLDER_DIR = UPLOAD_DIR / "placeholders"
SCHEMA_PATH = BACKEND_DIR / "sql" / "paolischema.sql"
