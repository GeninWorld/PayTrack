from flask_restful import Resource, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app
from decimal import Decimal, InvalidOperation
from models import db, Tenant, PaymentLinks
import uuid
import logging



logger = logging.getLogger(__name__)


class PaymentLinkResource(Resource):
    @jwt_required()
    def post(self):
        """
        Create a new payment link for a tenant
        """
        data = request.get_json()
        tenant_id = data.get("tenant_id")
        amount = data.get("amount")
        currency = data.get("currency", "KES")
        description = data.get("description")

        if not tenant_id or not amount:
            return {"error": "Missing required fields"}, 400

        try:
            amount = Decimal(amount)
            if amount <= 0:
                raise ValueError
        except (InvalidOperation, ValueError, TypeError):
            return {"error": "Invalid amount format"}, 400

        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        payment_link = PaymentLinks(
            tenant_id=tenant_id,
            amount=amount,
            currency=currency,
            description=description,
        )
        payment_link.generate_link_token()

        db.session.add(payment_link)
        db.session.commit()

        # Invalidate cache for this tenant so GET fetches fresh data
        cache = current_app.cache
        if cache:
            cache.delete(f"payment_links:{tenant_id}")

        return {
            "message": "Payment link created successfully",
            "payment_link": payment_link.to_dict("http://example.com"),  # Replace with actual frontend URL
        }, 201

    @jwt_required()
    def get(self, tenant_id):
        """
        Fetch all payment links for a tenant (with caching)
        """
        if not tenant_id:
            return {"error": "Missing tenant_id"}, 400

        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        cache = current_app.cache
        cache_key = f"payment_links:{tenant_id}"
        links_data = None

        if cache:
            links_data = cache.get(cache_key)

        if not links_data:  # Cache miss → fetch from DB
            links = PaymentLinks.query.filter_by(tenant_id=tenant_id).all()
            links_data = [link.to_dict("https://localhost:3000") for link in links]

            if cache:
                cache.set(cache_key, links_data, timeout=60 * 5)  # cache for 5 min

        return {"payment_links": links_data}, 200
