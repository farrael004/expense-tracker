import streamlit as st
import pandas as pd
from expense_tracker.storage import (
    load_config,
    load_transactions,
    load_settlements,
    compute_balance,
    record_settlement,
)


@st.dialog("Confirm Settlement")
def _show_settlement_dialog(
    unsettled: list[dict], people: list[str], balances: dict
):
    st.write("This will mark all unsettled transactions as settled.")
    st.write(f"**{len(unsettled)} transaction(s)** will be marked as settled.")

    unsettled_total = sum(t["amount"] for t in unsettled)
    st.write(f"**Total amount:** ${unsettled_total:,.2f}")

    st.warning("This action cannot be undone.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Confirm", type="primary", use_container_width=True):
            net = {p: round(balances.get(p, 0), 2) for p in people}
            creditors = sorted(
                [(p, v) for p, v in net.items() if v > 0], key=lambda x: -x[1]
            )
            debtors = sorted(
                [(p, v) for p, v in net.items() if v < 0], key=lambda x: x[1]
            )
            txn_ids = [t["id"] for t in unsettled]

            while creditors and debtors:
                creditor, credit_amt = creditors[0]
                debtor, debt_amt = debtors[0]
                transfer = min(credit_amt, abs(debt_amt))
                record_settlement(
                    payer=debtor,
                    payee=creditor,
                    amount=transfer,
                    transaction_ids=txn_ids,
                )
                credit_amt -= transfer
                debt_amt += transfer
                if credit_amt < 0.01:
                    creditors.pop(0)
                else:
                    creditors[0] = (creditor, credit_amt)
                if debt_amt > -0.01:
                    debtors.pop(0)
                else:
                    debtors[0] = (debtor, debt_amt)

            if not creditors and not debtors:
                pass
            elif txn_ids:
                record_settlement(
                    payer=people[0],
                    payee=people[1] if len(people) > 1 else people[0],
                    amount=0,
                    transaction_ids=txn_ids,
                )
            st.session_state["settlement_confirmed"] = True
            st.rerun()
    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("Settlement Details")
def _show_settlement_details_dialog(settlement: dict):
    st.subheader(f"Settlement on {settlement['date']}")
    st.write(f"**{settlement['payer']}** pays **{settlement['payee']}**")
    st.write(f"**Amount:** ${settlement['amount']:,.2f}")

    st.divider()
    st.write("**Transactions included in this settlement:**")

    backup = settlement.get("transactions_backup", [])
    if backup:
        df = pd.DataFrame(backup)
        if "tags" in df.columns:
            df["tags"] = df["tags"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else x
            )
        display_cols = ["date", "description", "amount", "person", "tags"]
        df = df[[c for c in display_cols if c in df.columns]]
        st.dataframe(
            df.rename(
                columns={
                    "date": "Date",
                    "description": "Description",
                    "amount": "Amount ($)",
                    "person": "Person",
                    "tags": "Tags",
                }
            ),
            width="stretch",
            hide_index=True,
        )
        st.write(f"**Total:** ${sum(t['amount'] for t in backup):,.2f}")
    else:
        st.info("No transaction backup available for this settlement.")

    if st.button("Close", use_container_width=True):
        st.rerun()


def render_page():
    st.title("Bill Splitting")

    config = load_config()
    people = config["people"]
    all_txns = load_transactions()
    unsettled = [t for t in all_txns if not t.get("settled", False)]
    balances = compute_balance(config, unsettled)

    st.subheader("Current Balance")
    _render_balance_summary(balances, people)

    st.divider()
    st.subheader("Unsettled Transactions")
    _render_unsettled_table(unsettled, people, balances)

    st.divider()
    st.subheader("Settlement History")
    _render_settlement_history(load_settlements())


def _render_balance_summary(balances: dict, people: list[str]):
    if len(people) < 2:
        st.info("Add at least 2 people in Settings.")
        return

    net = {p: round(balances.get(p, 0), 2) for p in people}

    creditors = [(p, v) for p, v in net.items() if v > 0]
    debtors = [(p, v) for p, v in net.items() if v < 0]

    if not creditors and not debtors:
        st.success("All settled up! No outstanding balance.")
        return

    for creditor, credit_amt in creditors:
        for debtor, debt_amt in debtors:
            transfer = min(credit_amt, abs(debt_amt))
            if transfer > 0.005:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.metric(
                        label=f"{debtor} owes {creditor}",
                        value=f"${transfer:,.2f}",
                    )


def _render_unsettled_table(unsettled: list[dict], people: list[str], balances: dict):
    if not unsettled:
        st.info("No unsettled transactions.")
        return

    filter_person = st.selectbox(
        "Filter by person",
        ["All"] + people,
        key="split_filter_person",
    )

    df = pd.DataFrame(unsettled)
    df["date"] = pd.to_datetime(df["date"])
    df["tags"] = df["tags"].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

    if filter_person != "All":
        df = df[df["person"] == filter_person]

    sort_col = st.selectbox("Sort by", ["date", "amount"], key="split_sort")
    df = df.sort_values(sort_col, ascending=(sort_col == "date"))

    display_cols = ["date", "description", "amount", "person", "tags"]
    st.dataframe(
        df[display_cols].rename(
            columns={
                "date": "Date",
                "description": "Description",
                "amount": "Amount ($)",
                "person": "Person",
                "tags": "Tags",
            }
        ),
        width="stretch",
        hide_index=True,
    )

    st.markdown(f"**Total unsettled: ${df['amount'].sum():,.2f}**")

    if st.button("Mark All as settled", type="primary"):
        _show_settlement_dialog(unsettled, people, balances)


def _render_settlement_history(settlements: list[dict]):
    if not settlements:
        st.info("No settlements recorded yet.")
        return

    with st.expander(f"View {len(settlements)} past settlement(s)"):
        df = pd.DataFrame(settlements)[["id", "date", "payer", "payee", "amount"]]
        df = df.sort_values("date", ascending=False)
        df["amount"] = df["amount"].apply(lambda x: f"${x:,.2f}")

        settlements_by_id = {s["id"]: s for s in settlements}

        for _, row in df.iterrows():
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(
                    f"**{row['date']}**: {row['payer']} pays {row['payee']} {row['amount']}"
                )
            with col2:
                if st.button(
                    "View", key=f"view_{row['id']}", use_container_width=True
                ):
                    settlement = settlements_by_id.get(row["id"])
                    if settlement:
                        _show_settlement_details_dialog(settlement)
