import streamlit as st
from expense_tracker.page import (
    upload_page,
    splitting_page,
    analysis_page,
    settings_page,
    edit_data_page,
)

# --- Authentication ---
if not st.user.is_logged_in:
    st.title("Expense Tracker")
    st.button("Sign in with Google", icon="🔑", on_click=st.login)
    st.stop()

allowed_emails = st.secrets.get("auth", {}).get("allowed_emails", [])
if allowed_emails and st.user.email not in allowed_emails:
    st.error(f"Access denied. **{st.user.email}** is not authorised to use this app.")
    st.button("Sign out", on_click=st.logout)
    st.stop()

# --- App ---
with st.sidebar:
    st.title("Expense Tracker")
    st.caption(f"Signed in as {st.user.email}")

    if "page" not in st.session_state:
        st.session_state.page = "Analysis"

    if st.button(label="Upload", icon="⬆️", width="stretch"):
        st.session_state.page = "Upload"

    if st.button(label="Bill Splitting", icon="⚖️", width="stretch"):
        st.session_state.page = "Bill Splitting"

    if st.button(label="Analysis", icon="📊", width="stretch"):
        st.session_state.page = "Analysis"

    if st.button(label="Edit Data", icon="✏️", width="stretch"):
        st.session_state.page = "Edit Data"

    if st.button(label="Settings", icon="⚙️", width="stretch"):
        st.session_state.page = "Settings"

    st.divider()
    st.button("Sign out", icon="🚪", on_click=st.logout, width="stretch")

match st.session_state["page"]:
    case "Upload":
        upload_page.render_page()
    case "Bill Splitting":
        splitting_page.render_page()
    case "Analysis":
        analysis_page.render_page()
    case "Edit Data":
        edit_data_page.render_page()
    case "Settings":
        settings_page.render_page()
