from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime

from app.database.db import Base


class RecoveryAudit(Base):

    __tablename__ = "recovery_audit"

    id = Column(Integer, primary_key=True, index=True)

    payment_id = Column(
        String,
        nullable=False,
        index=True
    )

    failure_code = Column(String, nullable=False)

    recommended_action = Column(
        String,
        nullable=False
    )

    action_allowed = Column(
        Boolean,
        nullable=False
    )

    decision_reason = Column(
        String,
        nullable=False
    )

    recovery_result = Column(
        String,
        nullable=False
    )

    recovered_amount = Column(
        Integer,
        default=0
    )

    processed_at = Column(
        DateTime,
        default=datetime.utcnow
    )