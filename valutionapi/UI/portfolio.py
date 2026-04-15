import streamlit as st


def render():
    st.title("📂 Portfolio Management")

    if "portfolios" not in st.session_state:
        st.session_state.portfolios = {}

    st.subheader("Current Portfolios")
    st.json(st.session_state.portfolios)
