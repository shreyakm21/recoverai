import random
from datetime import datetime

import os
import json
import hmac
import hashlib

from fastapi import Request

from app.services.ai_recovery_advisor import AIRecoveryAdvisor
from app.services.recovery_engine import RecoveryEngine
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.services.razorpay_service import RazorpayService
from pydantic import BaseModel

from app.database.db import get_db
from app.models.payment import Payment
from app.models.recovery_audit import RecoveryAudit

class RazorpayVerificationRequest(BaseModel):
    recoverai_payment_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

router = APIRouter()
engine = RecoveryEngine()
advisor = AIRecoveryAdvisor()
razorpay_service = RazorpayService()

SUCCESS_PROBABILITIES = {
    "RETRY": 0.70,
    "SEND_REMINDER": 0.35,
    "SEND_PAYMENT_LINK": 0.45,
    "REAUTHENTICATE": 0.20,
}

@router.get("/payments/failed")
def get_failed_payments(db: Session = Depends(get_db)):

    failed_payments = (
        db.query(Payment)
        .filter(Payment.status == "failed")
        .all()
    )

    return {
        "count": len(failed_payments),
        "payments": [
            {
                "payment_id": payment.payment_id,
                "customer_id": payment.customer_id,
                "merchant_id": payment.merchant_id,
                "amount": payment.amount,
                "payment_method": payment.payment_method,
                "status": payment.status,
                "failure_code": payment.failure_code,
                "failure_reason": payment.failure_reason,
                "retry_count": payment.retry_count,
                "recovery_status": payment.recovery_status,
                "recovered_amount": payment.recovered_amount,
                "created_at": payment.created_at,
            }
            for payment in failed_payments
        ]
    }


@router.get("/recovery/summary")
def get_recovery_summary(db: Session = Depends(get_db)):

    total_transactions = db.query(Payment).count()

    # These are all payments that originally failed.
    # Recovered payments still retain their failure_code,
    # so this remains our original at-risk population.
    originally_failed_payments = (
        db.query(Payment)
        .filter(Payment.failure_code.isnot(None))
        .all()
    )

    currently_failed_payments = (
        db.query(Payment)
        .filter(Payment.status == "failed")
        .all()
    )

    recovered_payments = (
        db.query(Payment)
        .filter(
            Payment.status == "success",
            Payment.recovered_amount > 0
        )
        .all()
    )

    blocked_payments = (
        db.query(Payment)
        .filter(Payment.recovery_status == "blocked")
        .all()
    )

    initial_revenue_at_risk = sum(
        payment.amount
        for payment in originally_failed_payments
    )

    remaining_revenue_at_risk = sum(
        payment.amount
        for payment in currently_failed_payments
    )

    recovered_revenue = sum(
        payment.recovered_amount
        for payment in recovered_payments
    )

    recovery_rate = (
        recovered_revenue / initial_revenue_at_risk * 100
        if initial_revenue_at_risk > 0
        else 0
    )

    return {
        "total_transactions": total_transactions,

        "initial_failed_payments": len(
            originally_failed_payments
        ),

        "initial_revenue_at_risk": initial_revenue_at_risk,

        "recovered_payments": len(
            recovered_payments
        ),

        "revenue_recovered": recovered_revenue,

        "recovery_rate_percent": round(
            recovery_rate,
            2
        ),

        "remaining_failed_payments": len(
            currently_failed_payments
        ),

        "remaining_revenue_at_risk": remaining_revenue_at_risk,

        "blocked_payments": len(
            blocked_payments
        )
    }


@router.get("/recovery/audit/{payment_id}")
def get_payment_audit(
    payment_id: str,
    db: Session = Depends(get_db)
):

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail=f"Payment {payment_id} not found"
        )

    audit_records = (
        db.query(RecoveryAudit)
        .filter(RecoveryAudit.payment_id == payment_id)
        .order_by(RecoveryAudit.processed_at.asc())
        .all()
    )

    if not audit_records:
        raise HTTPException(
            status_code=404,
            detail=f"No audit records found for {payment_id}"
        )

    return {
        "payment": {
            "payment_id": payment.payment_id,
            "amount": payment.amount,
            "status": payment.status,
            "failure_code": payment.failure_code,
            "retry_count": payment.retry_count,
            "recovery_status": payment.recovery_status,
            "recovered_amount": payment.recovered_amount
        },
        "attempt_count": len(audit_records),
        "timeline": [
            {
                "recommended_action": audit.recommended_action,
                "action_allowed": audit.action_allowed,
                "decision_reason": audit.decision_reason,
                "recovery_result": audit.recovery_result,
                "recovered_amount": audit.recovered_amount,
                "processed_at": audit.processed_at
            }
            for audit in audit_records
        ]
    }

