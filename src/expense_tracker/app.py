import streamlit as st
from expense_tracker.page import (
    upload_page,
    splitting_page,
    analysis_page,
    settings_page,
    edit_data_page,
)

with st.sidebar:
    st.title("Expense Tracker")

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
