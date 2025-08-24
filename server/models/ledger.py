from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class Ledger(db.Model):
    __tablename__ = 'ledger'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    gateway = db.Column(db.String(100))
    amount = db.Column(db.Numeric(12, 2))
    balance = db.Column(db.Numeric(12, 2))
    type = db.Column(db.String(50))  # e.g., "collection", "
    transaction_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('transaction.id'))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    