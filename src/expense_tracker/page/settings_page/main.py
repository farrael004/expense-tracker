import io
import json
import streamlit as st
import pandas as pd
from expense_tracker.storage import (
    load_config,
    save_config,
    load_transactions,
    save_transactions,
    load_settlements,
    save_settlements,
    DATA_DIR,
)


def render_page():
    st.title("Settings")

    config = load_config()

    config = _render_people_settings(config)
    st.divider()
    config = _render_split_settings(config)
    st.divider()
    config = _render_tag_settings(config)
    st.divider()
    _render_data_management()


def _render_people_settings(config: dict) -> dict:
    st.subheader("People")
    people = config.get("people", [])
    incomes = config.get("incomes", {})

    st.caption("Add, remove, or rename the people tracked in this app (2–5).")

    updated_people = []
    to_remove = []

    for i, person in enumerate(people):
        col1, col2 = st.columns([4, 1])
        with col1:
            new_name = st.text_input(
                f"Person {i + 1}", value=person, key=f"person_name_{i}"
            )
            updated_people.append(new_name)
        with col2:
            st.write("")
            st.write("")
            if len(people) > 2:
                if st.button("Remove", key=f"remove_person_{i}"):
                    to_remove.append(i)

    if to_remove:
        updated_people = [
            p for idx, p in enumerate(updated_people) if idx not in to_remove
        ]
        config["people"] = updated_people
        config["incomes"] = {p: incomes.get(p, 0) for p in updated_people}
        save_config(config)
        st.rerun()

    if len(updated_people) < 5:
        if st.button("+ Add Person"):
            updated_people.append(f"Person {len(updated_people) + 1}")
            config["people"] = updated_people
            config["incomes"] = {p: incomes.get(p, 0) for p in updated_people}
            save_config(config)
            st.rerun()

    if updated_people != people:
        config["people"] = updated_people
        config["incomes"] = {p: incomes.get(p, 0) for p in updated_people}
        save_config(config)

    return config


def _render_split_settings(config: dict) -> dict:
    st.subheader("Bill Splitting Method")

    split_method = config.get("split_method", "equal")
    incomes = config.get("incomes", {})
    people = config.get("people", [])

    method = st.radio(
        "How should expenses be split?",
        options=["equal", "income_proportion"],
        format_func=lambda x: "Split equally"
        if x == "equal"
        else "Split by income proportion",
        index=0 if split_method == "equal" else 1,
        key="split_method_radio",
    )

    if method == "income_proportion":
        st.caption("Enter annual income for each person to calculate proportions.")
        new_incomes = {}
        cols = st.columns(len(people))
        for i, person in enumerate(people):
            with cols[i]:
                new_incomes[person] = st.number_input(
                    f"{person}'s income",
                    min_value=0,
                    value=int(incomes.get(person, 50000)),
                    step=1000,
                    key=f"income_{person}",
                )

        total = sum(new_incomes.values())
        if total > 0:
            st.caption(
                "Proportions: "
                + " | ".join(
                    f"{p}: {v / total * 100:.1f}%" for p, v in new_incomes.items()
                )
            )

        if new_incomes != incomes or method != split_method:
            config["split_method"] = method
            config["incomes"] = new_incomes
            save_config(config)
    else:
        if method != split_method:
            config["split_method"] = method
            save_config(config)

    return config


def _render_tag_settings(config: dict) -> dict:
    st.subheader("Tags")
    tags = config.get("default_tags", [])

    st.caption("Manage the default tags available when uploading transactions.")

    cols = st.columns(4)
    tags_to_remove = []
    for i, tag in enumerate(tags):
        with cols[i % 4]:
            col_tag, col_del = st.columns([3, 1])
            with col_tag:
                st.write(tag)
            with col_del:
                if st.button("✕", key=f"del_tag_{i}"):
                    tags_to_remove.append(tag)

    if tags_to_remove:
        tags = [t for t in tags if t not in tags_to_remove]
        config["default_tags"] = tags
        save_config(config)
        st.rerun()

    new_tag = st.text_input("New tag name", key="new_tag_settings")
    if st.button("Add Tag", key="add_tag_settings"):
        if new_tag and new_tag not in tags:
            tags.append(new_tag)
            config["default_tags"] = tags
            save_config(config)
            st.success(f"Tag '{new_tag}' added.")
            st.rerun()
        elif new_tag in tags:
            st.warning("Tag already exists.")

    return config


def _render_data_management():
    st.subheader("Data Management")

    transactions = load_transactions()

    if transactions:
        df = pd.DataFrame(transactions)
        df["tags"] = df["tags"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else x
        )
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Export All Transactions as CSV",
            data=csv_bytes,
            file_name="transactions.csv",
            mime="text/csv",
        )

        json_bytes = json.dumps(transactions, indent=2).encode("utf-8")
        st.download_button(
            label="Export All Transactions as JSON",
            data=json_bytes,
            file_name="transactions.json",
            mime="application/json",
        )
    else:
        st.info("No transactions to export.")

    st.divider()
    st.markdown("**Danger Zone**")

    col1, col2 = st.columns(2)

    with col1:
        if "confirm_clear_unsettled" not in st.session_state:
            st.session_state.confirm_clear_unsettled = False

        if not st.session_state.confirm_clear_unsettled:
            if st.button("Clear Unsettled Transactions", type="secondary"):
                st.session_state.confirm_clear_unsettled = True
                st.rerun()
        else:
            st.warning("This will permanently delete all unsettled transactions.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm", key="confirm_clear_btn"):
                    settled = [t for t in transactions if t.get("settled", False)]
                    save_transactions(settled)
                    st.session_state.confirm_clear_unsettled = False
                    st.success("Unsettled transactions cleared.")
                    st.rerun()
            with c2:
                if st.button("Cancel", key="cancel_clear_btn"):
                    st.session_state.confirm_clear_unsettled = False
                    st.rerun()

    with col2:
        if "confirm_full_reset" not in st.session_state:
            st.session_state.confirm_full_reset = False

        if not st.session_state.confirm_full_reset:
            if st.button("Full Data Reset", type="secondary"):
                st.session_state.confirm_full_reset = True
                st.rerun()
        else:
            st.warning("This will delete ALL transactions and settlements.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Confirm Reset", key="confirm_reset_btn"):
                    save_transactions([])
                    save_settlements([])
                    st.session_state.confirm_full_reset = False
                    st.success("All data reset.")
                    st.rerun()
            with c2:
                if st.button("Cancel", key="cancel_reset_btn"):
                    st.session_state.confirm_full_reset = False
                    st.rerun()
