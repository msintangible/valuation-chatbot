"""
Financial Intelligence Chatbot UI
==================================
Simple Streamlit interface for the Financial Intelligence Agent
"""

import os
import streamlit as st
import requests
from typing import Dict, Any
import re
from auth.session import get_user_id, require_auth

# Configuration
API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net",
).rstrip("/")
API_CHAT_PATH = os.getenv("API_CHAT_PATH", "/chat/")
API_CHAT_URL = f"{API_BASE_URL}/{API_CHAT_PATH.lstrip('/')}"

# ─────────────────────────────────────────────────────────────
# Helper Functions for Response Rendering
# ─────────────────────────────────────────────────────────────

def parse_valuation_data(response_text: str) -> Dict[str, Any]:
    """
    Extract valuation metrics from response text.
    Handles both single and multi-stock responses.
    Returns dict with single stock data or list of dicts for multiple stocks.
    """
    # Pattern for multi-stock responses: "**Valuation Result: TICKER**"
    multi_stock_pattern = r'\*\*Valuation Result:\s*([A-Z]{1,5})\*\*\n-\s*Prediction:\s*([^\n]+)\n-\s*Confidence:\s*([\d.]+)%\n-\s*Current Price.*\$([0-9.,]+).*Graham Value.*\$([0-9.,]+)'
    
    multi_matches = re.findall(multi_stock_pattern, response_text)
    
    if multi_matches:
        # Multi-stock response
        stocks = []
        for ticker, prediction, confidence, price, graham in multi_matches:
            stocks.append({
                'ticker': ticker.strip(),
                'prediction': prediction.strip(),
                'confidence': confidence + '%',
                'current_price': '$' + price,
                'graham_value': '$' + graham
            })
        return {'type': 'multi', 'stocks': stocks}
    
    # Single stock response - try multiple patterns
    data = {'type': 'single'}
    
    # Try pattern 1: "**Valuation**: Fair Value ("
    prediction_match = re.search(r'\*\*Valuation\*\*:\s*(\w+\s*\w*)\s*\(', response_text)
    
    # Try pattern 2: "Prediction: Fair Value" (from Valuation Result section)
    if not prediction_match:
        prediction_match = re.search(r'(?:Prediction|Valuation Result):\s*([^\n]+?)(?:\n|$)', response_text)
    
    if prediction_match:
        data['prediction'] = prediction_match.group(1).strip()
    
    # Extract confidence percentage
    confidence_match = re.search(r'Confidence:\s*([\d.]+)%', response_text)
    if confidence_match:
        data['confidence'] = confidence_match.group(1) + '%'
    
    # Extract price and graham value
    price_match = re.search(r'Current Price:\s*\$([0-9.,]+)', response_text)
    if price_match:
        data['current_price'] = '$' + price_match.group(1)
    
    graham_match = re.search(r'Graham Value:\s*\$([0-9.,]+)', response_text)
    if graham_match:
        data['graham_value'] = '$' + graham_match.group(1)
    
    return data


def extract_tickers(query: str) -> list[str]:
    """Extract stock ticker symbols from user query."""
    # Look for uppercase 1-5 letter words that look like tickers
    matches = re.findall(r'\b[A-Z]{1,5}\b', query)
    # Remove common words that aren't tickers
    common_words = {'HOW', 'WHAT', 'WHY', 'WHEN', 'WHERE', 'CAN', 'SHOULD', 'COULD', 'WILL', 'WITH', 'FOR', 'AND', 'THE', 'IS', 'ARE'}
    tickers = [t for t in matches if t not in common_words]
    return list(dict.fromkeys(tickers))  # Remove duplicates while preserving order


def display_ticker_chips(tickers: list[str]):
    """Display detected tickers as visual chips."""
    if not tickers:
        return
    
    # Create visual chips using columns
    st.markdown("**📊 Detected Tickers:**")
    cols = st.columns(len(tickers) + 1)  # +1 for spacing
    
    for i, ticker in enumerate(tickers):
        with cols[i]:
            st.write(f"🏷️ `{ticker}`")


