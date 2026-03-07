import uuid
import random
from datetime import date, timedelta
from expense_tracker.storage import load_transactions, save_transactions, load_config

DUMMY_EXPENSES = {
    "Groceries": [
        ("Whole Foods", 87.42),
        ("Trader Joe's", 63.15),
        ("Costco", 142.80),
        ("Local Market", 34.50),
        ("Safeway", 55.20),
    ],
    "Dining": [
        ("Chipotle", 24.50),
        ("Shake Shack", 31.00),
        ("Sushi Place", 68.00),
        ("Pizza Hut", 29.99),
        ("Starbucks", 12.45),
        ("Local Cafe", 18.75),
    ],
    "Subscriptions": [
        ("Netflix", 15.49),
        ("Spotify", 9.99),
        ("Amazon Prime", 14.99),
        ("Hulu", 17.99),
        ("iCloud Storage", 2.99),
    ],
    "Commute": [
        ("Metro Card", 33.00),
        ("Uber", 18.50),
        ("Lyft", 22.30),
        ("Gas Station", 55.00),
        ("Parking", 20.00),
    ],
    "Healthcare": [
        ("CVS Pharmacy", 45.00),
        ("Doctor Copay", 30.00),
        ("Gym Membership", 49.99),
        ("Dentist", 120.00),
    ],
    "Entertainment": [
        ("Movie Tickets", 38.00),
        ("Concert Tickets", 95.00),
        ("Steam Games", 29.99),
        ("Bowling", 42.00),
    ],
    "Utilities": [
        ("Electric Bill", 110.00),
        ("Internet Bill", 79.99),
        ("Water Bill", 55.00),
        ("Phone Bill", 85.00),
    ],
    "Travel": [
        ("Airbnb", 215.00),
        ("Flight Booking", 380.00),
        ("Hotel Stay", 160.00),
    ],
    "Rent": [
        ("Monthly Rent", 1800.00),
    ],
    "Other": [
        ("Amazon Purchase", 42.99),
        ("Home Depot", 65.00),
        ("IKEA", 135.00),
        ("Target", 78.50),
    ],
}


def seed_dummy_data() -> None:
    existing = load_transactions()
    if existing:
        return

    config = load_config()
    people = config["people"]
    tags = config["default_tags"]

    today = date.today()
    start = today - timedelta(days=90)

    transactions = []
    for _ in range(110):
        tag = random.choice(tags)
        person = random.choice(people)
        options = DUMMY_EXPENSES.get(tag, DUMMY_EXPENSES["Other"])
        description, base_amount = random.choice(options)
        amount = round(base_amount * random.uniform(0.85, 1.15), 2)
        txn_date = start + timedelta(days=random.randint(0, 90))

        transactions.append(
            {
                "id": str(uuid.uuid4()),
                "date": txn_date.isoformat(),
                "description": description,
                "amount": amount,
                "person": person,
                "tags": [tag],
                "settled": False,
                "settlement_id": None,
            }
        )

    transactions.sort(key=lambda x: x["date"])
    save_transactions(transactions)
