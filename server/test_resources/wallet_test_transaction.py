from flask_restful import Resource
from flask import request
from workers.wallet_logger import logg_wallet
import uuid

class WalletTransactionResource(Resource):
    def post(self, tenant_id):
        data = request.get_json()
        amount = data.get("amount")
        gateway = data.get("gateway", "mpesa")
        txn_type = data.get("type", "credit")  # "credit" or "debit"

        # Generate a unique transaction reference
        transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        # Call Celery task asynchronously
        logg_wallet.delay(
            tenant_id=tenant_id,
            amount=amount,
            transaction_ref=transaction_ref,
            gateway=gateway,
            txn_type=txn_type
        )

        return {
            "status": "processing",
            "transaction_ref": transaction_ref,
            "tenant_id": tenant_id,
            "amount": str(amount),
            "gateway": gateway,
            "type": txn_type
        }, 202