def display_quick_actions(tickers: list[str]):
    """Display quick action buttons for common follow-ups."""
    st.markdown("---")
    st.markdown("**💡 Quick Actions:**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Analyze Portfolio", key="btn_portfolio"):
            st.session_state.messages.append({
                "role": "user",
                "content": "Analyze my portfolio risk"
            })
            st.rerun()
    
    with col2:
        if tickers and len(tickers) >= 1:
            action_text = f"📈 {tickers[0]} Details" if len(tickers) == 1 else "📈 Compare More"
            if st.button(action_text, key="btn_compare"):
                if len(tickers) == 1:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"Why is {tickers[0]} valued this way?"
                    })
                else:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": f"Explain factors for {', '.join(tickers[:2])}"
                    })
                st.rerun()
    
    with col3:
        if st.button("💰 Get Suggestions", key="btn_suggest"):
            st.session_state.messages.append({
                "role": "user",
                "content": "What stocks would you recommend?"
            })
            st.rerun()


def is_followup_memory_prompt(prompt: str, tickers: list[str]) -> bool:
    if tickers:
        return False
    normalized = prompt.strip().lower().rstrip("?.!")
    if normalized in {"explain more", "why", "go deeper", "deeper", "more detail", "tell me more"}:
        return True
    if "explain" in normalized and ("valuation" in normalized or "valution" in normalized):
        return True
    return False


def build_memory_followup_response() -> Dict[str, Any]:
    last_result = st.session_state.get("last_result")
    last_ticker = st.session_state.get("last_ticker")
    last_intent = st.session_state.get("last_intent")

    if not last_result:
        return {
            "response": "I need a previous stock analysis to explain further. Try 'Analyze AAPL'.",
            "next_best_action": "Run a stock analysis first (e.g., Analyze AAPL).",
            "tools_used": ["session_memory"],
            "errors": [],
            "recommendations": {"top_sectors": [], "suggested_tickers": []},
        }

    response_text = last_result.get("response", "")
    valuation = parse_valuation_data(response_text)
    ticker = last_ticker or "that stock"
    prediction = valuation.get("prediction", "the current valuation")
    confidence = valuation.get("confidence", "N/A")
    price = valuation.get("current_price", "Unavailable")
    graham = valuation.get("graham_value", "Unavailable")

    deeper = (
        f"🔍 **Deeper explanation for {ticker}**\n\n"
        f"- Current assessment: **{prediction}**\n"
        f"- Confidence: **{confidence}**\n"
        f"- Current Price: **{price}**\n"
        f"- Graham Value: **{graham}**\n\n"
        "What this means:\n"
        "- If the current price is far above Graham Value, the stock is likely overvalued.\n"
        "- If current price is below Graham Value, the stock may have upside potential.\n"
        "- Confidence shows how strongly the model supports this valuation view.\n\n"
        f"Context source: your previous **{last_intent or 'stock'}** result stored in session memory."
    )

    return {
        "response": deeper,
        "next_best_action": f"Ask for SHAP details or compare {ticker} with another stock.",
        "tools_used": ["session_memory"],
        "errors": [],
        "recommendations": {"top_sectors": [], "suggested_tickers": []},
    }


def render_backend_data_error(errors: list[dict]) -> None:
    first = errors[0] if errors else {}
    ticker = first.get("ticker") or "this stock"
    st.warning(
        f"⚠️ Unable to retrieve data for {ticker}. This may be due to:\n\n"
        "- Invalid ticker\n"
        "- Temporary API issue\n"
        "- Missing financial data\n\n"
        "Try again or use a different stock."
    )
    if st.button("🔄 Retry", key=f"retry_backend_error_{ticker}"):
        if st.session_state.get("last_prompt"):
            st.session_state.retry_prompt = st.session_state.last_prompt
        st.rerun()


