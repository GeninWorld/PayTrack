from models import db, Transaction, Ledger, Tenant
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from decimal import Decimal as decimal

class WalletService:

    @staticmethod
    def log_transaction(
        tenant_id,
        amount,
        gateway,
        txn_type,  # "credit" or "debit"
        status="success",
        transaction_ref=None,
        account_no=None,
        payment_link_id=None
    ):
        if not transaction_ref:
            transaction_ref = f"txn_{uuid.uuid4().hex[:12]}"

        try:
            amount = decimal(amount)

            # Lock tenant row to prevent concurrent updates
            tenant = (
                db.session.query(Tenant)
                .filter(Tenant.id == tenant_id)
                .with_for_update()
                .one_or_none()
            )
            if not tenant:
                raise ValueError("Tenant not found")

            # Fetch last ledger entry (no need to lock the ledger table)
            last_ledger = (
                db.session.query(Ledger)
                .order_by(Ledger.created_at.desc())
                .first()
            )

            previous_balance = last_ledger.balance if last_ledger else decimal("0.00")

            # Compute new balance
            if status != "success":
                new_balance = previous_balance
            else:
                if txn_type == "credit":
                    new_balance = previous_balance + amount
                    tenant.wallet_balance = tenant.wallet_balance + amount
                elif txn_type == "debit":
                    if previous_balance < amount:
                        raise ValueError("Insufficient wallet balance")
                    new_balance = previous_balance - amount
                    tenant.wallet_balance = tenant.wallet_balance - amount
                else:
                    raise ValueError("Invalid txn_type")

            db.session.add(tenant)

            # Create transaction
            txn = Transaction(
                id=uuid.uuid4(),
                transaction_ref=transaction_ref,
                tenant_id=tenant_id,
                amount=amount,
                account_no=account_no,
                gateway=gateway,
                type=txn_type,
                status=status,
                created_at=datetime.utcnow(),
                payment_link_id=payment_link_id
            )
            db.session.add(txn)

            # Create ledger entry
            ledger = Ledger(
                id=uuid.uuid4(),
                gateway=gateway,
                amount=amount,
                balance=new_balance,
                type=txn_type,
                transaction=txn,
                created_at=datetime.utcnow(),
            )
            db.session.add(ledger)

            db.session.commit()
            return txn, ledger

        except Exception as e:
            db.session.rollback()
            raise e
