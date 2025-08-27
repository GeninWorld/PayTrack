from models import db, Transaction, Ledger, Tenant
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from decimal import Decimal as decimal
from typing import Optional

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
        payment_link_id=None,
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

            # Fetch last ledger entry
            last_ledger = (
                db.session.query(Ledger)
                .order_by(Ledger.created_at.desc())
                .first()
            )
            previous_balance = last_ledger.balance if last_ledger else decimal("0.00")

            new_balance = previous_balance
            charge_amount = decimal("0.00")

            # Compute new balance
            if status == "success":
                if txn_type == "credit":
                    new_balance += amount
                    tenant.wallet_balance += amount

                elif txn_type == "debit":
                    # Deduct amount
                    if previous_balance < amount:
                        raise ValueError("Insufficient wallet balance")
                    new_balance -= amount
                    tenant.wallet_balance -= amount

                    # Check for business charge
                    charge_val = get_b2c_business_charge(float(amount))
                    if charge_val:
                        charge_amount = decimal(charge_val)
                        if new_balance < charge_amount:
                            raise ValueError("Insufficient balance for charges")

                        new_balance -= charge_amount
                        tenant.wallet_balance -= charge_amount

                        # Add extra charge transaction
                        charge_txn = Transaction(
                            id=uuid.uuid4(),
                            transaction_ref=f"charge_{transaction_ref}",
                            tenant_id=tenant_id,
                            amount=charge_amount,
                            account_no=account_no,
                            gateway=gateway,
                            type="debit",
                            status="success",
                            created_at=datetime.utcnow(),
                            payment_link_id=payment_link_id,
                            charges=True,
                        )
                        db.session.add(charge_txn)

                        # Ledger for charge
                        charge_ledger = Ledger(
                            id=uuid.uuid4(),
                            gateway=gateway,
                            amount=charge_amount,
                            balance=new_balance,
                            type="debit",
                            transaction=charge_txn,
                            created_at=datetime.utcnow(),
                        )
                        db.session.add(charge_ledger)

                else:
                    raise ValueError("Invalid txn_type")

            db.session.add(tenant)

            # Create main transaction
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
                payment_link_id=payment_link_id,
                charges=False,
            )
            db.session.add(txn)

            # Create main ledger entry
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