def simulate_recovery(action: str) -> bool:
    probability = SUCCESS_PROBABILITIES.get(action, 0)
    return random.random() < probability

@router.post("/recovery/process/{payment_id}")
def process_payment_recovery(
    payment_id: str,
    db: Session = Depends(get_db)
):

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail=f"Payment {payment_id} not found"
        )

    if payment.status != "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Recovery can only be processed for failed payments",
                "payment_id": payment.payment_id,
                "current_status": payment.status,
                "recovery_status": payment.recovery_status
            }
        )

    decision = engine.decide(
        failure_code=payment.failure_code,
        retry_count=payment.retry_count
    )

    recovery_result = "BLOCKED"
    recovered_amount = 0

    if decision.allowed:

        success = simulate_recovery(decision.action)

        if success:
            recovery_result = "RECOVERED"
            recovered_amount = payment.amount

            payment.status = "success"
            payment.recovery_status = "recovered"
            payment.recovered_amount = payment.amount

        else:
            recovery_result = "FAILED"
            payment.recovery_status = "unresolved"

            if decision.action == "RETRY":
                payment.retry_count += 1

    else:
        payment.recovery_status = "blocked"

    audit = RecoveryAudit(
        payment_id=payment.payment_id,
        failure_code=payment.failure_code,
        recommended_action=decision.action,
        action_allowed=decision.allowed,
        decision_reason=decision.reason,
        recovery_result=recovery_result,
        recovered_amount=recovered_amount,
        processed_at=datetime.utcnow()
    )

    db.add(audit)

    db.commit()
    db.refresh(payment)

    return {
        "payment_id": payment.payment_id,
        "failure_code": payment.failure_code,
        "recommended_action": decision.action,
        "action_allowed": decision.allowed,
        "recovery_result": recovery_result,
        "recovered_amount": recovered_amount,
        "retry_count": payment.retry_count,
        "recovery_status": payment.recovery_status
    }


@router.post("/recovery/process-batch")
def process_batch_recovery(
    db: Session = Depends(get_db)
):

    failed_payments = (
        db.query(Payment)
        .filter(Payment.status == "failed")
        .all()
    )

    if not failed_payments:
        return {
            "message": "No failed payments available for recovery.",
            "processed": 0,
            "recovered": 0,
            "blocked": 0,
            "unresolved": 0,
            "revenue_recovered": 0
        }

    processed = 0
    recovered = 0
    blocked = 0
    unresolved = 0
    revenue_recovered = 0

    results = []

    for payment in failed_payments:

        processed += 1

        decision = engine.decide(
            failure_code=payment.failure_code,
            retry_count=payment.retry_count
        )

        recovery_result = "BLOCKED"
        recovered_amount = 0

        if decision.allowed:

            success = simulate_recovery(decision.action)

            if success:

                recovery_result = "RECOVERED"
                recovered_amount = payment.amount

                payment.status = "success"
                payment.recovery_status = "recovered"
                payment.recovered_amount = payment.amount

                recovered += 1
                revenue_recovered += payment.amount

            else:

                recovery_result = "FAILED"
                payment.recovery_status = "unresolved"
                unresolved += 1

                if decision.action == "RETRY":
                    payment.retry_count += 1

        else:

            payment.recovery_status = "blocked"
            blocked += 1
            unresolved += 1

        audit = RecoveryAudit(
            payment_id=payment.payment_id,
            failure_code=payment.failure_code,
            recommended_action=decision.action,
            action_allowed=decision.allowed,
            decision_reason=decision.reason,
            recovery_result=recovery_result,
            recovered_amount=recovered_amount,
            processed_at=datetime.utcnow()
        )

        db.add(audit)

        results.append({
            "payment_id": payment.payment_id,
            "amount": payment.amount,
            "failure_code": payment.failure_code,
            "action": decision.action,
            "result": recovery_result,
            "recovered_amount": recovered_amount
        })

    db.commit()

    return {
        "processed": processed,
        "recovered": recovered,
        "blocked": blocked,
        "unresolved": unresolved,
        "revenue_recovered": revenue_recovered,
        "results": results
    }


