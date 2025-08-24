from models import db, ApiCollection
from flask_restful import Resource
from flask import request, current_app, jsonify
from decimal import Decimal
import logging
from workers.wallet_logger import logg_wallet  # Celery task
from workers.send_webhook import send_webhook
logger = logging.getLogger(__name__)
from utils.subscribe_manager import push_to_queue
from datetime import datetime

class MpesaCallbackResource(Resource):
    def post(self, tenant_id, api_collection_id):
        """
        Handle M-Pesa STK callback.
        
        """
        data = request.get_json()

        try:
            stk = data.get('Body', {}).get('stkCallback', {})
            merchant_request_id = stk.get('MerchantRequestID')
            checkout_request_id = stk.get('CheckoutRequestID')
            result_code = stk.get('ResultCode')
            result_desc = stk.get('ResultDesc')

            if not tenant_id or not api_collection_id:
                logger.warning("Tenant ID or ApiCollection ID missing in callback")
                return {"ResultCode": 1, "ResultDesc": "Missing data"}, 400

            api_collection = ApiCollection.query.get(api_collection_id)
            if not api_collection:
                logger.warning(f"ApiCollection {api_collection_id} not found")
                return {"ResultCode": 1, "ResultDesc": "Collection not found"}, 404

            if result_code == 0:
                # Successful payment
                metadata = stk.get('CallbackMetadata', {}).get('Item', [])
                parsed_metadata = {item['Name']: item.get('Value') for item in metadata}

                amount = Decimal(str(parsed_metadata.get("Amount")))
                transaction_id = parsed_metadata.get("MpesaReceiptNumber")
                phone_number = parsed_metadata.get("PhoneNumber")
                transaction_date = parsed_metadata.get("TransactionDate")

                # Update status immediately
                api_collection.status = "completed"
                api_collection.mpesa_checkout_request_id = checkout_request_id
                db.session.commit()

                
                
                if api_collection.payment_link_id is not None:
                    # Delay wallet logging asynchronously
                    logg_wallet.delay(
                        tenant_id=tenant_id,
                        amount=float(amount),
                        transaction_ref=transaction_id,
                        gateway="mpesa",
                        txn_type="credit",
                        account_no=phone_number,
                        payment_link_id=api_collection.payment_link_id
                    )
                    status_msg = {
                        "tenant_id": tenant_id,
                        "request_id": str(api_collection.id),
                        "status": "success",
                        "amount": float(amount),
                        "request_ref": api_collection.request_reference,
                        "currency": "KES",
                        "created_at": api_collection.updated_at.isoformat(),
                        "transaction_ref": transaction_id
                    }

                    push_to_queue(str(api_collection.id), status_msg)
                    
                else:
                    # Delay wallet logging asynchronously
                    logg_wallet.delay(
                        tenant_id=tenant_id,
                        amount=float(amount),
                        transaction_ref=transaction_id,
                        gateway="mpesa",
                        account_no=phone_number,
                        txn_type="credit"
                    )
                    send_webhook.delay(
                        tenant_id=tenant_id,
                        request_id = api_collection.id,
                        status="success",
                        amount=float(amount),
                        request_ref = api_collection.request_reference,
                        currency = "KES",
                        created_at = api_collection.updated_at,
                        transaction_ref = transaction_id
                    )

                logger.info(f"STK Callback successful for collection {api_collection_id}")
                # Safaricom expects a JSON response immediately
                return {"ResultCode": 0, "ResultDesc": "Accepted"}, 200

            else:
                # Failed payment
                api_collection.status = "failed"
                db.session.commit()
                if api_collection.payment_link_id is None:
                    send_webhook.delay(
                        tenant_id=tenant_id,
                        request_id = api_collection.id,
                        status="failed",
                        amount=float(api_collection.amount),
                        request_ref = api_collection.request_reference,
                        currency = "KES",
                        created_at = api_collection.updated_at,
                        remarks = result_desc
                    )
                logger.info(f"STK Callback failed for collection {api_collection_id}: {result_desc}")
                return {"ResultCode": 0, "ResultDesc": "Accepted"}, 200  # still 0 so Safaricom stops retrying

        except Exception as e:
            db.session.rollback()
            current_app.logger.exception(f"M-Pesa callback error: {e}")
            return {"ResultCode": 1, "ResultDesc": "Internal server error"}, 500
