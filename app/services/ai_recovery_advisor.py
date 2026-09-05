from dataclasses import dataclass


@dataclass
class AIRecoveryAdvice:
    diagnosis: str
    recommended_action: str
    reasoning: str
    risk_level: str


class AIRecoveryAdvisor:

    def analyze(
        self,
        failure_code: str,
        amount: int,
        payment_method: str,
        retry_count: int
    ) -> AIRecoveryAdvice:

        return self._fallback_analysis(
            failure_code=failure_code,
            amount=amount,
            payment_method=payment_method,
            retry_count=retry_count
        )

    def _fallback_analysis(
        self,
        failure_code: str,
        amount: int,
        payment_method: str,
        retry_count: int
    ) -> AIRecoveryAdvice:

        if failure_code == "BANK_TIMEOUT":
            return AIRecoveryAdvice(
                diagnosis="Temporary bank-side connectivity issue",
                recommended_action="RETRY",
                reasoning=(
                    "The failure appears temporary and is usually "
                    "appropriate for a bounded retry."
                ),
                risk_level="LOW"
            )

        if failure_code == "GATEWAY_ERROR":
            return AIRecoveryAdvice(
                diagnosis="Temporary payment gateway failure",
                recommended_action="RETRY",
                reasoning=(
                    "A temporary gateway error may succeed on another "
                    "attempt, provided retry limits are respected."
                ),
                risk_level="LOW"
            )

        if failure_code == "INSUFFICIENT_FUNDS":
            return AIRecoveryAdvice(
                diagnosis="Customer balance is insufficient",
                recommended_action="SEND_REMINDER",
                reasoning=(
                    "Immediate retries are unlikely to help. "
                    "The customer should be given time before trying again."
                ),
                risk_level="MEDIUM"
            )

        if failure_code == "CUSTOMER_ABANDONED":
            return AIRecoveryAdvice(
                diagnosis="Customer left the checkout before completion",
                recommended_action="SEND_PAYMENT_LINK",
                reasoning=(
                    "The customer showed purchase intent, so a convenient "
                    "payment link may help complete the transaction."
                ),
                risk_level="LOW"
            )

        if failure_code == "AUTH_FAILURE":
            return AIRecoveryAdvice(
                diagnosis="Authentication or authorization failed",
                recommended_action="REAUTHENTICATE",
                reasoning=(
                    "Automatic retries should be avoided because the "
                    "customer may need to authenticate again."
                ),
                risk_level="HIGH"
            )

        return AIRecoveryAdvice(
            diagnosis="Unrecognized payment failure",
            recommended_action="MANUAL_REVIEW",
            reasoning=(
                "There is insufficient information for safe automatic recovery."
            ),
            risk_level="HIGH"
        )