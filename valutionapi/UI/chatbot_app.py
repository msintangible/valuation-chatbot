"""
Financial Intelligence Chatbot UI
==================================
Simple Streamlit interface for the Financial Intelligence Agent
"""

import streamlit as st
import requests
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8001"
USER_ID = "3"

# Page configuration
st.set_page_config(
    page_title="Financial Intelligence Chatbot",
    page_icon="💰",
    layout="centered"
)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Header
st.title("💰 Financial Intelligence Chatbot")
st.markdown("Ask about stock valuations, portfolio analysis, and get personalized recommendations.")
st.divider()

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Display next_best_action if available
        if message["role"] == "assistant" and message.get("next_action"):
            st.info(f"💡 **Next:** {message['next_action']}")

# Chat input
if prompt := st.chat_input("Ask about stocks, portfolios, or get recommendations..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Call API and get response
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Send request to backend API
                payload = {
                    "user_id": USER_ID,
                    "query": prompt
                }

                st.write("📤 Sending:", payload)

                response = requests.post(
                    f"{API_BASE_URL}/chat/",
                    json=payload,
                    timeout=60
                )

                st.write("📥 Raw response:", response.text)

                data = response.json()
                st.write("📥 Parsed:", data)
                
                # Extract response fields
                assistant_message = data.get("response", "No response received.")
                next_action = data.get("next_best_action", "")
                
                # Display response
                st.markdown(assistant_message)
                
                # Display next action if available
                if next_action:
                    st.info(f"💡 **Next:** {next_action}")
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_message,
                    "next_action": next_action
                })
                
            except requests.exceptions.Timeout:
                error_msg = "⚠️ Request timed out. The server took too long to respond."
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "next_action": None
                })
                
            except requests.exceptions.ConnectionError:
                error_msg = "⚠️ Could not connect to the API. Make sure the server is running on http://localhost:8001"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "next_action": None
                })
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"⚠️ API error: {e.response.status_code} - {e.response.text}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "next_action": None
                })
                
            except Exception as e:
                error_msg = f"⚠️ Unexpected error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg,
                    "next_action": None
                })

# Sidebar with info
with st.sidebar:
    st.header("ℹ️ About")
    st.markdown("""
    This chatbot uses AI to help you with:
    - **Stock Valuations** - Check if stocks are under/over valued
    - **Explanations** - Understand why a stock is valued a certain way
    - **Portfolio Analysis** - Analyze your portfolio risk
    - **Recommendations** - Get personalized stock suggestions
    """)
    
    st.divider()
    
    st.header("📝 Examples")
    st.markdown("""
    Try asking:
    - "What's the valuation for AAPL?"
    - "Why is TSLA overvalued?"
    - "Suggest some stocks for me"
    - "Analyze my portfolio risk"
    """)
    
    st.divider()
    
    # Clear chat button
    if st.button("🗑️ Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    st.caption(f"Connected to: {API_BASE_URL}")
    st.caption(f"User ID: {USER_ID}")
