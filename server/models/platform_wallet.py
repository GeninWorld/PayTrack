
from models import db
import uuid

class Platform_wallet(db.Model):
    __tablename__ = 'platform_wallet'

    id = db.Column(db.UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    update_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())