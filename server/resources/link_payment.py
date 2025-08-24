from flask_restful import Resource, request
from models import Tenant, ApiCollection, db, PaymentLinks
from decimal import Decimal, InvalidOperation
from workers.initiate_mpesa import initiate_payment
from flask import current_app
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class LinkPayment(Resource):
    def post(self, link_token):
        """
        Trigger payment through a payment link (e.g. M-Pesa STK push).
        """
        data = request.get_json() or {}
        mpesa_number = data.get("mpesa_number")

        # -----------------------
        # Validate Mpesa number
        # -----------------------
        if not mpesa_number:
            return {"error": "Mpesa number required"}, 400

        if not mpesa_number.isdigit() or len(mpesa_number) < 10:
            return {"error": "Invalid Mpesa number format"}, 400

        # -----------------------
        # Fetch PaymentLink
        # -----------------------
        payment_link = PaymentLinks.query.filter_by(link_token=link_token).first()
        if not payment_link:
            return {"error": "Invalid payment link"}, 404

        if payment_link.status in ["paid", "expired"]:
            return {"error": f"Payment link is already {payment_link.status}"}, 400

        # -----------------------
        # Validate Amount
        # -----------------------
        try:
            amount = Decimal(payment_link.amount)
            if amount <= 0:
                return {"error": "Payment link has invalid amount"}, 400
        except (InvalidOperation, ValueError, TypeError):
            return {"error": "Invalid amount format"}, 400

        # -----------------------
        # Create Payment Request
        # -----------------------
        request_ref = uuid.uuid4().hex[:12]

        api_collection = ApiCollection(
            tenant_id=payment_link.tenant_id,    # FIXED: should map to tenant, not link
            amount=amount,
            currency=payment_link.currency,
            request_reference=request_ref,
            mpesa_number=mpesa_number,
            status="pending",
            payment_link_id=payment_link.id
        )

        try:
            db.session.add(api_collection)
            db.session.commit()
            logger.info(f"Payment request created: {api_collection.id} for link {link_token}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"DB error while creating payment request: {e}")
            return {"error": "Failed to create payment request"}, 500

        # -----------------------
        # Initiate payment asynchronously
        # -----------------------
        try:
            initiate_payment.delay(api_collection.id)
            logger.info(f"Queued payment initiation for request {api_collection.id}")
        except Exception as e:
            logger.error(f"Failed to queue payment initiation: {e}")
            return {
                "message": "Payment request created but failed to queue initiation",
                "request_id": str(api_collection.id),
                "status": "pending",
                "queue_error": str(e)
            }, 202
        return {
            "message": "Payment request created",
            "request_id": str(api_collection.id),
            "status": "pending"
        }, 202

    def initiate_worker(self, api_collection_id):
        """
        Utility to manually queue payment initiation.
        """
        try:
            with current_app.app_context():
                initiate_payment.delay(api_collection_id)
                logger.info(f"Queued manual initiation for payment request {api_collection_id}")
        except Exception as e:
            logger.error(f"Failed to queue manual initiation: {e}")
