import logging
import json
import requests
from celery_app import celery
from models import db, Tenant, TenantConfig
from decimal import Decimal
from flask import current_app

logger = logging.getLogger(__name__)

def serialize_tenant(tenant, config):
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "wallet_balance": float(tenant.wallet_balance or 0),
        "config": {
            "account_no": config.account_no,
            "link_id": config.link_id,
            "callback_url": config.api_callback_url
        }
    }

@celery.task(bind=True, name="workers.send_webhook", max_retries=3, default_retry_delay=30)
def send_webhook(
    self,
    tenant_id,
    request_id,
    status,
    amount,
    request_ref,
    currency,
    transaction_ref=None,
    remarks=None,
    created_at=None,
    event_type="COLLECTION"  # New parameter: COLLECTION or DISBURSEMENT
):
    """
    Celery task to send webhook (collection or disbursement) to tenant.
    """
    try:
        with current_app.app_context():
            cache = current_app.cache

            # --- CACHE CHECK ---
            cached = cache.get(f"tenant:{tenant_id}") if tenant_id else None
            if cached:
                tenant_data = json.loads(cached)
            else:
                result = (
                    db.session.query(Tenant, TenantConfig)
                    .join(TenantConfig)
                    .filter(Tenant.id == tenant_id)
                    .first()
                )
                if not result:
                    logger.warning(f"Tenant {tenant_id} not found in DB")
                    return {"error": "Tenant not found"}, 404

                tenant, config = result
                tenant_data = serialize_tenant(tenant, config)

                # Save to cache
                cache.set(f"tenant:{tenant_id}", json.dumps(tenant_data), timeout=3600)

        # --- BASE PAYLOAD ---
        webhook_payload = {
            "event_type": event_type.upper(),   # <---- include type
            "tenant_id": str(tenant_id),
            "request_id": str(request_id),
            "status": status,
            "amount": str(amount) if isinstance(amount, Decimal) else amount,
            "request_ref": str(request_ref),
            "currency": currency,
            "created_at": created_at.isoformat(),
        }

        # --- CONDITIONAL FIELDS ---
        if event_type.upper() == "COLLECTION":
            if status.upper() == "FAILED":
                webhook_payload["remarks"] = remarks or "Collection failed"
            elif status.upper() == "SUCCESS":
                webhook_payload["transaction_ref"] = transaction_ref

        elif event_type.upper() == "DISBURSEMENT":
            if status.upper() == "FAILED":
                webhook_payload["remarks"] = remarks or "Disbursement failed"
            elif status.upper() == "SUCCESS":
                webhook_payload["transaction_ref"] = transaction_ref
                # you can also add destination account details if available
                # webhook_payload["to_account"] = "..." 

        callback_url = tenant_data["config"].get("callback_url")
        if not callback_url:
            logger.info(f"No callback_url configured for tenant {tenant_id}")
            return {"message": "No callback URL configured"}, 200

        # --- SEND WEBHOOK ---
        resp = requests.post(callback_url, json=webhook_payload, timeout=10)
        resp.raise_for_status()

        logger.info(
            f"{event_type} webhook sent successfully to tenant {tenant_id} at {callback_url}"
        )
        return {"message": f"{event_type} webhook sent successfully"}, 200

    except Exception as e:
        logger.exception(f"Failed to send {event_type} webhook for tenant {tenant_id}: {e}")
        raise self.retry(exc=e)
