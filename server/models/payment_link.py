from models import db
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

class PaymentLinks(db.Model):
    __tablename__ = 'payment_links'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'), nullable=False, index=True)
    link_token = db.Column(db.String(50), unique=True, nullable=False, index=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default="KES")
    description = db.Column(db.String(255))
    status = db.Column(db.String(50), default="pending", index=True)
    meta_data = db.Column(db.JSON, default={})
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)
    provider_reference = db.Column(db.String(100), nullable=True)

    def generate_link_token(self):
        self.link_token = uuid.uuid4().hex[:12]  

    def to_dict(self, frontend_url=None):
        """Serialize payment link object"""
        return {
            "id": str(self.id),
            "tenant_id": str(self.tenant_id),
            "link_token": self.link_token,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "link_url": f"{frontend_url}/pay/{self.link_token}" if frontend_url else None
        }
