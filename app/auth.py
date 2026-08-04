"""Relational authentication and campaign authorization for Emporos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
import secrets

import psycopg
from psycopg.rows import dict_row

from app.database import database_url


SESSION_COOKIE = "emporos_session"
SESSION_DAYS = 30


@dataclass(frozen=True)
class User:
    user_id: int
    public_id: str
    email: str
    display_name: str


def _connect():
    url = database_url()
    if not url:
        raise RuntimeError("No Emporos database URL is configured")
    return psycopg.connect(url, row_factory=dict_row)


def _digest(token: str) -> bytes:
    return hashlib.sha256(token.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters")
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode(), salt=salt, n=2**15, r=8, p=1, maxmem=64*1024*1024
    )
    return f"scrypt$32768$8$1${salt.hex()}${derived.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt, expected = encoded.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p),
            maxmem=64*1024*1024,
        )
        return hmac.compare_digest(actual, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


def register(email: str, display_name: str, password: str) -> User:
    normalized = email.strip().lower()
    if "@" not in normalized or not display_name.strip():
        raise ValueError("A valid email and display name are required")
    encoded = hash_password(password)
    try:
        with _connect() as connection:
            row = connection.execute(
                """INSERT INTO auth_user_account(email,display_name,password_hash)
                   VALUES(%s,%s,%s)
                   RETURNING user_id,public_id::text,email,display_name""",
                (normalized, display_name.strip(), encoded),
            ).fetchone()
    except psycopg.errors.UniqueViolation as exc:
        raise ValueError("An account already exists for that email") from exc
    return User(**row)


def authenticate(email: str, password: str) -> User | None:
    with _connect() as connection:
        row = connection.execute(
            """SELECT user_id,public_id::text,email,display_name,password_hash
               FROM auth_user_account WHERE email=%s AND account_status='active'""",
            (email.strip().lower(),),
        ).fetchone()
    if not row or not verify_password(password, row.pop("password_hash")):
        return None
    return User(**row)


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_DAYS)
    with _connect() as connection:
        connection.execute(
            "INSERT INTO auth_user_session(user_id,token_digest,expires_at) VALUES(%s,%s,%s)",
            (user_id, _digest(token), expires),
        )
    return token


def user_for_session(token: str | None) -> User | None:
    if not token:
        return None
    with _connect() as connection:
        row = connection.execute(
            """UPDATE auth_user_session session SET last_seen_at=clock_timestamp()
               FROM auth_user_account account
               WHERE session.token_digest=%s AND session.revoked_at IS NULL
                 AND session.expires_at>clock_timestamp()
                 AND account.user_id=session.user_id AND account.account_status='active'
               RETURNING account.user_id,account.public_id::text,account.email,account.display_name""",
            (_digest(token),),
        ).fetchone()
    return User(**row) if row else None


def revoke_session(token: str | None) -> None:
    if token:
        with _connect() as connection:
            connection.execute(
                "UPDATE auth_user_session SET revoked_at=clock_timestamp() WHERE token_digest=%s",
                (_digest(token),),
            )


def grant_campaign_owner(campaign_public_id: str, user_id: int) -> None:
    with _connect() as connection:
        connection.execute(
            """INSERT INTO auth_campaign_membership(campaign_id,user_id,membership_role)
               SELECT campaign_id,%s,'owner' FROM camp_campaign WHERE public_id=%s
               ON CONFLICT (campaign_id,user_id) DO NOTHING""",
            (user_id, campaign_public_id),
        )


def can_access_campaign(user_id: int, campaign_public_id: str) -> bool:
    with _connect() as connection:
        return connection.execute(
            """SELECT EXISTS(
               SELECT 1 FROM auth_campaign_membership membership
               JOIN camp_campaign campaign USING(campaign_id)
               WHERE membership.user_id=%s AND campaign.public_id=%s) AS allowed""",
            (user_id, campaign_public_id),
        ).fetchone()["allowed"]


def campaign_role(user_id: int, campaign_public_id: str) -> str | None:
    with _connect() as connection:
        row = connection.execute(
            """SELECT membership.membership_role FROM auth_campaign_membership membership
               JOIN camp_campaign campaign USING(campaign_id)
               WHERE membership.user_id=%s AND campaign.public_id=%s""",
            (user_id, campaign_public_id),
        ).fetchone()
    return row["membership_role"] if row else None


def create_invitation(campaign_public_id: str, owner_user_id: int, email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("A valid invitation email is required")
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=7)
    with _connect() as connection:
        campaign = connection.execute(
            """SELECT campaign.campaign_id FROM camp_campaign campaign
               JOIN auth_campaign_membership membership USING(campaign_id)
               WHERE campaign.public_id=%s AND membership.user_id=%s
                 AND membership.membership_role='owner'""",
            (campaign_public_id, owner_user_id),
        ).fetchone()
        if not campaign:
            raise PermissionError("Only the campaign owner may invite members")
        connection.execute(
            """INSERT INTO auth_campaign_invitation
               (campaign_id,invited_by_user_id,invited_email,invitation_digest,expires_at)
               VALUES(%s,%s,%s,%s,%s)""",
            (campaign["campaign_id"], owner_user_id, normalized, _digest(token), expires),
        )
    return token


def accept_invitation(token: str, user: User) -> str:
    with _connect() as connection:
        invitation = connection.execute(
            """SELECT invitation.invitation_id,invitation.campaign_id,
                      campaign.public_id::text AS campaign_public_id,
                      invitation.invited_email
               FROM auth_campaign_invitation invitation
               JOIN camp_campaign campaign USING(campaign_id)
               WHERE invitation.invitation_digest=%s AND invitation.revoked_at IS NULL
                 AND invitation.accepted_at IS NULL AND invitation.expires_at>clock_timestamp()
               FOR UPDATE""",
            (_digest(token),),
        ).fetchone()
        if not invitation or invitation["invited_email"] != user.email:
            raise ValueError("This invitation is invalid, expired, or belongs to another account")
        connection.execute(
            """INSERT INTO auth_campaign_membership(campaign_id,user_id,membership_role)
               VALUES(%s,%s,'member') ON CONFLICT (campaign_id,user_id) DO NOTHING""",
            (invitation["campaign_id"], user.user_id),
        )
        connection.execute(
            """UPDATE auth_campaign_invitation SET accepted_by_user_id=%s,
                      accepted_at=clock_timestamp() WHERE invitation_id=%s""",
            (user.user_id, invitation["invitation_id"]),
        )
    return invitation["campaign_public_id"]


def secure_cookie() -> bool:
    return os.environ.get("EMPOROS_COOKIE_SECURE", "false").lower() == "true"
