import pymysql

from .settings import DB_CONFIG


def get_db_connection():
    return pymysql.connect(**DB_CONFIG)


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
