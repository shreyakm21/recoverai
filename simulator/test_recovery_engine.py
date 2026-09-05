import csv

from app.services.recovery_engine import RecoveryEngine


engine = RecoveryEngine()

with open("data/transactions.csv", newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)

    failed_transactions = [
        row for row in reader
        if row["status"] == "failed"
    ]


print(f"\nFailed transactions found: {len(failed_transactions)}\n")

for transaction in failed_transactions[:10]:

    decision = engine.decide(
        failure_code=transaction["failure_code"],
        retry_count=int(transaction["retry_count"])
    )

    print("-" * 60)
    print(f"Payment ID : {transaction['payment_id']}")
    print(f"Amount     : ₹{transaction['amount']}")
    print(f"Failure    : {transaction['failure_code']}")
    print(f"Action     : {decision.action}")
    print(f"Allowed    : {decision.allowed}")
    print(f"Reason     : {decision.reason}")