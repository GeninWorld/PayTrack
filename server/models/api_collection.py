
from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class ApiCollection(db.Model):
    __tablename__ = 'api_collections'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('tenants.id'))
    request_reference = db.Column(db.String(255), nullable=False)
    mpesa_checkout_request_id = db.Column(db.String(255), nullable=True)
    mpesa_number = db.Column(db.String(20), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # e.g., "pending", "completed", "failed"
    payment_link_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('payment_links.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    tenant = db.relationship("Tenant", back_populates="api_collections")
    payment_link = db.relationship("PaymentLinks", backref="api_collections", lazy=True)

