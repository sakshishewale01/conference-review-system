import mysql.connector


def get_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Sakshi@123",
        database="conf_review_system"
    )