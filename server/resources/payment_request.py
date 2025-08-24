from flask_restful import Resource, request
from decorators.api_keys import api_key_required
from models import Tenant, ApiCollection, db
from decimal import Decimal, InvalidOperation
from workers.initiate_mpesa import initiate_payment
from flask import current_app
import logging
from datetime import datetime, timedelta
import uuid

logger = logging.getLogger(__name__)


class PaymentRequestResource(Resource):

    @api_key_required
    def post(self, tenant_id=None):
        data = request.get_json() or {}
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        request_ref = data.get("request_ref")
        mpesa_number = data.get("mpesa_number")

        # -----------------------
        # Validate required fields
        # -----------------------
        if not amount or not request_ref or not mpesa_number:
            return {"error": "Missing required fields"}, 400

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            return {"error": "Invalid amount format"}, 400

        # -----------------------
        # Fetch tenant
        # -----------------------
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        # -----------------------
        # Check for duplicate request_ref first
        # -----------------------
        existing_request = ApiCollection.query.filter_by(request_reference=request_ref).first()
        if existing_request:
            return {"error": "Payment request with this reference already exists"}, 409

        # -----------------------
        # Create payment request
        # -----------------------
        api_collection = ApiCollection(
            tenant_id=tenant.id,
            amount=amount,
            currency=currency,
            request_reference=request_ref,
            mpesa_number=mpesa_number,
            status="pending"
        )

        try:
            db.session.add(api_collection)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {"error": "Failed to create payment request: " + str(e)}, 500

        # -----------------------
        # Initiate payment asynchronously
        # -----------------------
        
        initiate_payment.delay(api_collection.id)

        return {
            "message": "Payment request created",
            "request_id": str(api_collection.id),
            "status": "pending"
        }, 202

    def initiate_worker(self, api_collection_id):
        try:
            with current_app.app_context():
                initiate_payment.delay(api_collection_id)
                logger.info("queing started for payment initiation")
        except Exception as e:
            logger.error(f"failed to queue initiattion: {e}")
            
            

# Simple in-memory rate-limit dict (demo only)
_last_poll_times = {}


class PaymentStatusResource(Resource):

    @api_key_required
    def get(self, collection_identifier, **kwargs):
        """
        Returns the status of a payment request.
        `collection_identifier` can be either the UUID (`id`) or `request_ref`.
        """

        # -------------------
        # Rate-limiting (basic example)
        # -------------------
        client_ip = request.remote_addr
        now = datetime.utcnow()
        last_poll = _last_poll_times.get((client_ip, collection_identifier))

        if last_poll and now - last_poll < timedelta(seconds=10):
            return {"error": "Polling too frequently. Use callback URL instead."}, 429

        _last_poll_times[(client_ip, collection_identifier)] = now

        # -------------------
        # Determine if identifier is UUID
        # -------------------
        api_collection = None
        try:
            uid = uuid.UUID(collection_identifier)
            api_collection = ApiCollection.query.filter_by(id=uid).first()
        except ValueError:
            # Not a UUID, treat as request_reference
            api_collection = ApiCollection.query.filter_by(request_reference=collection_identifier).first()

        if not api_collection:
            return {"error": "Payment request not found"}, 404

        # -------------------
        # Return limited info
        # -------------------
        return {
            "request_id": str(api_collection.id),
            "status": api_collection.status,
            "amount": str(api_collection.amount),
            "request_ref": api_collection.request_reference,
            "currency": api_collection.currency,
            "created_at": api_collection.created_at.isoformat(),
            "updated_at": api_collection.updated_at.isoformat()
        }, 200