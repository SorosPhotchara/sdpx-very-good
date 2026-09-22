"""Verify Google identities and derive local instructor eligibility."""

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    is_instructor: bool


def identity_from_claims(claims: dict[str, object]) -> Identity:
    email = claims.get("email")
    subject = claims.get("sub")
    if claims.get("email_verified") is not True or not isinstance(email, str) or not isinstance(subject, str):
        raise HTTPException(status_code=401, detail="Unverified Google identity")

    normalized_email = email.strip().lower()
    if not normalized_email or not subject:
        raise HTTPException(status_code=401, detail="Incomplete Google identity")
    approved = approved_instructors()
    return Identity(subject=subject, email=normalized_email, is_instructor=normalized_email in approved)


def approved_instructors() -> set[str]:
    return {
        address.strip().lower()
        for address in os.environ.get("INSTRUCTOR_EMAILS", "").split(",")
        if address.strip()
    }


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Identity:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    if os.environ.get("AUTH_MODE") == "mock":
        if os.environ.get("APP_ENV") != "development":
            raise HTTPException(status_code=503, detail="Mock sign-in requires development mode")
        email = credentials.credentials.removeprefix("mock:").strip().lower()
        if not credentials.credentials.startswith("mock:") or "@" not in email or ":" in email:
            raise HTTPException(status_code=401, detail="Invalid demo identity")
        return identity_from_claims({"sub": f"demo:{email}", "email": email, "email_verified": True})
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")

    try:
        claims = id_token.verify_oauth2_token(
            credentials.credentials, requests.Request(), client_id
        )
    except ValueError as error:
        raise HTTPException(status_code=401, detail="Invalid Google token") from error
    except GoogleAuthError as error:
        raise HTTPException(status_code=503, detail="Google token verification unavailable") from error
    return identity_from_claims(claims)
