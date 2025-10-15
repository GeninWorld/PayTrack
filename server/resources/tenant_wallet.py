from flask import request, current_app
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Tenant, TenantConfig, Transaction
from sqlalchemy import desc, func
from sqlalchemy.orm import selectinload
import json
from datetime import datetime


def serialize_transaction(tx):
    return {
        "id": str(tx.id),
        "transaction_ref": tx.transaction_ref,
        "amount": f"{tx.amount:.2f}" if tx.amount is not None else "0.00",
        "account_no": tx.account_no,
        "gateway": tx.gateway,
        "type": tx.type,
        "status": tx.status,
        "created_at": tx.created_at.isoformat() if tx.created_at else None,
        "updated_at": tx.updated_at.isoformat() if tx.updated_at else None,
    }


class TenantWalletResource(Resource):
    @jwt_required()
    def get(self, tenant_id):
        """
        Optimized tenant wallet endpoint:
        - Uses cache for aggregates + transactions
        - Efficient queries with limits + filters
        - Single tenant + config fetch with eager load
        """
        limit = min(int(request.args.get("limit", 20)), 100)
        cursor = request.args.get("cursor")
        cache = current_app.cache

        # 🔹 Check cache first
        cache_key = f"wallet:{tenant_id}:{cursor or 'first'}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached), 200

        # 🔹 Get tenant + config in one hit
        tenant = (
            db.session.query(Tenant)
            .options(selectinload(Tenant.configs))  # preload configs if relationship exists
            .filter_by(id=tenant_id)
            .first()
        )
        if not tenant:
            return {"error": "Tenant not found"}, 404

        config = tenant.configs[0] if hasattr(tenant, "configs") and tenant.configs else None

        # 🔹 Transactions (paginated)
        tx_query = (
            Transaction.query
            .filter(Transaction.tenant_id == tenant.id)
            .order_by(desc(Transaction.created_at))
        )

        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
                tx_query = tx_query.filter(Transaction.created_at < cursor_dt)
            except ValueError:
                return {"error": "Invalid cursor format, must be ISO datetime"}, 400

        transactions = tx_query.limit(limit + 1).all()
        has_more = len(transactions) > limit
        transactions = transactions[:limit]

        next_cursor = (
            transactions[-1].created_at.isoformat() if has_more and transactions else None
        )

        # 🔹 Aggregates (cache separately for 1 min)
        agg_cache_key = f"wallet:agg:{tenant_id}"
        totals = cache.get(agg_cache_key)
        if not totals:
            aggregates = (
                db.session.query(
                    Transaction.type,
                    func.coalesce(func.sum(Transaction.amount), 0).label("total")
                )
                .filter(Transaction.tenant_id == tenant.id)
                .group_by(Transaction.type)
                .all()
            )
            totals = {t: f"{total:.2f}" for t, total in aggregates}
            cache.set(agg_cache_key, totals, timeout=60)

        response = {
            "wallet": {
                "id": str(tenant.id),
                "name": tenant.name,
                "balance": f"{tenant.wallet_balance:.2f}",
                "account_no": config.account_no if config else None,
                "link_id": config.link_id if config else None,
                "totals": {
                    "credit": totals.get("credit", "0.00"),
                    "debit": totals.get("debit", "0.00"),
                }
            },
            "transactions": [serialize_transaction(tx) for tx in transactions],
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
                "limit": limit,
            },
        }

        # 🔹 Cache full response for 30s
        cache.set(cache_key, json.dumps(response), timeout=30)

        return response, 200



class TenantDashboardWalletResource(Resource):
    @jwt_required()
    def get(self):
        """
        Optimized tenant wallet endpoint:
        - Uses cache for aggregates + transactions
        - Efficient queries with limits + filters
        - Single tenant + config fetch with eager load
        """
        limit = min(int(request.args.get("limit", 20)), 100)
        cursor = request.args.get("cursor")
        tenant_id = get_jwt_identity()
        cache = current_app.cache

        # 🔹 Check cache first
        cache_key = f"wallet:{tenant_id}:{cursor or 'first'}:{limit}"
        cached = cache.get(cache_key)
        if cached:
            return json.loads(cached), 200

        # 🔹 Get tenant + config in one hit
        tenant = (
            db.session.query(Tenant)
            .options(selectinload(Tenant.configs))  # preload configs if relationship exists
            .filter_by(id=tenant_id)
            .first()
        )
        if not tenant:
            return {"error": "Tenant not found"}, 404

        config = tenant.configs[0] if hasattr(tenant, "configs") and tenant.configs else None

        # 🔹 Transactions (paginated)
        tx_query = (
            Transaction.query
            .filter(Transaction.tenant_id == tenant.id)
            .order_by(desc(Transaction.created_at))
        )

        if cursor:
            try:
                cursor_dt = datetime.fromisoformat(cursor)
                tx_query = tx_query.filter(Transaction.created_at < cursor_dt)
            except ValueError:
                return {"error": "Invalid cursor format, must be ISO datetime"}, 400

        transactions = tx_query.limit(limit + 1).all()
        has_more = len(transactions) > limit
        transactions = transactions[:limit]

        next_cursor = (
            transactions[-1].created_at.isoformat() if has_more and transactions else None
        )

        # 🔹 Aggregates (cache separately for 1 min)
        agg_cache_key = f"wallet:agg:{tenant_id}"
        totals = cache.get(agg_cache_key)
        if not totals:
            aggregates = (
                db.session.query(
                    Transaction.type,
                    func.coalesce(func.sum(Transaction.amount), 0).label("total")
                )
                .filter(Transaction.tenant_id == tenant.id)
                .group_by(Transaction.type)
                .all()
            )
            totals = {t: f"{total:.2f}" for t, total in aggregates}
            cache.set(agg_cache_key, totals, timeout=60)

        response = {
            "wallet": {
                "id": str(tenant.id),
                "name": tenant.name,
                "balance": f"{tenant.wallet_balance:.2f}",
                "account_no": config.account_no if config else None,
                "link_id": config.link_id if config else None,
                "payment_method": config.payment_method if config else None,
                "totals": {
                    "credit": totals.get("credit", "0.00"),
                    "debit": totals.get("debit", "0.00"),
                }
            },
            "transactions": [serialize_transaction(tx) for tx in transactions],
            "pagination": {
                "next_cursor": next_cursor,
                "has_more": has_more,
                "limit": limit,
            },
        }

        # 🔹 Cache full response for 30s
        cache.set(cache_key, json.dumps(response), timeout=30)

        return response, 200
