import os
from contextlib import contextmanager

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def _database_settings():
    required_settings = {
        "MYSQL_HOST": os.getenv("MYSQL_HOST"),
        "MYSQL_USER": os.getenv("MYSQL_USER"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD"),
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
    }
    missing_settings = [
        name for name, value in required_settings.items() if not value
    ]
    if missing_settings:
        raise RuntimeError(
            "Missing database settings: " + ", ".join(missing_settings)
        )

    try:
        port = int(os.getenv("MYSQL_PORT", "3306"))
    except ValueError as error:
        raise RuntimeError("MYSQL_PORT must be a valid number") from error

    if not 1 <= port <= 65535:
        raise RuntimeError("MYSQL_PORT must be between 1 and 65535")

    return required_settings, port


def get_connection():
    settings, port = _database_settings()
    return mysql.connector.connect(
        host=settings["MYSQL_HOST"],
        port=port,
        user=settings["MYSQL_USER"],
        password=settings["MYSQL_PASSWORD"],
        database=settings["MYSQL_DATABASE"],
    )


@contextmanager
def connection_scope():
    """Close a connection and roll back if work inside the scope fails."""
    connection = get_connection()
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


@contextmanager
def cursor_scope(dictionary=False):
    """Provide a cursor and connection with reliable cleanup."""
    with connection_scope() as connection:
        cursor = connection.cursor(dictionary=dictionary)
        try:
            yield connection, cursor
        finally:
            cursor.close()
