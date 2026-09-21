import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import current_identity, identity_from_claims


class AuthTests(unittest.TestCase):
    def test_verified_approved_instructor_is_normalized(self) -> None:
        with patch.dict(os.environ, {"INSTRUCTOR_EMAILS": "teacher@example.edu"}):
            identity = identity_from_claims({
                "sub": "google-subject",
                "email": " Teacher@Example.edu ",
                "email_verified": True,
            })
        self.assertEqual(identity.email, "teacher@example.edu")
        self.assertTrue(identity.is_instructor)

    def test_unverified_email_is_rejected(self) -> None:
        with self.assertRaises(HTTPException) as raised:
            identity_from_claims({
                "sub": "google-subject",
                "email": "student@example.edu",
                "email_verified": False,
            })
        self.assertEqual(raised.exception.status_code, 401)

    def test_google_token_is_verified_for_the_configured_client(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="sample-token")
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": "web-client-id", "AUTH_MODE": "google"}):
            with patch("app.auth.id_token.verify_oauth2_token") as verify:
                verify.return_value = {
                    "sub": "google-subject",
                    "email": "student@example.edu",
                    "email_verified": True,
                }
                identity = current_identity(credentials)

        self.assertEqual(identity.email, "student@example.edu")
        self.assertEqual(verify.call_args.args[0], "sample-token")
        self.assertEqual(verify.call_args.args[2], "web-client-id")

    def test_mock_identity_requires_explicit_development_mode(self) -> None:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="mock:teacher@example.edu")
        with patch.dict(os.environ, {"AUTH_MODE": "mock", "APP_ENV": "development", "INSTRUCTOR_EMAILS": "teacher@example.edu"}):
            self.assertTrue(current_identity(credentials).is_instructor)
        with patch.dict(os.environ, {"AUTH_MODE": "mock", "APP_ENV": "production"}):
            with self.assertRaises(HTTPException) as raised:
                current_identity(credentials)
        self.assertEqual(raised.exception.status_code, 503)
