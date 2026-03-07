import uuid
import io
import streamlit as st
import pandas as pd
from expense_tracker.storage import (
    load_config,
    save_config,
    load_transactions,
    save_transactions,
)


def render_page():
    st.title("Upload Expenses")

    config = load_config()
    people = config["people"]
    tags = config["default_tags"]

    uploaded_file = st.file_uploader("Upload a bank statement CSV", type=["csv"])

    if uploaded_file is None:
        st.info("Upload a CSV file to get started.")
        return

    try:
        df_raw = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    st.subheader("Preview")
    st.dataframe(df_raw.head(10), use_container_width=True)

    st.subheader("Column Mapping")
    columns = list(df_raw.columns)

    col1, col2, col3 = st.columns(3)
    with col1:
        date_col = st.selectbox("Date column", columns, key="date_col")
    with col2:
        desc_col = st.selectbox("Description column", columns, key="desc_col")
    with col3:
        amount_col = st.selectbox("Amount column", columns, key="amount_col")

    person = st.selectbox("This statement belongs to", people, key="upload_person")

    st.subheader("Tag Assignment")

    bulk_tags = st.multiselect(
        "Apply these tags to ALL transactions",
        options=tags,
        key="bulk_tags",
    )

    new_tag_input = st.text_input("Create a new tag (press Enter to add)", key="new_tag_input")
    if new_tag_input and new_tag_input not in tags:
        if st.button("Add tag", key="add_tag_btn"):
            tags.append(new_tag_input)
            config["default_tags"] = tags
            save_config(config)
            st.success(f"Tag '{new_tag_input}' added.")
            st.rerun()

    use_per_row = st.checkbox("Override tags per individual transaction", value=False)

    try:
        df_work = df_raw[[date_col, desc_col, amount_col]].copy()
        df_work.columns = ["date", "description", "amount"]
        df_work["date"] = pd.to_datetime(df_work["date"], infer_datetime_format=True).dt.date
        df_work["amount"] = pd.to_numeric(df_work["amount"].astype(str).str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
        df_work = df_work.dropna(subset=["amount"])
        df_work["amount"] = df_work["amount"].abs()
    except Exception as e:
        st.error(f"Error processing columns: {e}")
        return

    per_row_tags: dict[int, list[str]] = {}
    if use_per_row:
        st.markdown("**Per-transaction tags**")
        for i, row in df_work.iterrows():
            row_tags = st.multiselect(
                f"{row['date']} — {row['description']} (${row['amount']:.2f})",
                options=tags,
                default=bulk_tags,
                key=f"row_tags_{i}",
            )
            per_row_tags[i] = row_tags

    existing = load_transactions()
    existing_keys = {
        (t["date"], t["description"].strip().lower(), round(float(t["amount"]), 2))
        for t in existing
    }

    def get_tags_for(i: int) -> list[str]:
        return per_row_tags.get(i, bulk_tags) if use_per_row else bulk_tags

    new_rows = []
    duplicate_rows = []
    for i, row in df_work.iterrows():
        key = (str(row["date"]), str(row["description"]).strip().lower(), round(float(row["amount"]), 2))
        if key in existing_keys:
            duplicate_rows.append(row)
        else:
            new_rows.append((i, row))

    if duplicate_rows:
        st.warning(f"{len(duplicate_rows)} duplicate transaction(s) detected and will be skipped.")

    st.markdown(f"**{len(new_rows)} new transaction(s) ready to import.**")

    if st.button("Save Transactions", type="primary", disabled=len(new_rows) == 0):
        new_txns = []
        for i, row in new_rows:
            new_txns.append(
                {
                    "id": str(uuid.uuid4()),
                    "date": str(row["date"]),
                    "description": str(row["description"]),
                    "amount": round(float(row["amount"]), 2),
                    "person": person,
                    "tags": get_tags_for(i),
                    "settled": False,
                    "settlement_id": None,
                }
            )
        save_transactions(existing + new_txns)
        st.success(f"Saved {len(new_txns)} transaction(s).")
        st.rerun()
