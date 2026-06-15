from __future__ import annotations

import os
import re

import requests
import streamlit as st

from auth.session import is_authenticated, store_auth

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net",
).rstrip("/")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _extract_error_message(payload: object) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("code") or "Registration failed.")
        if isinstance(detail, str):
            return detail
    return "Registration failed."


def _go_login() -> None:
    st.switch_page("pages/Login.py")


if is_authenticated():
    st.rerun()

st.title("Register")
st.caption("Create your account to use the authenticated valuation tools.")

flash = st.session_state.pop("auth_flash", "")
if flash:
    st.success(flash)

with st.form("register_form", clear_on_submit=False):
    username = st.text_input("Username", placeholder="your name")
    email = st.text_input("Email", placeholder="you@example.com")
    password = st.text_input("Password", type="password", help="Minimum 6 characters, max 128")
    confirm_password = st.text_input("Confirm Password", type="password")
    submitted = st.form_submit_button("Register", use_container_width=True)

if submitted:
    username_clean = username.strip()
    email_clean = email.strip()

    form_errors: list[str] = []
    if not username_clean:
        form_errors.append("Username cannot be empty.")
    if not email_clean:
        form_errors.append("Email cannot be empty.")
    elif not _EMAIL_RE.match(email_clean):
        form_errors.append("Please enter a valid email address (e.g. you@example.com).")
    if not password:
        form_errors.append("Password cannot be empty.")
    elif len(password) < 6:
        form_errors.append("Password must be at least 6 characters.")
    elif len(password) > 128:
        form_errors.append("Password must be 128 characters or fewer.")
    elif password != confirm_password:
        form_errors.append("Passwords do not match.")

    if form_errors:
        for msg in form_errors:
            st.error(msg)
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/register",
                json={
                    "username": username_clean,
                    "email": email_clean,
                    "password": password,
                },
                timeout=30,
            )
            payload = response.json()
        except requests.RequestException as exc:
            st.error("Could not reach the authentication server.")
            with st.expander("Error details"):
                st.code(str(exc), language="text")
        except ValueError:
            st.error("Authentication server returned an invalid response.")
        else:
            if response.ok:
                # Auto-login: call /auth/login immediately after successful registration
                try:
                    login_resp = requests.post(
                        f"{API_BASE_URL}/auth/login",
                        json={"email": email_clean, "password": password},
                        timeout=30,
                    )
                    login_payload = login_resp.json()
                except Exception:
                    login_payload = {}
                    login_resp = None

                if (
                    login_resp is not None
                    and login_resp.ok
                    and isinstance(login_payload, dict)
                    and login_payload.get("access_token")
                ):
                    store_auth(
                        token=login_payload["access_token"],
                        email=email_clean,
                        role=login_payload.get("role"),
                    )
                    st.session_state.auth_flash = "Welcome! Your account has been created."
                    st.switch_page("chatbot.py")
                else:
                    # Registration succeeded but auto-login failed — fall back to login page
                    st.session_state.auth_flash = "Registration successful. Please log in."
                    _go_login()
            else:
                st.error(_extract_error_message(payload))

if st.button("Back to Login", use_container_width=True):
    _go_login()
