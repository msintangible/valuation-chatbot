import os
import requests
import streamlit as st
import pandas as pd
from auth.session import get_token, get_role, require_auth

API_BASE_URL = os.getenv(
    "API_BASE_URL",
    "https://valuationchatbot-exfsfyf6cta5gpek.germanywestcentral-01.azurewebsites.net",
).rstrip("/")

def render():
    require_auth()
    
    if get_role() != "admin":
        st.error("Access Denied: Admin privileges required.")
        st.stop()

    st.title("🛡️ Admin Panel")
    
    tabs = st.tabs(["User Management", "User Predictions"])

    with tabs[0]:
        st.subheader("All Users")
        with st.spinner("Fetching users..."):
            try:
                token = get_token()
                headers = {"Authorization": f"Bearer {token}"}
                response = requests.get(f"{API_BASE_URL}/users/", headers=headers, timeout=10)
                response.raise_for_status()
                users = response.json()

                if not users:
                    st.info("No users found.")
                else:
                    df = pd.DataFrame(users)
                    
                    # Select and order columns
                    cols = ["email", "username", "role", "is_active", "last_login", "created_at", "user_id", "channel_id"]
                    available_cols = [c for c in cols if c in df.columns]
                    df = df[available_cols]

                    # Rename columns for display
                    df.columns = [c.replace("_", " ").title() for c in df.columns]

                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.caption(f"Total users: {len(users)}")

            except Exception as e:
                st.error("Could not load users.")
                st.exception(e)

    with tabs[1]:
        st.subheader("Inspect User Activity")
        if 'users' in locals() and users:
            user_options = {u['email'] or u['user_id']: u['user_id'] for u in users}
            selected_email = st.selectbox("Select a user to inspect predictions", options=list(user_options.keys()))
            selected_user_id = user_options[selected_email]

            if st.button("Load Predictions"):
                with st.spinner(f"Loading predictions for {selected_email}..."):
                    try:
                        headers = {"Authorization": f"Bearer {token}"}
                        # We don't have an admin-specific prediction endpoint but we can use the general user one
                        pred_resp = requests.get(f"{API_BASE_URL}/predictions/user/{selected_user_id}?limit=50", headers=headers, timeout=10)
                        pred_resp.raise_for_status()
                        predictions = pred_resp.json()

                        if not predictions:
                            st.info(f"No recent predictions found for {selected_email}.")
                        else:
                            p_df = pd.DataFrame(predictions)
                            # Format columns
                            p_df = p_df[["ticker", "label_text", "confidence", "current_price", "graham_value", "predicted_at"]]
                            p_df.columns = ["Ticker", "Label", "Confidence", "Price", "Graham Value", "Date"]
                            
                            # Format Confidence as %
                            p_df["Confidence"] = p_df["Confidence"].apply(lambda x: f"{x:.1%}" if pd.notnull(x) else "N/A")
                            
                            st.dataframe(p_df, use_container_width=True, hide_index=True)
                    except Exception as e:
                        st.error("Failed to load user predictions.")
                        st.exception(e)
        else:
            st.info("Please refresh User Management tab to populate user list.")

if __name__ == "__main__":
    render()
