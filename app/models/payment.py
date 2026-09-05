from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database.db import Base


class Payment(Base):

    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    customer_id = Column(String, nullable=False)
    merchant_id = Column(String, nullable=False)

    amount = Column(Integer, nullable=False)

    payment_method = Column(String, nullable=False)

    status = Column(String, nullable=False)

    failure_code = Column(String, nullable=True)
    failure_reason = Column(String, nullable=True)

    retry_count = Column(
        Integer,
        default=0
    )

    recovery_status = Column(
        String,
        default="pending"
    )

    recovered_amount = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )