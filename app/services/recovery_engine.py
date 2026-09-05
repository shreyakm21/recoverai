from dataclasses import dataclass


@dataclass
class RecoveryDecision:
    action: str
    reason: str
    allowed: bool
    max_retries: int = 0


class RecoveryEngine:

    def decide(self, failure_code: str, retry_count: int) -> RecoveryDecision:

        if failure_code == "BANK_TIMEOUT":
            if retry_count >= 2:
                return RecoveryDecision(
                    action="STOP",
                    reason="Maximum retry limit reached for bank timeout",
                    allowed=False,
                    max_retries=2
                )

            return RecoveryDecision(
                action="RETRY",
                reason="Temporary bank timeout is likely recoverable",
                allowed=True,
                max_retries=2
            )

        if failure_code == "GATEWAY_ERROR":
            if retry_count >= 2:
                return RecoveryDecision(
                    action="STOP",
                    reason="Maximum retry limit reached for gateway error",
                    allowed=False,
                    max_retries=2
                )

            return RecoveryDecision(
                action="RETRY",
                reason="Gateway error may be temporary",
                allowed=True,
                max_retries=2
            )

        if failure_code == "INSUFFICIENT_FUNDS":
            return RecoveryDecision(
                action="SEND_REMINDER",
                reason="Immediate retry may fail again. Ask customer to retry later.",
                allowed=True
            )

        if failure_code == "CUSTOMER_ABANDONED":
            return RecoveryDecision(
                action="SEND_PAYMENT_LINK",
                reason="Customer abandoned checkout and may complete payment later.",
                allowed=True
            )

        if failure_code == "AUTH_FAILURE":
            return RecoveryDecision(
                action="REAUTHENTICATE",
                reason="Automatic retry is unsafe after authentication failure.",
                allowed=False
            )

        return RecoveryDecision(
            action="MANUAL_REVIEW",
            reason="Unknown failure type requires review.",
            allowed=False
        )