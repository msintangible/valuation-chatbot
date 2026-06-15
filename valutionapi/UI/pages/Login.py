from __future__ import annotations

import os
import re

import requests
import streamlit as st

from auth.session import is_authenticated, store_auth

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net",
).rstrip("/")


_ERROR_CODE_MESSAGES: dict[str, str] = {
    "email_not_registered": "No account found with this email address. Please register first.",
    "incorrect_password": "Incorrect password. Please try again.",
    "account_inactive": "This account has been deactivated. Please contact support.",
    "password_not_set": "This account was created without a password. Please re-register.",
}


def _extract_error_message(payload: object) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, dict):
            code = detail.get("code", "")
            if code in _ERROR_CODE_MESSAGES:
                return _ERROR_CODE_MESSAGES[code]
            return str(detail.get("message") or code or "Login failed.")
        if isinstance(detail, str):
            return detail
    return "Login failed."


def _go_register() -> None:
    st.switch_page("pages/Register.py")


def _go_home() -> None:
    st.switch_page("chatbot.py")

if is_authenticated():
    _go_home()

st.title("Login")
st.caption("Sign in to access the valuation dashboard, portfolio tools, and chatbot.")

flash = st.session_state.pop("auth_flash", "")
if flash:
    st.success(flash)

with st.form("login_form", clear_on_submit=False):
    email = st.text_input("Email", placeholder="you@example.com")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login", use_container_width=True)

if submitted:
    email_clean = email.strip()
    if not email_clean:
        st.error("Email cannot be empty.")
    elif not _EMAIL_RE.match(email_clean):
        st.error("Please enter a valid email address (e.g. you@example.com).")
    elif not password:
        st.error("Password cannot be empty.")
    elif len(password) < 6:
        st.error("Password must be at least 6 characters.")
    else:
        try:
            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json={"email": email_clean, "password": password},
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
            if response.ok and isinstance(payload, dict) and payload.get("access_token"):
                token = payload["access_token"]
                store_auth(token=token, email=email_clean, role=payload.get("role"))
                st.session_state.auth_flash = "Logged in successfully."
                _go_home()
            else:
                st.error(_extract_error_message(payload))

