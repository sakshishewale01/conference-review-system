import os
import unittest
from unittest.mock import MagicMock, patch

import db


class DatabaseLayerTests(unittest.TestCase):
    def setUp(self):
        self.environment = {
            "MYSQL_HOST": "localhost",
            "MYSQL_PORT": "3306",
            "MYSQL_USER": "test-user",
            "MYSQL_PASSWORD": "test-password",
            "MYSQL_DATABASE": "test-database",
        }

    def test_missing_configuration_fails_before_connecting(self):
        with patch.dict(os.environ, self.environment, clear=True):
            del os.environ["MYSQL_PASSWORD"]
            with patch.object(db.mysql.connector, "connect") as connect:
                with self.assertRaisesRegex(
                    RuntimeError,
                    "MYSQL_PASSWORD",
                ):
                    db.get_connection()
                connect.assert_not_called()

    def test_valid_configuration_is_passed_to_mysql_connector(self):
        connection = MagicMock()
        with patch.dict(os.environ, self.environment, clear=True):
            with patch.object(
                db.mysql.connector,
                "connect",
                return_value=connection,
            ) as connect:
                result = db.get_connection()

        self.assertIs(result, connection)
        connect.assert_called_once_with(
            host="localhost",
            port=3306,
            user="test-user",
            password="test-password",
            database="test-database",
        )

    def test_connection_scope_rolls_back_and_closes_on_failure(self):
        connection = MagicMock()
        with patch.object(db, "get_connection", return_value=connection):
            with self.assertRaisesRegex(RuntimeError, "query failed"):
                with db.connection_scope():
                    raise RuntimeError("query failed")

        connection.rollback.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_cursor_scope_closes_cursor_and_connection(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        with patch.object(db, "get_connection", return_value=connection):
            with db.cursor_scope(dictionary=True) as values:
                self.assertEqual(values, (connection, cursor))

        connection.cursor.assert_called_once_with(dictionary=True)
        cursor.close.assert_called_once_with()
        connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
