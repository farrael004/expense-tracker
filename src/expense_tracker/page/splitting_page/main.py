import streamlit as st
import pandas as pd
from expense_tracker.storage import (
    load_config,
    load_transactions,
    load_settlements,
    compute_balance,
    record_settlement,
)


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
        df[display_cols].rename(columns={"date": "Date", "description": "Description",
                                          "amount": "Amount ($)", "person": "Person", "tags": "Tags"}),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown(f"**Total unsettled: ${df['amount'].sum():,.2f}**")

    if st.button("Mark All as Settled", type="primary"):
        net = {p: round(balances.get(p, 0), 2) for p in people}
        creditors = [(p, v) for p, v in net.items() if v > 0]
        debtors = [(p, v) for p, v in net.items() if v < 0]
        txn_ids = [t["id"] for t in unsettled]

        if creditors and debtors:
            creditor = creditors[0][0]
            debtor = debtors[0][0]
            transfer = min(creditors[0][1], abs(debtors[0][1]))
            record_settlement(
                payer=debtor,
                payee=creditor,
                amount=transfer,
                transaction_ids=txn_ids,
            )
            st.success(f"Settlement recorded: {debtor} pays {creditor} ${transfer:,.2f}")
        else:
            record_settlement(
                payer=people[0],
                payee=people[1] if len(people) > 1 else people[0],
                amount=0,
                transaction_ids=txn_ids,
            )
            st.success("All transactions marked as settled.")
        st.rerun()


def _render_settlement_history(settlements: list[dict]):
    if not settlements:
        st.info("No settlements recorded yet.")
        return

    with st.expander(f"View {len(settlements)} past settlement(s)"):
        df = pd.DataFrame(settlements)[["date", "payer", "payee", "amount"]]
        df = df.sort_values("date", ascending=False)
        df["amount"] = df["amount"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(
            df.rename(columns={"date": "Date", "payer": "Payer", "payee": "Payee", "amount": "Amount"}),
            use_container_width=True,
            hide_index=True,
        )
