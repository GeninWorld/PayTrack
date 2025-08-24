# models.py
from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid


class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    key = db.Column(db.String(255), primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime, nullable=True)
    tenant_id = db.Column(UUID(as_uuid=True), db.ForeignKey('tenants.id'))

    tenant = db.relationship("Tenant", back_populates="api_key")

    __table_args__ = (
        db.Index("idx_tenant_id", "tenant_id"),
    )
