import os

import razorpay
from dotenv import load_dotenv


load_dotenv()


class RazorpayService:

    def __init__(self):
        key_id = os.getenv("RAZORPAY_KEY_ID")
        key_secret = os.getenv("RAZORPAY_KEY_SECRET")

        if not key_id or not key_secret:
            raise ValueError(
                "Razorpay API credentials are missing from .env"
            )

        self.client = razorpay.Client(
            auth=(key_id, key_secret)
        )

    def create_order(
        self,
        amount_rupees: int,
        receipt: str
    ):
        amount_paise = amount_rupees * 100

        order_data = {
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "payment_capture": 1
        }

        order = self.client.order.create(
            data=order_data
        )

        return order

    def verify_payment_signature(
        self,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str
    ) -> bool:

        try:
            self.client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature
            })

            return True

        except razorpay.errors.SignatureVerificationError:
            return False

    def fetch_order(self, order_id: str):
        return self.client.order.fetch(order_id)

    def fetch_payment(self, payment_id: str):
        return self.client.payment.fetch(payment_id)