@router.get("/recovery/advice/{payment_id}")
def get_recovery_advice(
    payment_id: str,
    db: Session = Depends(get_db)
):

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail=f"Payment {payment_id} not found"
        )

    if payment.status != "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Recovery advice is only generated for failed payments",
                "payment_id": payment.payment_id,
                "current_status": payment.status
            }
        )

    advice = advisor.analyze(
        failure_code=payment.failure_code,
        amount=payment.amount,
        payment_method=payment.payment_method,
        retry_count=payment.retry_count
    )

    policy_decision = engine.decide(
        failure_code=payment.failure_code,
        retry_count=payment.retry_count
    )

    return {
        "payment_id": payment.payment_id,
        "amount": payment.amount,
        "payment_method": payment.payment_method,
        "failure_code": payment.failure_code,
        "retry_count": payment.retry_count,

        "ai_advice": {
            "diagnosis": advice.diagnosis,
            "recommended_action": advice.recommended_action,
            "reasoning": advice.reasoning,
            "risk_level": advice.risk_level
        },

        "policy_decision": {
            "action": policy_decision.action,
            "allowed": policy_decision.allowed,
            "reason": policy_decision.reason
        },

        "recommendation_matches_policy": (
            advice.recommended_action == policy_decision.action
        )
    }

@router.post("/razorpay/order/{payment_id}")
def create_razorpay_order(
    payment_id: str,
    db: Session = Depends(get_db)
):

    payment = (
        db.query(Payment)
        .filter(Payment.payment_id == payment_id)
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail=f"Payment {payment_id} not found"
        )

    if payment.status != "failed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Razorpay recovery order can only be created for failed payments",
                "payment_id": payment.payment_id,
                "current_status": payment.status
            }
        )

    try:
        order = razorpay_service.create_order(
            amount_rupees=payment.amount,
            receipt=f"recovery_{payment.payment_id}"
        )

        return {
            "recoverai_payment_id": payment.payment_id,
            "amount_rupees": payment.amount,
            "razorpay_order_id": order["id"],
            "razorpay_status": order["status"],
            "currency": order["currency"],
            "amount_paise": order["amount"]
        }

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Failed to create Razorpay test order",
                "error": str(error)
            }
        )


@router.post("/razorpay/verify")
def verify_razorpay_payment(
    request: RazorpayVerificationRequest,
    db: Session = Depends(get_db)
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.payment_id == request.recoverai_payment_id
        )
        .first()
    )

    if not payment:
        raise HTTPException(
            status_code=404,
            detail="RecoverAI payment not found"
        )

    if payment.status != "failed":
        raise HTTPException(
            status_code=400,
            detail="Payment is no longer awaiting recovery"
        )

    verified = razorpay_service.verify_payment_signature(
        razorpay_order_id=request.razorpay_order_id,
        razorpay_payment_id=request.razorpay_payment_id,
        razorpay_signature=request.razorpay_signature
    )

    if not verified:
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay payment signature"
        )

    razorpay_order = razorpay_service.fetch_order(
        request.razorpay_order_id
    )

    razorpay_payment = razorpay_service.fetch_payment(
        request.razorpay_payment_id
    )

    payment.status = "success"
    payment.recovery_status = "recovered"
    payment.recovered_amount = payment.amount

    audit = RecoveryAudit(
        payment_id=payment.payment_id,
        failure_code=payment.failure_code,
        recommended_action="RAZORPAY_CHECKOUT",
        action_allowed=True,
        decision_reason=(
            "Payment recovery confirmed through "
            "Razorpay Test Mode signature verification"
        ),
        recovery_result="RECOVERED",
        recovered_amount=payment.amount,
        processed_at=datetime.utcnow()
    )

    db.add(audit)
    db.commit()
    db.refresh(payment)

    return {
        "verified": True,
        "recoverai_payment_id": payment.payment_id,
        "razorpay_payment_id": request.razorpay_payment_id,
        "razorpay_order_id": request.razorpay_order_id,
        "status": payment.status,
        "recovery_status": payment.recovery_status,
        "recovered_amount": payment.recovered_amount
    }


@router.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):

    raw_body = await request.body()

    received_signature = request.headers.get(
        "X-Razorpay-Signature"
    )

    event_id = request.headers.get(
        "x-razorpay-event-id"
    )

    webhook_secret = os.getenv(
        "RAZORPAY_WEBHOOK_SECRET"
    )

    if not webhook_secret:
        raise HTTPException(
            status_code=500,
            detail="Webhook secret not configured"
        )

    if not received_signature:
        raise HTTPException(
            status_code=400,
            detail="Missing Razorpay webhook signature"
        )

    expected_signature = hmac.new(
        webhook_secret.encode(),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        received_signature
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid webhook signature"
        )

    payload = json.loads(raw_body)

    event_type = payload.get("event")

    payment_entity = (
        payload
        .get("payload", {})
        .get("payment", {})
        .get("entity", {})
    )

    return {
        "received": True,
        "event_id": event_id,
        "event": event_type,
        "razorpay_payment_id": payment_entity.get("id"),
        "status": payment_entity.get("status")
    }