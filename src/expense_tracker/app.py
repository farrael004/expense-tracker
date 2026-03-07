import streamlit as st
from expense_tracker.page import (
    upload_page,
    splitting_page,
    analysis_page,
    settings_page,
)

with st.sidebar:
    st.title("Expense Tracker")

    if "page" not in st.session_state:
        st.session_state.page = "Analysis"

    if st.button(label="Upload", icon="⬆️", use_container_width=True):
        st.session_state.page = "Upload"

    if st.button(label="Bill Splitting", icon="⚖️", use_container_width=True):
        st.session_state.page = "Bill Splitting"

    if st.button(label="Analysis", icon="📊", use_container_width=True):
        st.session_state.page = "Analysis"

    if st.button(label="Settings", icon="⚙️", use_container_width=True):
        st.session_state.page = "Settings"

match st.session_state["page"]:
    case "Upload":
        upload_page.render_page()
    case "Bill Splitting":
        splitting_page.render_page()
    case "Analysis":
        analysis_page.render_page()
    case "Settings":
        settings_page.render_page()
