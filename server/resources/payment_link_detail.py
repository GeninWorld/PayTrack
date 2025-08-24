from flask_restful import Resource, request
from flask import current_app
from flask_jwt_extended import jwt_required
from models import db, PaymentLinks, Transaction


class PaymentLinkDetailResource(Resource):
    @jwt_required()
    def get(self, link_token):
        """
        Fetch a single payment link by token and its transactions (paginated with cursor).
        Uses caching for performance.
        """
        cache = current_app.cache

        # ---------------------------
        # 1. Fetch PaymentLink (cache it longer since metadata rarely changes)
        # ---------------------------
        cache_key_link = f"payment_link:{link_token}"
        payment_link_data = None

        if cache:
            payment_link_data = cache.get(cache_key_link)

        if not payment_link_data:
            payment_link = PaymentLinks.query.filter_by(link_token=link_token).first()
            if not payment_link:
                return {"error": "Payment link not found"}, 404

            payment_link_data = payment_link.to_dict("http://example.com")  # Replace with actual frontend URL

            if cache:
                cache.set(cache_key_link, payment_link_data, timeout=60 * 10)  # cache for 10 minutes
        else:
            # hydrate a lightweight object with just id for querying transactions
            payment_link = PaymentLinks.query.filter_by(link_token=link_token).first()

        # ---------------------------
        # 2. Pagination setup
        # ---------------------------
        limit = int(request.args.get("limit", 10))   # default 10
        cursor = request.args.get("cursor")          # cursor = transaction.created_at (ISO string)

        cache_key_txn = f"payment_link:{link_token}:txns:{cursor or 'first'}:{limit}"
        transactions_data = None

        if cache:
            transactions_data = cache.get(cache_key_txn)

        if not transactions_data:
            query = Transaction.query.filter_by(payment_link_id=payment_link.id).order_by(Transaction.created_at.desc())

            if cursor:
                query = query.filter(Transaction.created_at < cursor)

            transactions = query.limit(limit + 1).all()

            has_more = len(transactions) > limit
            next_cursor = None
            if has_more:
                next_cursor = transactions[-1].created_at.isoformat()
                transactions = transactions[:limit]

            transactions_data = {
                "transactions": [t.to_dict() for t in transactions],
                "pagination": {
                    "limit": limit,
                    "next_cursor": next_cursor,
                    "has_more": has_more,
                }
            }

            if cache:
                cache.set(cache_key_txn, transactions_data, timeout=30)  # short TTL cache for transactions

        # ---------------------------
        # 3. Return response
        # ---------------------------
        return {
            "payment_link": payment_link_data,
            "transactions": transactions_data["transactions"],
            "pagination": transactions_data["pagination"]
        }, 200
