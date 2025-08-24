from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Transaction(db.Model):
    __tablename__ = 'transaction'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_ref = db.Column(db.String(255))
    tenant_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('tenants.id'))
    amount = db.Column(db.Numeric(12, 2))
    account_no = db.Column(db.String(50), nullable=True)
    gateway = db.Column(db.String(100))
    type = db.Column(db.String(50))
    status = db.Column(db.String(50))
    
    payment_link_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('payment_links.id'), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False)
    updated_at = db.Column(db.DateTime, nullable=True)

    ledger_entries = db.relationship("Ledger", backref="transaction", lazy=True)
    payment_links = db.relationship("PaymentLinks", backref="transaction", lazy=True)

    __table_args__ = (
        db.Index("idx_tenant_created", "tenant_id", "created_at"),
    )
    
    def to_dict(self):
        return {
            "id": str(self.id),
            "transaction_ref": self.transaction_ref,
            "tenant_id": str(self.tenant_id),
            "amount": str(self.amount),
            "account_no": self.account_no,
            "gateway": self.gateway,
            "type": self.type,
            "status": self.status,
            "payment_link_id": str(self.payment_link_id) if self.payment_link_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }