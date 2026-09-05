import csv
import random
from collections import Counter
from pathlib import Path
from datetime import datetime

from app.services.recovery_engine import RecoveryEngine


random.seed(99)

engine = RecoveryEngine()

INPUT_FILE = Path("data/transactions.csv")
AUDIT_FILE = Path("data/recovery_audit.csv")


SUCCESS_PROBABILITIES = {
    "RETRY": 0.70,
    "SEND_REMINDER": 0.35,
    "SEND_PAYMENT_LINK": 0.45,
    "REAUTHENTICATE": 0.20,
}


def simulate_recovery(action: str) -> bool:
    probability = SUCCESS_PROBABILITIES.get(action, 0)
    return random.random() < probability


with INPUT_FILE.open(newline="", encoding="utf-8") as file:
    reader = csv.DictReader(file)
    transactions = list(reader)


failed_transactions = [
    transaction
    for transaction in transactions
    if transaction["status"] == "failed"
]


revenue_at_risk = sum(
    int(transaction["amount"])
    for transaction in failed_transactions
)


recovered_revenue = 0
recovered_payments = 0
blocked_actions = 0
unresolved_payments = 0

action_counter = Counter()

audit_records = []


for transaction in failed_transactions:

    decision = engine.decide(
        failure_code=transaction["failure_code"],
        retry_count=int(transaction["retry_count"])
    )

    action_counter[decision.action] += 1

    amount = int(transaction["amount"])

    recovery_result = "UNRESOLVED"
    recovered_amount = 0


    if not decision.allowed:

        blocked_actions += 1
        unresolved_payments += 1

        recovery_result = "BLOCKED"

    else:

        recovery_success = simulate_recovery(decision.action)

        if recovery_success:

            recovered_payments += 1
            recovered_revenue += amount

            recovered_amount = amount
            recovery_result = "RECOVERED"

        else:

            unresolved_payments += 1
            recovery_result = "FAILED"


    audit_records.append({
        "payment_id": transaction["payment_id"],
        "customer_id": transaction["customer_id"],
        "merchant_id": transaction["merchant_id"],
        "amount": amount,
        "payment_method": transaction["payment_method"],
        "failure_code": transaction["failure_code"],
        "failure_reason": transaction["failure_reason"],
        "recommended_action": decision.action,
        "action_allowed": decision.allowed,
        "decision_reason": decision.reason,
        "retry_count": transaction["retry_count"],
        "recovery_result": recovery_result,
        "recovered_amount": recovered_amount,
        "processed_at": datetime.now().isoformat(timespec="seconds")
    })


AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)

with AUDIT_FILE.open(
    "w",
    newline="",
    encoding="utf-8"
) as file:

    fieldnames = audit_records[0].keys()

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(audit_records)


recovery_rate = (
    recovered_revenue / revenue_at_risk * 100
    if revenue_at_risk > 0
    else 0
)


print("\n" + "=" * 55)
print("             RECOVERAI RECOVERY REPORT")
print("=" * 55)

print(f"\nTotal transactions      : {len(transactions)}")
print(f"Failed payments         : {len(failed_transactions)}")
print(f"Revenue at risk         : ₹{revenue_at_risk:,}")

print("\nRecovery actions:")

for action, count in action_counter.items():
    print(f"  {action:<20}: {count}")

print(f"\nRecovered payments      : {recovered_payments}")
print(f"Revenue recovered       : ₹{recovered_revenue:,}")
print(f"Recovery rate           : {recovery_rate:.2f}%")
print(f"Blocked actions         : {blocked_actions}")
print(f"Unresolved payments     : {unresolved_payments}")

print(f"\nAudit trail saved to    : {AUDIT_FILE}")

print("\n" + "=" * 55)