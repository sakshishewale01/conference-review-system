import os

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


def get_connection():
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

    return mysql.connector.connect(
        host=required_settings["MYSQL_HOST"],
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=required_settings["MYSQL_USER"],
        password=required_settings["MYSQL_PASSWORD"],
        database=required_settings["MYSQL_DATABASE"],
    )