def handle_error(error_type: str, error_msg: str, original_error: Exception = None):
    """
    Render user-friendly error message with retry button and details.
    
    Args:
        error_type: Type of error (timeout, connection, validation, api, unknown)
        error_msg: User-friendly error message
        original_error: Original exception for debug details
    """
    # Show friendly error message
    st.error(f"❌ {error_msg}")
    
    # Show helpful suggestions based on error type
    if error_type == "timeout":
        st.warning("""
        **Why this happened:**
        - The server is processing your request but taking too long
        - You can try again, or try a simpler query
        """)
    elif error_type == "connection":
        st.warning("""
        **Why this happened:**
        - The API server might be down or not responding
        - Check if the API service is running and reachable
        """)
    elif error_type == "validation":
        st.warning("""
        **Why this happened:**
        - Your query doesn't contain a valid stock ticker
        - Try including a stock symbol like: AAPL, TSLA, MSFT
        """)
    elif error_type == "api":
        st.warning("""
        **Why this happened:**
        - The API encountered an error processing your request
        - You can try again or try a different query
        """)
    
    # Add retry button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Retry Last Query"):
            if st.session_state.get("last_prompt"):
                st.session_state.retry_prompt = st.session_state.last_prompt
            st.rerun()
    
    with col2:
        if st.button("🗑️ Clear & Start Fresh"):
            st.session_state.messages = []
            st.rerun()
    
    # Show technical details in expander (for debugging)
    if original_error:
        with st.expander("🔍 Technical Details"):
            st.code(str(original_error), language="text")


def render_response(data: Dict[str, Any], tickers: list[str] = None, show_quick_actions: bool = True):
    """
    Render API response with structured UI components.
    Handles both single and multi-stock responses.
    
    Args:
        data: API response data
        tickers: List of detected tickers for quick actions
        show_quick_actions: Whether to display quick action buttons (only for latest message)
    """
    response_text = data.get("response", "")
    next_action = data.get("next_best_action", "")
    tools_used = data.get("tools_used", [])
    errors = data.get("errors", [])
    tickers = tickers or []

    if errors:
        render_backend_data_error(errors)
        st.markdown(response_text)
        if next_action:
            st.info(f"💡 **Suggestion:** {next_action}")
        return
    
    # Parse valuation data if present
    valuation = parse_valuation_data(response_text)
    
    # ─────────────────────────────────────────────────────────
    # 1. VALUATION METRICS (handles single and multi-stock)
    # Only show if we actually found metrics
    # ─────────────────────────────────────────────────────────
    has_metrics = False
    
    if valuation.get('type') == 'multi' and valuation.get('stocks'):
        # Multi-stock comparison view
        has_metrics = True
        stocks = valuation['stocks']
        for stock in stocks:
            st.markdown(f"### 📊 {stock['ticker']}")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Prediction", stock['prediction'])
            with col2:
                st.metric("Confidence", stock['confidence'])
            with col3:
                st.metric("Current Price", stock['current_price'])
            
            st.divider()
    
    elif valuation.get('type') == 'single' and (valuation.get('prediction') or valuation.get('confidence')):
        # Single stock view - only show if we have actual data
        has_metrics = True
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Prediction", valuation.get('prediction', 'N/A'), delta=None)
        with col2:
            st.metric("🎯 Confidence", valuation.get('confidence', 'N/A'))
        with col3:
            if valuation.get('current_price'):
                st.metric("💰 Current Price", valuation.get('current_price', 'N/A'))
    
    # ─────────────────────────────────────────────────────────
    # 2. FULL RESPONSE (formatted text)
    # ─────────────────────────────────────────────────────────
    st.markdown(response_text)
    
    # ─────────────────────────────────────────────────────────
    # 3. GRAHAM VALUE CONTEXT (only if we have metrics)
    # ─────────────────────────────────────────────────────────
    if valuation.get('type') == 'multi' and valuation.get('stocks'):
        # Multi-stock Graham analysis
        with st.expander("📈 Graham Value Analysis"):
            for stock in valuation['stocks']:
                st.markdown(f"""
                **{stock['ticker']}**
                - Current Price: {stock['current_price']}
                - Graham Value: {stock['graham_value']}
                """)
    elif valuation.get('graham_value') and valuation.get('current_price'):
        # Single stock Graham analysis
        with st.expander("📈 Graham Value Analysis"):
            st.markdown(f"""
            **Current Price:** {valuation.get('current_price')}
            
            **Graham Intrinsic Value:** {valuation.get('graham_value')}
            
            The Graham Number is a fundamental analysis metric that helps identify 
            if a stock is trading at a fair price relative to its intrinsic value.
            """)
    
    # ─────────────────────────────────────────────────────────
    # 4. NEXT ACTION (highlighted)
    # ─────────────────────────────────────────────────────────
    if next_action:
        st.info(f"💡 **Suggestion:** {next_action}")
    
    # ─────────────────────────────────────────────────────────
    # 5. TOOLS USED (metadata, collapsible)
    # ─────────────────────────────────────────────────────────
    if tools_used:
        with st.expander("🔧 Tools Used"):
            st.markdown("**Endpoints called:**")
            for tool in tools_used:
                st.caption(f"✓ {tool}")

