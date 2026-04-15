import streamlit as st


st.set_page_config(
    page_title="Financial Intelligence App",
    page_icon="💼",
    layout="centered",
)

if "page" not in st.session_state:
    st.session_state.page = "home"


def go_home():
    st.session_state.page = "home"


def go_chat():
    st.session_state.page = "chat"


def go_portfolio():
    st.session_state.page = "portfolio"


with st.sidebar:
    st.header("Navigation")
    st.button("Home", on_click=go_home, use_container_width=True)
    st.button("Chatbot", on_click=go_chat, use_container_width=True)
    st.button("Portfolio Manager", on_click=go_portfolio, use_container_width=True)
    st.divider()


if st.session_state.page == "home":
    st.title("🏠 Home")
    st.markdown("Welcome to the Financial Intelligence App.")
    st.info("Use the sidebar to open the Chatbot or Portfolio Manager.")
elif st.session_state.page == "chat":
    import chatbot

    chatbot.render()
elif st.session_state.page == "portfolio":
    import portfolio

    portfolio.render()
else:
    st.session_state.page = "home"
    st.rerun()
