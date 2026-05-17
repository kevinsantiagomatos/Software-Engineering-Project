import os

import pymysql

from .settings import DB_CONFIG


def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.err.OperationalError as exc:
        # Local-dev fallback: some environments use root/password by default.
        err_code = exc.args[0] if exc.args else None
        if (
            err_code == 1045
            and (DB_CONFIG.get("user") or "").strip().lower() == "root"
            and not (DB_CONFIG.get("password") or "")
            and not os.getenv("DB_PASSWORD")
        ):
            fallback_config = dict(DB_CONFIG)
            fallback_config["password"] = "password"
            return pymysql.connect(**fallback_config)
        raise


def fetch_all(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()


def fetch_one(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()


def execute(query: str, params=None):
    params = params or ()
    with get_db_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, params)
        connection.commit()
