from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Tenant(db.Model):
    __tablename__ = 'tenants'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    wallet_balance = db.Column(db.Numeric(12, 2), default=0.00)

    transactions = db.relationship("Transaction", backref="tenant", lazy=True)
    api_key = db.relationship("ApiKey", back_populates="tenant", uselist=False)
    configs = db.relationship("TenantConfig", backref="tenant", lazy=True)
    api_collections = db.relationship(
        "ApiCollection",
        back_populates="tenant",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    