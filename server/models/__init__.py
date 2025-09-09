from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData

# Configure naming convention for constraints
metadata = MetaData(naming_convention={
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
})

db = SQLAlchemy(metadata=metadata)

# Import models so they are registered with SQLAlchemy
from models.user import User
from models.Tenant import Tenant
from models.Api_key import ApiKey   
from models.Transaction import Transaction
from models.TenantConfig import TenantConfig
from models.ledger import Ledger
from models.payment_link import PaymentLinks
from models.api_collection import ApiCollection
from models.api_disbursement import ApiDisbursement
from models.platform_wallet import Platform_wallet