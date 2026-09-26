"""Verify Google identities and derive local instructor eligibility."""

import os
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests
from google.oauth2 import id_token
from . import models
from .database import get_db

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Identity:
    subject: str
    email: str
    is_instructor: bool
    is_admin: bool = False
    picture_url: str | None = None


def identity_from_claims(claims: dict[str, object]) -> Identity:
    email = claims.get("email")
    subject = claims.get("sub")
    if claims.get("email_verified") is not True or not isinstance(email, str) or not isinstance(subject, str):
        raise HTTPException(status_code=401, detail="Unverified Google identity")

    normalized_email = email.strip().lower()
    if not normalized_email or not subject:
        raise HTTPException(status_code=401, detail="Incomplete Google identity")
    approved = approved_instructors()
    admins = configured_admins()
    return Identity(
        subject=subject,
        email=normalized_email,
        is_instructor=normalized_email in approved,
        is_admin=normalized_email in admins,
        picture_url=claims.get("picture") if isinstance(claims.get("picture"), str) else None,
    )


def configured_admins() -> set[str]:
    return {
        address.strip().lower()
        for address in os.environ.get("ADMIN_EMAILS", "").split(",")
        if address.strip()
    }


def approved_instructors(db: Session | None = None) -> set[str]:
    approved = {
        address.strip().lower()
        for address in os.environ.get("INSTRUCTOR_EMAILS", "").split(",")
        if address.strip()
    }
    if db is not None:
        approved.update(db.scalars(select(models.InstructorApproval.email)))
    return approved


def current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Identity:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in required")
    if os.environ.get("AUTH_MODE") == "mock":
        if os.environ.get("APP_ENV") != "development":
            raise HTTPException(status_code=503, detail="Mock sign-in requires development mode")
        email = credentials.credentials.removeprefix("mock:").strip().lower()
        if not credentials.credentials.startswith("mock:") or "@" not in email or ":" in email:
            raise HTTPException(status_code=401, detail="Invalid demo identity")
        identity = identity_from_claims({"sub": f"demo:{email}", "email": email, "email_verified": True})
        return _apply_database_approval(identity, db)
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
    return _apply_database_approval(identity_from_claims(claims), db)


def _apply_database_approval(identity: Identity, db: Session) -> Identity:
    if not isinstance(db, Session):
        return identity
    return Identity(
        subject=identity.subject,
        email=identity.email,
        is_instructor=identity.is_instructor or db.get(models.InstructorApproval, identity.email) is not None,
        is_admin=identity.is_admin,
        picture_url=identity.picture_url,
    )
