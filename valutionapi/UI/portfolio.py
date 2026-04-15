import requests
import streamlit as st


API_BASE_URL = "http://localhost:8001"
USER_ID = "2"


def show_api_error(message: str, error: Exception) -> None:
    st.error(message)
    with st.expander("Error details"):
        st.code(str(error), language="text")


def load_portfolios() -> None:
    with st.spinner("Loading portfolios..."):
        try:
            response = requests.get(f"{API_BASE_URL}/predict/portfolio/{USER_ID}", timeout=30)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, list):
                st.session_state.portfolio_list = data
            elif isinstance(data, dict) and isinstance(data.get("portfolios"), list):
                st.session_state.portfolio_list = data["portfolios"]
            else:
                st.session_state.portfolio_list = []
        except Exception as e:
            show_api_error("Could not load portfolios.", e)
            st.session_state.portfolio_list = []


def load_portfolio_details(name: str) -> dict | None:
    with st.spinner("Loading portfolio details..."):
        try:
            response = requests.get(f"{API_BASE_URL}/predict/portfolio/{USER_ID}/{name}", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            show_api_error("Could not load portfolio details.", e)
            return None


def render():
    st.title("📂 Portfolio Management")

    if "portfolio_list" not in st.session_state:
        st.session_state.portfolio_list = []
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Create Portfolio
    st.subheader("Create Portfolio")
    new_portfolio_name = st.text_input("Portfolio Name", key="new_portfolio_name")
    if st.button("Create Portfolio", use_container_width=True):
        if not new_portfolio_name.strip():
            st.error("Please enter a portfolio name.")
        else:
            with st.spinner("Creating portfolio..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/predict/portfolio/create",
                        json={"user_id": USER_ID, "name": new_portfolio_name.strip()},
                        timeout=30,
                    )
                    response.raise_for_status()
                    st.success(f"Portfolio '{new_portfolio_name.strip()}' created.")
                    load_portfolios()
                except Exception as e:
                    show_api_error("Could not create portfolio.", e)

    # Select Portfolio
    st.subheader("Select Portfolio")
    load_portfolios()
    portfolio_names = [
        p.get("name", "")
        for p in st.session_state.portfolio_list
        if isinstance(p, dict) and p.get("name")
    ]
    if not portfolio_names:
        st.info("No portfolios found. Create one to continue.")
        return

    selected_portfolio = st.selectbox("Select Portfolio", options=portfolio_names, key="selected_portfolio")

    # Portfolio Details
    st.subheader("Portfolio Details")
    details = load_portfolio_details(selected_portfolio)
    if not details:
        return

    st.write(f"**Name:** {details.get('name', selected_portfolio)}")
    st.write(f"**Risk Label:** {details.get('risk_label', 'N/A')}")
    st.write(f"**Risk Score:** {details.get('risk_score', 'N/A')}")

    # Holdings
    st.subheader("Holdings")
    col1, col2 = st.columns(2)
    with col1:
        ticker_input = st.text_input("Ticker", key="add_ticker_input")
    with col2:
        shares_input = st.number_input("Shares", min_value=0.0, value=1.0, step=1.0, key="add_shares_input")

    if st.button("Add Ticker", use_container_width=True):
        if not ticker_input.strip():
            st.error("Please enter a ticker symbol.")
        else:
            with st.spinner("Adding ticker..."):
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/predict/portfolio/{USER_ID}/{selected_portfolio}/add",
                        json={"ticker": ticker_input.strip().upper(), "shares": float(shares_input)},
                        timeout=30,
                    )
                    response.raise_for_status()
                    st.success(f"Added {ticker_input.strip().upper()} to {selected_portfolio}.")
                    st.rerun()
                except Exception as e:
                    show_api_error("Could not add ticker.", e)

    holdings = details.get("holdings", [])
    if holdings:
        for idx, holding in enumerate(holdings):
            ticker = holding.get("ticker", "Unknown") if isinstance(holding, dict) else str(holding)
            row_col1, row_col2 = st.columns([4, 1])
            with row_col1:
                st.write(f"- {ticker}")
            with row_col2:
                if st.button("Remove", key=f"remove_{selected_portfolio}_{ticker}_{idx}"):
                    with st.spinner(f"Removing {ticker}..."):
                        try:
                            response = requests.delete(
                                f"{API_BASE_URL}/predict/portfolio/{USER_ID}/{selected_portfolio}/{ticker}",
                                timeout=30,
                            )
                            response.raise_for_status()
                            st.success(f"Removed {ticker} from {selected_portfolio}.")
                            st.rerun()
                        except Exception as e:
                            show_api_error(f"Could not remove {ticker}.", e)
    else:
        st.caption("No holdings in this portfolio yet.")

    # Actions
    st.subheader("Actions")
    action_col1, action_col2 = st.columns(2)

    with action_col1:
        if st.button("Delete Portfolio", type="secondary", use_container_width=True):
            with st.spinner("Deleting portfolio..."):
                try:
                    response = requests.delete(
                        f"{API_BASE_URL}/predict/portfolio/{USER_ID}/{selected_portfolio}",
                        timeout=30,
                    )
                    response.raise_for_status()
                    st.success(f"Deleted portfolio '{selected_portfolio}'.")
                    load_portfolios()
                    st.rerun()
                except Exception as e:
                    show_api_error("Could not delete portfolio.", e)

    with action_col2:
        if st.button("Analyze Portfolio", type="primary", use_container_width=True):
            st.session_state.page = "chat"
            st.session_state.messages.append(
                {"role": "user", "content": f"Analyze portfolio {selected_portfolio}"}
            )
            st.rerun()
