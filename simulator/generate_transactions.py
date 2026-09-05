import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
random.seed(42)

OUTPUT_FILE = Path("data/transactions.csv")
TOTAL_TRANSACTIONS = 200

PAYMENT_METHODS = ["upi", "card", "netbanking", "wallet"]

FAILURE_CODES = {
    "BANK_TIMEOUT": "Temporary bank-side timeout",
    "GATEWAY_ERROR": "Payment gateway temporarily unavailable",
    "INSUFFICIENT_FUNDS": "Customer account has insufficient funds",
    "CUSTOMER_ABANDONED": "Customer abandoned the payment flow",
    "AUTH_FAILURE": "Authentication or authorization failed",
}

AMOUNTS = [
    199,
    299,
    499,
    799,
    999,
    1299,
    1499,
    1999,
    2499,
    4999,
]


def generate_transaction(index: int) -> dict:
    # Around 30% of payments will fail.
    is_failed = random.random() < 0.30

    status = "failed" if is_failed else "success"

    if is_failed:
        failure_code = random.choice(list(FAILURE_CODES.keys()))
        failure_reason = FAILURE_CODES[failure_code]
    else:
        failure_code = ""
        failure_reason = ""

    created_at = datetime.now() - timedelta(
        minutes=random.randint(0, 7 * 24 * 60)
    )

    return {
        "payment_id": f"pay_{index:05d}",
        "customer_id": f"cust_{random.randint(1, 80):03d}",
        "merchant_id": f"merchant_{random.randint(1, 5):02d}",
        "amount": random.choice(AMOUNTS),
        "payment_method": random.choice(PAYMENT_METHODS),
        "status": status,
        "failure_code": failure_code,
        "failure_reason": failure_reason,
        "retry_count": 0,
        "recovery_status": "not_required" if status == "success" else "pending",
        "recovered_amount": 0,
        "created_at": created_at.isoformat(timespec="seconds"),
    }


def generate_dataset():
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    transactions = [
        generate_transaction(i)
        for i in range(1, TOTAL_TRANSACTIONS + 1)
    ]

    fieldnames = transactions[0].keys()

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(transactions)

    total_failed = sum(
        1 for transaction in transactions
        if transaction["status"] == "failed"
    )

    revenue_at_risk = sum(
        transaction["amount"]
        for transaction in transactions
        if transaction["status"] == "failed"
    )

    print(f"Generated {len(transactions)} transactions")
    print(f"Successful payments: {len(transactions) - total_failed}")
    print(f"Failed payments: {total_failed}")
    print(f"Revenue at risk: ₹{revenue_at_risk:,}")
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_dataset()