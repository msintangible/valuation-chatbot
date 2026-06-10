from __future__ import annotations

import os

import requests
import streamlit as st

from auth.session import is_authenticated

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")


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
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    submitted = st.form_submit_button("Register", use_container_width=True)

if submitted:
    username_clean = username.strip()
    email_clean = email.strip()
    if not username_clean:
        st.error("Username cannot be empty.")
    if not email_clean:
        st.error("Email cannot be empty.")
    elif not password:
        st.error("Password cannot be empty.")
    elif password != confirm_password:
        st.error("Passwords must match.")
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
                st.session_state.auth_flash = "Registration successful. Please log in."
                _go_login()
            else:
                st.error(_extract_error_message(payload))

if st.button("Back to Login", use_container_width=True):
    _go_login()
