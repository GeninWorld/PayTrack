from flask_restful import Resource, request
from flask_jwt_extended import jwt_required
from models import Tenant, ApiDisbursement, db
from decimal import Decimal, InvalidOperation
from decorators.api_keys import api_key_required
from workers.initiate_mpesa import initiate_disbursement
from flask import current_app
import logging
from datetime import datetime, timedelta
import uuid
from typing import Optional

logger = logging.getLogger(__name__)


class DisbursmentRequestResource(Resource):

    @api_key_required
    def post(self, tenant_id=None):
        data = request.get_json() or {}
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        request_ref = data.get("request_ref")
        mpesa_number = data.get("mpesa_number", None)
        b2b_account = data.get("b2b_account", {})
        # -----------------------
        # Validate required fields
        # -----------------------
        if not amount or not request_ref:
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
        # Check wallet balance (amount + charges)
        # -----------------------

        if b2b_account:
            charge_val = get_b2b_business_charge(float(amount)) or 0
        else:
            charge_val = get_b2c_business_charge(float(amount)) or 0

        total_deduction = amount + Decimal(charge_val)

        if tenant.wallet_balance < total_deduction:
            return {
                "error": "Insufficient wallet balance",
                "wallet_balance": str(tenant.wallet_balance),
                "required_balance": str(total_deduction)
            }, 402  # 402 Payment Required is semantically correct

        # -----------------------
        # Check for duplicate request_ref first
        # -----------------------
        existing_request = ApiDisbursement.query.filter_by(request_reference=request_ref).first()
        if existing_request:
            return {"error": "Payment request with this reference already exists"}, 409

        # -----------------------
        # Create payment request
        # -----------------------
        disbursement = ApiDisbursement(
            tenant_id=tenant.id,
            amount=amount,
            currency=currency,
            request_reference=request_ref,
            mpesa_number=mpesa_number if mpesa_number else None,
            b2b_account=b2b_account if b2b_account else None,
            status="pending"
        )

        try:
            db.session.add(disbursement)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {"error": "Failed to create payment request: " + str(e)}, 500

        # -----------------------
        # Initiate payment asynchronously
        # -----------------------
        initiate_disbursement.delay(disbursement.id)

        return {
            "message": "Payment request created",
            "request_id": str(disbursement.id),
            "status": "pending",
            "deducted_amount": str(amount),
            "charges": str(charge_val),
            "total_required": str(total_deduction)
        }, 202

def get_b2c_business_charge(amount: float) -> Optional[int]:
    tariff_table = [
        (1, 49, 0),
        (50, 100, 0),
        (101, 500, 5),
        (501, 1000, 5),
        (1001, 1500, 5),
        (1501, 2500, 9),
        (2501, 3500, 9),
        (3501, 5000, 9),
        (5001, 7500, 11),
        (7501, 10000, 11),
        (10001, 15000, 11),
        (15001, 20000, 11),
        (20001, 25000, 13),
        (25001, 30000, 13),
        (30001, 35000, 13),
        (35001, 40000, 13),
        (40001, 45000, 13),
        (45001, 50000, 13),
        (50001, 70000, 13),
        (70001, 250000, 13),
    ]

    for min_amt, max_amt, business_charge in tariff_table:
        if min_amt <= amount <= max_amt:
            return business_charge

    return None  # Out of range
    

def get_b2b_business_charge(amount: float) -> Optional[int]:
    tariff_table = [
        (1, 49, 2),
        (50, 100, 3),
        (101, 500, 8),
        (501, 1000, 13),
        (1001, 1500, 18),
        (1501, 2500, 25),
        (2501, 3500, 30),
        (3501, 5000, 39),
        (5001, 7500, 48),
        (7501, 10000, 54),
        (10001, 15000, 63),
        (15001, 20000, 68),
        (20001, 25000, 74),
        (25001, 30000, 79),
        (30001, 35000, 90),
        (35001, 40000, 106),
        (40001, 45000, 110),
        (45001, 50000, 115),
        (50001, 70000, 115),
        (70001, 150000, 115),
        (150001, 250000, 115),
        (250001, 500000, 115),
        (500001, 1000000, 115),
        (1000001, 3000000, 115),
        (3000001, 5000000, 115),
        (5000001, 20000000, 115),
        (20000001, 50000000, 115),
    ]

    for min_amt, max_amt, business_charge in tariff_table:
        if min_amt <= amount <= max_amt:
            return business_charge

    return None  # Out of range


# Simple in-memory rate-limit dict (demo only)
_last_poll_times = {}


class DisbursmentStatus(Resource):

    @jwt_required
    def get(self, collection_identifier):
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
        disbursement = None
        try:
            uid = uuid.UUID(collection_identifier)
            disbursement = ApiDisbursement.query.filter_by(id=uid).first()
        except ValueError:
            # Not a UUID, treat as request_reference
            disbursement = ApiDisbursement.query.filter_by(request_reference=collection_identifier).first()

        if not disbursement:
            return {"error": "Payment request not found"}, 404

        # -------------------
        # Return limited info
        # -------------------
        return {
            "request_id": str(disbursement.id),
            "status": disbursement.status,
            "amount": str(disbursement.amount),
            "request_ref": disbursement.request_reference,
            "currency": disbursement.currency,
            "created_at": disbursement.created_at.isoformat(),
            "updated_at": disbursement.updated_at.isoformat()
        }, 200