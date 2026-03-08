import fnmatch
import uuid
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

    tab_manual, tab_csv = st.tabs(["Manual Entry", "CSV Upload"])

    with tab_manual:
        with st.form("manual_entry_form"):
            date_val = st.date_input("Date")
            description_val = st.text_input("Description")
            amount_val = st.number_input(
                "Amount", min_value=0.0, step=0.01, format="%.2f"
            )
            person_val = st.selectbox("Person", people, key="manual_person")
            tags_val = st.multiselect("Tags", options=tags, key="manual_tags")
            submitted = st.form_submit_button("Add Entry", type="primary")

        if submitted:
            if not description_val:
                st.error("Description is required.")
            elif amount_val <= 0:
                st.error("Amount must be greater than zero.")
            else:
                existing = load_transactions()
                key = (
                    str(date_val),
                    description_val.strip().lower(),
                    round(float(amount_val), 2),
                )
                existing_keys = {
                    (
                        t["date"],
                        t["description"].strip().lower(),
                        round(float(t["amount"]), 2),
                    )
                    for t in existing
                }
                if key in existing_keys:
                    st.warning("A matching transaction already exists.")
                else:
                    existing.append(
                        {
                            "id": str(uuid.uuid4()),
                            "date": str(date_val),
                            "description": description_val.strip(),
                            "amount": round(float(amount_val), 2),
                            "person": person_val,
                            "tags": tags_val,
                            "settled": False,
                            "settlement_id": None,
                        }
                    )
                    save_transactions(existing)
                    st.toast("1 entry added.", icon="✅")

    with tab_csv:
        uploaded_file = st.file_uploader("Upload a bank statement CSV", type=["csv"])

        if uploaded_file is None:
            st.info("Upload a CSV file to get started.")
        else:
            try:
                df_raw = pd.read_csv(uploaded_file)
            except Exception as e:
                st.error(f"Could not read CSV: {e}")
                return

            st.subheader("Column Mapping")
            columns = list(df_raw.columns)

            col_lower = {c.lower(): i for i, c in enumerate(columns)}
            default_date_idx = col_lower.get("date", 0)
            default_desc_idx = col_lower.get("description", 0)
            default_amount_idx = col_lower.get("amount", 0)

            col1, col2, col3 = st.columns(3)
            with col1:
                date_col = st.selectbox(
                    "Date column", columns, index=default_date_idx, key="date_col"
                )
            with col2:
                desc_col = st.selectbox(
                    "Description column",
                    columns,
                    index=default_desc_idx,
                    key="desc_col",
                )
            with col3:
                amount_col = st.selectbox(
                    "Amount column", columns, index=default_amount_idx, key="amount_col"
                )

            person = st.selectbox(
                "This statement belongs to", people, key="upload_person"
            )

            st.subheader("Tag Assignment")

            new_tag_input = st.text_input(
                "Create a new tag (press Enter to add)", key="new_tag_input"
            )
            if new_tag_input and new_tag_input not in tags:
                if st.button("Add tag", key="add_tag_btn"):
                    tags.append(new_tag_input)
                    config["default_tags"] = tags
                    save_config(config)
                    st.success(f"Tag '{new_tag_input}' added.")
                    st.rerun()

            use_bulk = st.checkbox(
                "Apply the same tags to all transactions", value=False
            )
            if use_bulk:
                bulk_tags = st.multiselect(
                    "Tags to apply to all transactions",
                    options=tags,
                    key="bulk_tags",
                )
            else:
                bulk_tags = []

            try:
                df_work = df_raw[[date_col, desc_col, amount_col]].copy()
                df_work.columns = ["date", "description", "amount"]
                df_work["date"] = pd.to_datetime(
                    df_work["date"], format="mixed"
                ).dt.date
                df_work["amount"] = pd.to_numeric(
                    df_work["amount"]
                    .astype(str)
                    .str.replace(r"[^\d.\-]", "", regex=True),
                    errors="coerce",
                )
                df_work = df_work.dropna(subset=["amount"])
            except Exception as e:
                st.error(f"Error processing columns: {e}")
                return

            df_work["tags"] = [list(bulk_tags)] * len(df_work)

            st.subheader("Preview")
            caption_area = st.container()
            force_positive = st.checkbox(
                "Convert negative amounts to positive", value=False
            )
            if force_positive:
                df_work["amount"] = df_work["amount"].abs()

            skip_patterns = config.get("skip_patterns", [])
            if skip_patterns:

                def _matches_any(desc: str) -> bool:
                    desc_lower = str(desc).strip().lower()
                    return any(
                        fnmatch.fnmatch(desc_lower, p.lower()) for p in skip_patterns
                    )

                is_skipped = df_work["description"].apply(_matches_any)
                n_skipped = int(is_skipped.sum())
                if n_skipped:
                    st.info(f"{n_skipped} row(s) removed by auto-skip patterns.")
                df_work = df_work[~is_skipped].reset_index(drop=True)

            existing = load_transactions()
            existing_keys = {
                (
                    t["date"],
                    t["description"].strip().lower(),
                    round(float(t["amount"]), 2),
                )
                for t in existing
            }

            is_dup = df_work.apply(
                lambda row: (
                    str(row["date"]),
                    str(row["description"]).strip().lower(),
                    round(float(row["amount"]), 2),
                )
                in existing_keys,
                axis=1,
            )
            n_dups = int(is_dup.sum())
            if n_dups:
                st.warning(
                    f"{n_dups} duplicate transaction(s) detected and will be skipped."
                )

            df_new = df_work[~is_dup].reset_index(drop=True)

            with caption_area:
                st.caption(
                    f"{len(df_new)} new transaction(s) ready to import. "
                    "Remove rows you don't want or edit values before saving."
                )

            edited = st.data_editor(
                df_new,
                width="stretch",
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "date": st.column_config.DateColumn("Date"),
                    "description": st.column_config.TextColumn("Description"),
                    "amount": st.column_config.NumberColumn(
                        "Amount ($)", format="$%.2f"
                    ),
                    "tags": st.column_config.MultiselectColumn(
                        "Tags",
                        options=tags,
                    ),
                },
            )

            if st.button(
                "Save Transactions", type="primary", disabled=len(edited) == 0
            ):
                new_txns = []
                for _, row in edited.iterrows():
                    raw_tags = row.get("tags", [])
                    row_tags = (
                        list(raw_tags) if isinstance(raw_tags, (list, tuple)) else []
                    )
                    new_txns.append(
                        {
                            "id": str(uuid.uuid4()),
                            "date": str(row["date"]),
                            "description": str(row["description"]),
                            "amount": round(float(row["amount"]), 2),
                            "person": person,
                            "tags": row_tags,
                            "settled": False,
                            "settlement_id": None,
                        }
                    )
                save_transactions(existing + new_txns)
                st.toast(
                    f"{len(new_txns)} entr{'y' if len(new_txns) == 1 else 'ies'} added.",
                    icon="✅",
                )
                st.rerun()
