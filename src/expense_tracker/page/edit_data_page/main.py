import streamlit as st
import pandas as pd
from expense_tracker.storage import load_config, load_transactions, save_transactions


def render_page():
    st.title("Edit Data")

    config = load_config()
    people = config["people"]
    all_tags = config["default_tags"]
    transactions = load_transactions()

    if not transactions:
        st.info("No transactions found. Upload data or load dummy data first.")
        return

    df = _build_dataframe(transactions)
    df = _render_filters(df, people)

    if df.empty:
        st.warning("No transactions match the current filters.")
        return

    edited = st.data_editor(
        df[["id", "date", "description", "amount", "person", "tags", "settled"]].rename(
            columns={
                "date": "Date",
                "description": "Description",
                "amount": "Amount ($)",
                "person": "Person",
                "tags": "Tags",
                "settled": "Settled",
            }
        ),
        width="stretch",
        hide_index=True,
        column_order=["Date", "Description", "Amount ($)", "Person", "Tags", "Settled"],
        column_config={
            "id": st.column_config.TextColumn("ID", disabled=True),
            "Date": st.column_config.DateColumn("Date"),
            "Description": st.column_config.TextColumn("Description"),
            "Amount ($)": st.column_config.NumberColumn(
                "Amount ($)", min_value=0, format="$%.2f"
            ),
            "Person": st.column_config.SelectboxColumn("Person", options=people),
            "Tags": st.column_config.MultiselectColumn(
                "Tags",
                options=all_tags,
            ),
            "Settled": st.column_config.CheckboxColumn("Settled"),
        },
        num_rows="dynamic",
    )

    if st.button("Save Changes", type="primary"):
        _save_edits(edited, transactions)
        st.success("Changes saved.")
        st.rerun()


def _build_dataframe(transactions: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(transactions)
    df["date"] = pd.to_datetime(df["date"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df["tags"] = df["tags"].apply(lambda x: list(x) if isinstance(x, list) else [])
    return df


def _render_filters(df: pd.DataFrame, people: list[str]) -> pd.DataFrame:
    with st.sidebar:
        st.header("Filters")

        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        date_range = st.date_input(
            "Date range", value=(min_date, max_date), key="edit_date"
        )

        selected_people = st.multiselect(
            "Person", people, default=people, key="edit_people"
        )

        all_tags_in_data = sorted(set(tag for tags in df["tags"] for tag in tags))
        selected_tags = st.multiselect(
            "Tags", all_tags_in_data, default=all_tags_in_data, key="edit_tags"
        )

        min_amt = float(df["amount"].min())
        max_amt = float(df["amount"].max())
        if min_amt < max_amt:
            amount_range = st.slider(
                "Amount range ($)",
                min_amt,
                max_amt,
                (min_amt, max_amt),
                key="edit_amount",
            )
        else:
            amount_range = (min_amt, max_amt)

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        df = df[(df["date"] >= start) & (df["date"] <= end)]

    if selected_people:
        df = df[df["person"].isin(selected_people)]

    if all_tags_in_data and len(selected_tags) < len(all_tags_in_data):
        df = df[
            df["tags"].apply(
                lambda tags: any(t in selected_tags for t in tags)
                if tags
                else not selected_tags
            )
        ]

    df = df[(df["amount"] >= amount_range[0]) & (df["amount"] <= amount_range[1])]
    return df


def _save_edits(edited: pd.DataFrame, original_transactions: list[dict]) -> None:
    txn_by_id = {t["id"]: t for t in original_transactions}

    edited_ids = set(edited["id"].dropna().tolist())

    for _, row in edited.iterrows():
        row_id = row.get("id")
        if pd.isna(row_id) or row_id == "":
            continue
        if row_id in txn_by_id:
            txn = txn_by_id[row_id]
            txn["date"] = pd.Timestamp(row["Date"]).date().isoformat()
            txn["description"] = str(row["Description"])
            txn["amount"] = float(row["Amount ($)"])
            txn["person"] = str(row["Person"])
            raw_tags = row.get("Tags", [])
            txn["tags"] = list(raw_tags) if isinstance(raw_tags, (list, tuple)) else []
            txn["settled"] = bool(row.get("Settled", False))

    remaining = [t for t in original_transactions if t["id"] in edited_ids]
    save_transactions(remaining)
