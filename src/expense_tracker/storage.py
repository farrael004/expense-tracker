import json
import uuid
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

CONFIG_FILE = DATA_DIR / "config.json"
TRANSACTIONS_FILE = DATA_DIR / "transactions.json"
SETTLEMENTS_FILE = DATA_DIR / "settlements.json"

DEFAULT_CONFIG = {
    "people": ["Person A", "Person B"],
    "split_method": "income_proportion",
    "incomes": {"Person A": 60000, "Person B": 40000},
    "default_tags": [
        "Groceries",
        "Rent",
        "Subscriptions",
        "Dining",
        "Commute",
        "Healthcare",
        "Entertainment",
        "Utilities",
        "Travel",
        "Other",
    ],
}


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def load_transactions() -> list[dict]:
    if not TRANSACTIONS_FILE.exists():
        return []
    with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_transactions(transactions: list[dict]) -> None:
    with open(TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(transactions, f, indent=2)


def load_settlements() -> list[dict]:
    if not SETTLEMENTS_FILE.exists():
        return []
    with open(SETTLEMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settlements(settlements: list[dict]) -> None:
    with open(SETTLEMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(settlements, f, indent=2)


def get_unsettled_transactions() -> list[dict]:
    return [t for t in load_transactions() if not t.get("settled", False)]


def compute_balance(config: dict, transactions: list[dict]) -> dict[str, float]:
    people = config["people"]
    split_method = config.get("split_method", "equal")
    incomes = config.get("incomes", {})

    if split_method == "income_proportion" and incomes:
        total_income = sum(incomes.get(p, 0) for p in people)
        proportions = {
            p: (incomes.get(p, 0) / total_income if total_income > 0 else 1 / len(people))
            for p in people
        }
    else:
        proportions = {p: 1 / len(people) for p in people}

    balances = {p: 0.0 for p in people}

    for txn in transactions:
        if txn.get("settled", False):
            continue
        payer = txn["person"]
        amount = txn["amount"]
        if payer not in people:
            continue
        for person in people:
            if person == payer:
                balances[person] += amount * (1 - proportions[person])
            else:
                balances[person] -= amount * proportions[person]

    return balances


def record_settlement(payer: str, payee: str, amount: float, transaction_ids: list[str]) -> None:
    transactions = load_transactions()
    for txn in transactions:
        if txn["id"] in transaction_ids:
            txn["settled"] = True
            txn["settlement_id"] = None

    settlement_id = str(uuid.uuid4())
    for txn in transactions:
        if txn["id"] in transaction_ids:
            txn["settlement_id"] = settlement_id

    save_transactions(transactions)

    settlements = load_settlements()
    settlements.append(
        {
            "id": settlement_id,
            "date": date.today().isoformat(),
            "payer": payer,
            "payee": payee,
            "amount": round(amount, 2),
            "transaction_ids": transaction_ids,
        }
    )
    save_settlements(settlements)
