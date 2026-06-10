from __future__ import annotations

from typing import Any

import streamlit as st
from jose import jwt


AUTH_TOKEN_KEY = "auth_token"
AUTH_EMAIL_KEY = "auth_email"
AUTH_ROLE_KEY = "auth_role"
AUTH_USER_ID_KEY = "auth_user_id"


def is_authenticated() -> bool:
    return bool(str(st.session_state.get(AUTH_TOKEN_KEY, "")).strip())


def get_token() -> str:
    return str(st.session_state.get(AUTH_TOKEN_KEY, "")).strip()


def get_email() -> str:
    return str(st.session_state.get(AUTH_EMAIL_KEY, "")).strip()


def get_role() -> str:
    return str(st.session_state.get(AUTH_ROLE_KEY, "")).strip()


def get_user_id() -> str:
    return str(st.session_state.get(AUTH_USER_ID_KEY, "")).strip()


def store_auth(token: str, email: str, role: str | None = None, user_id: str | None = None) -> None:
    claims = _decode_unverified_claims(token)
    resolved_user_id = (user_id or claims.get("sub") or "").strip()
    resolved_role = (role or claims.get("role") or "user").strip()

    st.session_state[AUTH_TOKEN_KEY] = token
    st.session_state[AUTH_EMAIL_KEY] = email.strip()
    st.session_state[AUTH_ROLE_KEY] = resolved_role
    st.session_state[AUTH_USER_ID_KEY] = resolved_user_id
    st.session_state["user_id"] = resolved_user_id


def logout() -> None:
    for key in (AUTH_TOKEN_KEY, AUTH_EMAIL_KEY, AUTH_ROLE_KEY, AUTH_USER_ID_KEY, "user_id"):
        st.session_state.pop(key, None)


def require_auth() -> None:
    if not is_authenticated():
        st.switch_page("pages/Login.py")
        st.stop()


def _decode_unverified_claims(token: str) -> dict[str, Any]:
    try:
        claims = jwt.get_unverified_claims(token)
        return claims if isinstance(claims, dict) else {}
    except Exception:
        return {}
