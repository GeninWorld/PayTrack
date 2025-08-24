from models import db
from sqlalchemy.dialects.postgresql import UUID
import uuid

class TenantConfig(db.Model):
    __tablename__ = 'tenant_config'

    tenant_id = db.Column(db.UUID(as_uuid=True), db.ForeignKey('tenants.id'), primary_key=True)
    account_no = db.Column(db.Integer, nullable=False)
    link_id = db.Column(db.String(255), nullable=False)
    api_callback_url = db.Column(db.String(255), nullable=True)
    
    __table_args__ = (
        db.Index("idx_tenant_config", "tenant_id"),
    )