def render():
    """Render the chatbot page UI."""
    require_auth()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "debug_mode" not in st.session_state:
        st.session_state.debug_mode = False
    if "last_result" not in st.session_state:
        st.session_state.last_result = None
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = None
    if "last_intent" not in st.session_state:
        st.session_state.last_intent = None
    if "last_prompt" not in st.session_state:
        st.session_state.last_prompt = None
    if "retry_prompt" not in st.session_state:
        st.session_state.retry_prompt = None

    st.title("💰 Financial Intelligence Chatbot")
    st.markdown("Ask about stock valuations, finance metrics/indicators, portfolio analysis, and personalized recommendations.")
    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                if message.get("full_data"):
                    render_response(message["full_data"], message.get("tickers", []), show_quick_actions=False)
                else:
                    st.markdown(message["content"])
            else:
                st.markdown(message["content"])

    def process_message(prompt: str, display_output: bool = True):
        """Process a user query and get API response. Can be called from chat input or quick actions."""
        st.session_state.last_prompt = prompt

        if display_output:
            with st.chat_message("user"):
                st.markdown(prompt)

        with st.chat_message("assistant"):
            status_container = st.empty()
            tickers = extract_tickers(prompt)
            api_query = prompt

            try:
                if is_followup_memory_prompt(prompt, tickers):
                    last_ticker = st.session_state.get("last_ticker")
                    if last_ticker:
                        api_query = f"{prompt} for {last_ticker}"
                        tickers = [last_ticker]

                with status_container.container():
                    st.info("🔍 Analyzing query...")

                display_ticker_chips(tickers)

                with status_container.container():
                    st.info("📡 Fetching market data...")

                payload = {
                    "user_id": get_user_id(),
                    "query": api_query
                }

                if st.session_state.debug_mode:
                    st.write("📤 Sending:", payload)

                response = None
                for attempt in range(2):
                    try:
                        response = requests.post(
                            API_CHAT_URL,
                            json=payload,
                            timeout=60
                        )
                        break
                    except requests.exceptions.Timeout:
                        if attempt == 0:
                            continue
                        raise

                if st.session_state.debug_mode:
                    st.write("📥 Status:", response.status_code)
                    st.write("📥 URL:", response.url)
                    st.write("📥 Raw response:", response.text)

                with status_container.container():
                    st.info("🧠 Generating insights...")

                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError as e:
                    raise ValueError(f"Invalid JSON response: {response.text}") from e

                if st.session_state.debug_mode:
                    st.write("📥 Parsed:", data)

                status_container.empty()
                render_response(data, tickers)

                if not data.get("errors"):
                    st.session_state.last_result = data
                    st.session_state.last_ticker = tickers[0] if tickers else st.session_state.get("last_ticker")
                    used_tools = data.get("tools_used", [])
                    if "stock_valuation" in used_tools:
                        st.session_state.last_intent = "stock_valuation"
                    elif "shap_explain" in used_tools:
                        st.session_state.last_intent = "explanation"
                    else:
                        st.session_state.last_intent = "general"

                assistant_message = data.get("response", "No response received.")
                next_action = data.get("next_best_action", "")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_message,
                    "next_action": next_action,
                    "tickers": tickers,
                    "full_data": data
                })

            except requests.exceptions.Timeout as e:
                handle_error(
                    "timeout",
                    "Request timed out. The server took too long to respond.",
                    e
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Request timed out. Please try again.",
                    "next_action": None
                })

            except requests.exceptions.ConnectionError as e:
                handle_error(
                    "connection",
                    "Could not connect to the API server.",
                    e
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Connection failed. Please check if server is running.",
                    "next_action": None
                })

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                if status_code == 400:
                    error_type = "validation"
                    friendly_msg = "Invalid request. Please check your input."
                else:
                    error_type = "api"
                    friendly_msg = f"API error (Code {status_code}). Please try again."

                handle_error(error_type, friendly_msg, e)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": friendly_msg,
                    "next_action": None
                })

            except ValueError as e:
                handle_error(
                    "response",
                    "API returned an invalid response format.",
                    e
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "API returned an invalid response.",
                    "next_action": None
                })

            except Exception as e:
                handle_error(
                    "unknown",
                    "Something unexpected happened. Please try again.",
                    e
                )
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "An unexpected error occurred.",
                    "next_action": None
                })

    prompt = None
    unprocessed = None

    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user" and i == len(st.session_state.messages) - 1:
            if i + 1 >= len(st.session_state.messages) or st.session_state.messages[i + 1]["role"] != "assistant":
                unprocessed = msg["content"]
                break

    chat_input = st.chat_input("Ask about metrics (P/E, ROE), valuations, portfolios, or recommendations...")

    if st.session_state.retry_prompt:
        prompt = st.session_state.retry_prompt
        st.session_state.retry_prompt = None
        display_output = False
    elif unprocessed:
        prompt = unprocessed
        display_output = False
    elif chat_input:
        st.session_state.messages.append({"role": "user", "content": chat_input})
        prompt = chat_input
        display_output = True

    if prompt:
        process_message(prompt, display_output=display_output)

    if st.session_state.messages:
        last_message = st.session_state.messages[-1]
        if last_message["role"] == "assistant" and last_message.get("tickers"):
            st.markdown("---")
            st.markdown("**💡 Quick Actions:**")

            col1, col2, col3 = st.columns(3)
            tickers = last_message.get("tickers", [])

            with col1:
                if st.button("📊 Analyze Portfolio", key="quick_analyze"):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "Analyze my portfolio risk"
                    })
                    st.rerun()

            with col2:
                if tickers and len(tickers) >= 1:
                    action_text = f"📈 {tickers[0]} Details" if len(tickers) == 1 else "📈 Compare More"
                    if st.button(action_text, key="quick_details"):
                        if len(tickers) == 1:
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Why is {tickers[0]} valued this way?"
                            })
                        else:
                            st.session_state.messages.append({
                                "role": "user",
                                "content": f"Explain factors for {', '.join(tickers[:2])}"
                            })
                        st.rerun()

            with col3:
                if st.button("💰 Get Suggestions", key="quick_suggest"):
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "What stocks would you recommend?"
                    })
                    st.rerun()

    with st.sidebar:
        st.caption(f"Current user ID: {get_user_id()}")
        st.divider()
        st.session_state.debug_mode = st.toggle("🐞 Debug Mode", value=st.session_state.debug_mode)
        st.divider()

        st.header("ℹ️ About")
        st.markdown("""
        This chatbot uses AI to help you with:
        - **Stock Valuations** - Check if stocks are under/over valued
        - **Finance Metrics** - Understand indicators like P/E, ROE, EPS, EBITDA, RSI
        - **Explanations** - Understand why a stock is valued a certain way
        - **Portfolio Analysis** - Analyze your portfolio risk
        - **Recommendations** - Get personalized stock suggestions
        """)

        st.divider()
        st.header("📝 Examples")
        st.markdown("""
        Try asking:
        - "What's the valuation for AAPL?"
        - "What does ROE tell me?"
        - "How do I interpret P/E ratio?"
        - "Why is TSLA overvalued?"
        - "Suggest some stocks for me"
        - "Analyze my portfolio risk"
        """)

        st.divider()
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.rerun()

        st.caption(f"Connected to: {API_BASE_URL}")
        st.caption(f"User ID: {get_user_id()}")
