import json
import os
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
    "skip_patterns": [],
}


def _get_cloud_config() -> dict:
    try:
        import streamlit as st

        section = st.secrets.get("cloud", {})
        aws = st.secrets.get("aws", {})
        return {
            "provider": str(section.get("provider", "")).lower(),
            "s3_bucket": str(section.get("s3_bucket_name", "")),
            "s3_prefix": str(section.get("s3_key_prefix", "")),
            "aws_access_key_id": str(aws.get("aws_access_key_id", "")),
            "aws_secret_access_key": str(aws.get("aws_secret_access_key", "")),
            "aws_region": str(aws.get("aws_default_region", "")),
        }
    except Exception:
        return {
            "provider": os.environ.get("EXPENSE_TRACKER_CLOUD_PROVIDER", "").lower(),
            "s3_bucket": os.environ.get("S3_BUCKET_NAME", ""),
            "s3_prefix": os.environ.get("S3_KEY_PREFIX", ""),
            "aws_access_key_id": os.environ.get("AWS_ACCESS_KEY_ID", ""),
            "aws_secret_access_key": os.environ.get("AWS_SECRET_ACCESS_KEY", ""),
            "aws_region": os.environ.get("AWS_DEFAULT_REGION", ""),
        }


def _get_cloud_provider():
    cfg = _get_cloud_config()
    if cfg["provider"] == "s3":
        from expense_tracker.cloud.s3 import S3Provider

        if not cfg["s3_bucket"]:
            raise ValueError(
                "cloud.s3_bucket_name secret is required for the S3 provider."
            )
        return S3Provider(
            bucket=cfg["s3_bucket"],
            prefix=cfg["s3_prefix"],
            aws_access_key_id=cfg["aws_access_key_id"] or None,
            aws_secret_access_key=cfg["aws_secret_access_key"] or None,
            aws_region=cfg["aws_region"] or None,
        )
    return None


def _cloud_load(key: str) -> str | None:
    provider = _get_cloud_provider()
    if provider is None:
        return None
    return provider.download(key)


def _cloud_save(key: str, data: str) -> None:
    provider = _get_cloud_provider()
    if provider is not None:
        provider.upload(key, data)


def load_config() -> dict:
    remote = _cloud_load("config.json")
    if remote is not None:
        CONFIG_FILE.write_text(remote, encoding="utf-8")
    elif not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict) -> None:
    data = json.dumps(config, indent=2)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(data)
    _cloud_save("config.json", data)


def load_transactions() -> list[dict]:
    remote = _cloud_load("transactions.json")
    if remote is not None:
        TRANSACTIONS_FILE.write_text(remote, encoding="utf-8")
    elif not TRANSACTIONS_FILE.exists():
        return []
    with open(TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_transactions(transactions: list[dict]) -> None:
    data = json.dumps(transactions, indent=2)
    with open(TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
        f.write(data)
    _cloud_save("transactions.json", data)


def load_settlements() -> list[dict]:
    remote = _cloud_load("settlements.json")
    if remote is not None:
        SETTLEMENTS_FILE.write_text(remote, encoding="utf-8")
    elif not SETTLEMENTS_FILE.exists():
        return []
    with open(SETTLEMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_settlements(settlements: list[dict]) -> None:
    data = json.dumps(settlements, indent=2)
    with open(SETTLEMENTS_FILE, "w", encoding="utf-8") as f:
        f.write(data)
    _cloud_save("settlements.json", data)


def get_unsettled_transactions() -> list[dict]:
    return [t for t in load_transactions() if not t.get("settled", False)]


def compute_balance(config: dict, transactions: list[dict]) -> dict[str, float]:
    people = config["people"]
    split_method = config.get("split_method", "equal")
    incomes = config.get("incomes", {})

    if split_method == "income_proportion" and incomes:
        total_income = sum(incomes.get(p, 0) for p in people)
        proportions = {
            p: (
                incomes.get(p, 0) / total_income
                if total_income > 0
                else 1 / len(people)
            )
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


def record_settlement(
    payer: str, payee: str, amount: float, transaction_ids: list[str]
) -> None:
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
