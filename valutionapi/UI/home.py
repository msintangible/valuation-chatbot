import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import uuid


API_BASE_URL = "http://localhost:8001"
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

USER_ID = st.session_state.user_id


st.set_page_config(
    page_title="Financial Intelligence App",
    page_icon="💼",
    layout="centered",
)

if "page" not in st.session_state:
    st.session_state.page = "home"
if "messages" not in st.session_state:
    st.session_state.messages = []


def go_home():
    st.session_state.page = "home"


def go_chat():
    st.session_state.page = "chat"


def go_portfolio():
    st.session_state.page = "portfolio"


def queue_chat_prompt(prompt: str):
    st.session_state.page = "chat"
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()


with st.sidebar:
    st.header("Navigation")
    st.button("Home", on_click=go_home, use_container_width=True)
    st.button("Chatbot", on_click=go_chat, use_container_width=True)
    st.button("Portfolio Manager", on_click=go_portfolio, use_container_width=True)
    st.divider()


if st.session_state.page == "home":
    st.title("💰 Financial Intelligence App")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 Go to Chatbot", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
    with col2:
        if st.button("📂 Manage Portfolio", use_container_width=True):
            st.session_state.page = "portfolio"
            st.rerun()

    st.subheader("🔍 Quick Stock Check")
    ticker = st.text_input("Enter ticker (e.g. AAPL)", key="quick_check_ticker")
    if st.button("Analyze", type="primary", use_container_width=True):
        cleaned_ticker = ticker.strip().upper()
        if not cleaned_ticker:
            st.error("Please enter a ticker symbol.")
        else:
            with st.spinner(f"Analyzing {cleaned_ticker}..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/predict/",
                        json={"ticker": cleaned_ticker, "user_id": USER_ID},
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

    st.divider()
    st.subheader("📊 How the AI System Works")

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

    st.markdown("**⚙️ System Components**")
    components_df = pd.DataFrame(
        {
            "Component": ["LLM Agent", "FastAPI Layer", "XGBoost + SHAP", "Database", "Streamlit UI"],
            "Load": [10, 25, 40, 10, 5],
        }
    )
    if components_df.empty:
        st.info("No data available to display chart")
    else:
        components_fig = px.bar(
            components_df,
            x="Component",
            y="Load",
            title="System Components",
        )
        st.plotly_chart(components_fig, use_container_width=True)

    st.markdown("**🔄 Data Flow Across Stages**")
    data_flow_df = pd.DataFrame(
        {
            "Stage": ["Input", "Processing", "Tool Calls", "Aggregation", "Output"],
            "Data Volume": [100, 82, 76, 54, 38],
        }
    )
    if data_flow_df.empty:
        st.info("No data available to display chart")
    else:
        data_flow_fig = px.line(
            data_flow_df,
            x="Stage",
            y="Data Volume",
            title="System Workflow",
        )
        st.plotly_chart(data_flow_fig, use_container_width=True)

    st.markdown("**📈 Model Insight: Feature Importance**")
    feature_df = pd.DataFrame(
        {
            "Feature": ["PE Ratio", "ROE", "Debt/Equity", "Momentum", "Revenue Growth"],
            "Importance": [0.28, 0.22, 0.16, 0.18, 0.16],
        }
    )
    if feature_df.empty:
        st.info("No data available to display chart")
    else:
        feature_fig = px.bar(
            feature_df,
            x="Feature",
            y="Importance",
            title="What Drives Stock Valuation",
        )
        st.plotly_chart(feature_fig, use_container_width=True)

    st.markdown(
        "User input is processed by an AI agent which determines intent and dynamically calls backend tools "
        "such as FastAPI valuation endpoints, XGBoost model inference, SHAP explainability, and portfolio APIs. "
        "The results are aggregated and returned as structured insights."
    )

    with st.expander("🧠 What this app does"):
        st.write(
            """
            - Analyze stock valuations using AI
            - Explain why stocks are over/under valued
            - Manage and analyze portfolios
            - Provide investment insights
            """
        )

elif st.session_state.page == "chat":
    import chatbot

    chatbot.render()
elif st.session_state.page == "portfolio":
    import portfolio

    portfolio.render()
else:
    st.session_state.page = "home"
    st.rerun()
