import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
from auth.session import get_email, get_role, get_user_id, logout, is_authenticated

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net",
).rstrip("/")

st.set_page_config(page_title="Financial Intelligence App", page_icon="💼", layout="centered")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

def handle_logout():
    logout()
    st.session_state.auth_flash = "You have been logged out."
    st.rerun()

def queue_chat_prompt(prompt: str):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.switch_page(chatbot_page)

def show_home():
    st.title("💰 Financial Intelligence App")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Go to Chatbot", use_container_width=True):
            st.switch_page(chatbot_page)
    with col2:
        if st.button("📂 Manage Portfolio", use_container_width=True):
            st.switch_page(portfolio_page)

    st.subheader("🔍 Quick Stock Check")
    with st.form("quick_check_form", clear_on_submit=False):
        ticker = st.text_input("Enter ticker (e.g. AAPL)", key="quick_check_ticker")
        submitted = st.form_submit_button("Analyze", type="primary", use_container_width=True)
        
    if submitted:
        cleaned_ticker = ticker.strip().upper()
        if not cleaned_ticker:
            st.error("Please enter a ticker symbol.")
        else:
            with st.spinner(f"Analyzing {cleaned_ticker}..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/predict/",
                        json={"ticker": cleaned_ticker, "user_id": get_user_id()},
                        timeout=30,
                    )
                    response.raise_for_status()
                    result = response.json()
                    st.success(f"Analysis complete for {cleaned_ticker}.")

                    label = result.get("label", "N/A")
                    confidence = result.get("confidence")
                    current_price = result.get("current_price")
                    graham_value = result.get("graham_value")

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        st.metric("Prediction", label)
                    with c2:
                        conf_text = f"{confidence:.1%}" if isinstance(confidence, (int, float)) else "N/A"
                        st.metric("Confidence", conf_text)
                    with c3:
                        price_text = f"${current_price:.2f}" if isinstance(current_price, (int, float)) else "N/A"
                        st.metric("Current Price", price_text)

                    if isinstance(graham_value, (int, float)):
                        st.write(f"**Graham Value:** ${graham_value:.2f}")
                except Exception as e:
                    st.error("Could not analyze this ticker right now.")
                    with st.expander("Error details"):
                        st.code(str(e), language="text")

    st.subheader("💡 Try these")
    examples = [
        "Why is TSLA overvalued?",
        "Analyze AAPL",
        "Suggest stocks for growth",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            queue_chat_prompt(example)

    with st.expander("🧠 What this app does"):
        st.write(
            """
            - Analyze stock valuations using AI
            - Explain why stocks are over/under valued
            - Manage and analyze portfolios
            - Provide investment insights
            """
        )

def show_dashboard():
    st.title("📊 System Dashboard")
    st.subheader("How the AI System Works")

    flow_cols = st.columns(5)
    flow_steps = [
        ("🧑‍💻", "User Input", "Asks about stocks or portfolio"),
        ("🤖", "AI Agent", "Detects intent and context"),
        ("🛠️", "Tools", "Calls FastAPI prediction tools"),
        ("🧠", "Analysis", "Runs XGBoost + SHAP logic"),
        ("📬", "Response", "Returns structured insights"),
    ]
    for col, (icon, title, desc) in zip(flow_cols, flow_steps):
        with col:
            st.markdown(f"### {icon}")
            st.markdown(f"**{title}**")
            st.caption(desc)

    st.divider()
    st.markdown("**⚙️ System Components**")
    components_df = pd.DataFrame(
        {
            "Component": ["LLM Agent", "FastAPI Layer", "XGBoost + SHAP", "Database", "Streamlit UI"],
            "Load": [10, 25, 40, 10, 5],
        }
    )
    components_fig = px.bar(components_df, x="Component", y="Load", title="System Components")
    st.plotly_chart(components_fig, use_container_width=True)

    st.markdown("**🔄 Data Flow Across Stages**")
    data_flow_df = pd.DataFrame(
        {
            "Stage": ["Input", "Processing", "Tool Calls", "Aggregation", "Output"],
            "Data Volume": [100, 82, 76, 54, 38],
        }
    )
    data_flow_fig = px.line(data_flow_df, x="Stage", y="Data Volume", title="System Workflow")
    st.plotly_chart(data_flow_fig, use_container_width=True)

    st.markdown("**📈 Model Insight: Feature Importance**")
    feature_df = pd.DataFrame(
        {
            "Feature": ["PE Ratio", "ROE", "Debt/Equity", "Momentum", "Revenue Growth"],
            "Importance": [0.28, 0.22, 0.16, 0.18, 0.16],
        }
    )
    feature_fig = px.bar(feature_df, x="Feature", y="Importance", title="What Drives Stock Valuation")
    st.plotly_chart(feature_fig, use_container_width=True)

def show_portfolio():
    import portfolio
    portfolio.render()

def show_chatbot():
    import chatbot
    chatbot.render()

def show_admin():
    from pages import Admin
    Admin.render()

# Define Pages
home_page = st.Page(show_home, title="Home", icon="🏠")
dashboard_page = st.Page(show_dashboard, title="Dashboard", icon="📊")
portfolio_page = st.Page(show_portfolio, title="Portfolio", icon="📂")
chatbot_page = st.Page(show_chatbot, title="Chatbot", icon="💬")
admin_page = st.Page(show_admin, title="Admin Panel", icon="🛡️")
logout_page = st.Page(handle_logout, title="Logout", icon="🚪")

login_page = st.Page("pages/Login.py", title="Login", icon="🔐")
register_page = st.Page("pages/Register.py", title="Register", icon="📝")

# Navigation logic
if is_authenticated():
    tools_pages = [home_page, portfolio_page, dashboard_page, chatbot_page]
    if get_role() == "admin":
        tools_pages.append(admin_page)
        
    pg = st.navigation({
        "Tools": tools_pages,
        "Account": [logout_page]
    })
    
    # Render user info in sidebar
    with st.sidebar:
        st.caption(f"Logged in as: {get_email()}")
        st.caption(f"Role: {get_role()}")
        st.divider()
else:
    # No page config here to let Login/Register handle it if they want, 
    # but st.navigation usually needs one.
    pg = st.navigation([login_page, register_page])

pg.run()

