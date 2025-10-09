from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class ApiDisbursement(db.Model):
    __tablename__ = 'api_disbursements'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('tenants.id'), nullable=False)
    request_reference = db.Column(db.String(255), nullable=False, unique=True)
    mpesa_transaction_id = db.Column(db.String(255), nullable=True)  # returned by Mpesa after payout
    mpesa_number = db.Column(db.String(20), nullable=True)  # phone number to send money to
    b2b_account = db.Column(db.JSON, nullable=True)  # Mpesa B2C account details
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False, default="KES")
    status = db.Column(db.String(50), nullable=False, default="pending")  # pending, processing, completed, failed
    remarks = db.Column(db.String(255), nullable=True)  # reason if failed or extra info
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(
        db.DateTime,
        default=db.func.current_timestamp(),
        onupdate=db.func.current_timestamp()
    )

    tenant = db.relationship("Tenant", back_populates="api_disbursements")
