import csv
from datetime import datetime

from app.database.db import Base, engine, SessionLocal
from app.models.payment import Payment
from app.models.recovery_audit import RecoveryAudit


TRANSACTIONS_FILE = "data/transactions.csv"


def seed_database():

    print("Creating database tables...")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:

        existing_payments = db.query(Payment).count()

        if existing_payments > 0:
            print(
                f"Database already contains "
                f"{existing_payments} payments."
            )
            return

        print("Importing payments...")

        with open(
            TRANSACTIONS_FILE,
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                payment = Payment(
                    payment_id=row["payment_id"],
                    customer_id=row["customer_id"],
                    merchant_id=row["merchant_id"],
                    amount=int(row["amount"]),
                    payment_method=row["payment_method"],
                    status=row["status"],

                    failure_code=(
                        row["failure_code"] or None
                    ),

                    failure_reason=(
                        row["failure_reason"] or None
                    ),

                    retry_count=0,

                    recovery_status=(
                        "pending"
                        if row["status"] == "failed"
                        else "not_required"
                    ),

                    recovered_amount=0,

                    created_at=datetime.fromisoformat(
                        row["created_at"]
                    )
                )

                db.add(payment)

        db.commit()

        print("Database seeded successfully.")
        print(
            "Payments:",
            db.query(Payment).count()
        )

        print(
            "Audit records: 0"
        )

    except Exception as error:

        db.rollback()
        print("Error:", error)

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()