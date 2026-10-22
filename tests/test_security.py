import io
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import MagicMock, patch

from werkzeug.security import generate_password_hash

import app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(
            TESTING=True,
            WTF_CSRF_ENABLED=True,
            SECRET_KEY="test-secret",
        )
        self.client = app.app.test_client()

    def _csrf_token(self, path):
        response = self.client.get(path)
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def test_post_without_csrf_token_is_rejected(self):
        response = self.client.post(
            "/register",
            data={
                "full_name": "Test User",
                "email": "test@example.com",
                "password": "long enough password",
                "role": "admin",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_ignores_admin_role(self):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = None
        connection.cursor.return_value = cursor

        @contextmanager
        def fake_scope(dictionary=False):
            yield connection, cursor

        token = self._csrf_token("/register")
        with patch.object(app, "cursor_scope", fake_scope):
            response = self.client.post(
                "/register",
                data={
                    "_csrf_token": token,
                    "full_name": "Test User",
                    "email": "test@example.com",
                    "password": "long enough password",
                    "role": "admin",
                },
            )

        self.assertEqual(response.status_code, 302)
        insert_call = cursor.execute.call_args_list[-1]
        self.assertIn("author", insert_call.args[1])
        self.assertNotIn("long enough password", insert_call.args[1])

    def test_login_stores_only_user_id(self):
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = {
            "user_id": 4,
            "full_name": "Test User",
            "email": "test@example.com",
            "role": "author",
            "password": generate_password_hash("long enough password"),
        }
        connection.cursor.return_value = cursor

        @contextmanager
        def fake_scope(dictionary=False):
            yield connection, cursor

        token = self._csrf_token("/login")
        with patch.object(app, "cursor_scope", fake_scope):
            response = self.client.post(
                "/login",
                data={
                    "_csrf_token": token,
                    "email": "test@example.com",
                    "password": "long enough password",
                },
            )

        self.assertEqual(response.status_code, 302)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], 4)
            self.assertNotIn("password", session)
            self.assertNotIn("role", session)
            self.assertNotIn("full_name", session)

    def test_admin_route_rejects_author(self):
        with patch.object(
            app,
            "_current_user",
            return_value={"user_id": 4, "role": "author"},
        ):
            response = self.client.get("/admin_dashboard")
        self.assertEqual(response.status_code, 403)

    def test_protected_route_redirects_anonymous_user(self):
        with patch.object(app, "_current_user", return_value=None):
            response = self.client.get("/submit_paper")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_upload_rejects_non_pdf(self):
        with patch.object(
            app,
            "_current_user",
            return_value={"user_id": 4, "role": "author"},
        ):
            token = self._csrf_token("/submit_paper")
            response = self.client.post(
                "/submit_paper",
                data={
                    "_csrf_token": token,
                    "title": "A valid title",
                    "abstract": "A valid abstract",
                    "keywords": "flask",
                    "paper_file": (
                        io.BytesIO(b"not a pdf"),
                        "malicious.html",
                    ),
                },
                content_type="multipart/form-data",
            )
        self.assertEqual(response.status_code, 400)

    def test_session_cookie_security_configuration(self):
        self.assertTrue(app.app.config["SESSION_COOKIE_HTTPONLY"])
        self.assertEqual(app.app.config["SESSION_COOKIE_SAMESITE"], "Lax")

    def test_valid_submission_uses_generated_pdf_path_and_pending_status(self):
        connection = MagicMock()
        cursor = MagicMock()
        connection.cursor.return_value = cursor
        user = {"user_id": 8, "role": "author"}

        @contextmanager
        def fake_scope(dictionary=False):
            yield connection, cursor

        with tempfile.TemporaryDirectory() as upload_dir:
            original_upload_dir = app.app.config["UPLOAD_FOLDER"]
            app.app.config["UPLOAD_FOLDER"] = upload_dir
            token = self._csrf_token("/register")
            with patch.object(app, "_current_user", return_value=user):
                with patch.object(app, "cursor_scope", fake_scope):
                    response = self.client.post(
                        "/submit_paper",
                        data={
                            "_csrf_token": token,
                            "title": "A meaningful paper title",
                            "abstract": "A meaningful abstract " * 5,
                            "keywords": "flask, security",
                            "paper_file": (
                                io.BytesIO(b"%PDF-1.7 test"),
                                "../../unsafe-name.pdf",
                            ),
                        },
                        content_type="multipart/form-data",
                    )
            app.app.config["UPLOAD_FOLDER"] = original_upload_dir

        self.assertEqual(response.status_code, 302)
        insert_call = next(
            call for call in cursor.execute.call_args_list
            if "INSERT INTO papers" in call.args[0]
        )
        values = insert_call.args[1]
        self.assertEqual(values[-1], "Pending")
        self.assertEqual(values[4], "unsafe-name.pdf")
        self.assertTrue(values[5].endswith(".pdf"))
        self.assertNotIn("unsafe-name", values[5])

    def test_invalid_status_filter_is_rejected(self):
        with patch.object(
            app,
            "_current_user",
            return_value={"user_id": 4, "role": "admin"},
        ):
            response = self.client.get("/papers?status=Unknown")
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
