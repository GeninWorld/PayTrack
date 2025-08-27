import logging
from celery_app import celery
from models import db
from utils.wallet import WalletService
from decimal import Decimal
from flask import current_app

logger = logging.getLogger(__name__)

@celery.task(bind=True, name="workers.wallet_logger", max_retries=3, default_retry_delay=30)
def logg_wallet(self, tenant_id, amount, transaction_ref, gateway="mpesa", txn_type="credit",account_no=None, payment_link_id=None):
    """
    Celery task to log a wallet transaction using the passed parameters.
    """
    try:
        with current_app.app_context():
            
            # Ensure amount is Decimal
            amount = Decimal(amount)

            # Log transaction via WalletService
            txn, ledger = WalletService.log_transaction(
                tenant_id=tenant_id,
                amount=amount,
                gateway=gateway,
                txn_type=txn_type,
                transaction_ref=transaction_ref,
                account_no=account_no,
                payment_link_id=payment_link_id,
            )

            logger.info(f"Wallet transaction logged successfully: txn_id={txn.transaction_ref}, tenant_id={tenant_id}")

    except Exception as e:
        db.session.rollback()
        logger.exception(f"Failed to log wallet transaction for tenant {tenant_id}: {e}")
        raise self.retry(exc=e)
