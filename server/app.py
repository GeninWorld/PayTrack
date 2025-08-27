import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask
from flask_restful import Api
from flask_caching import Cache
from flask_jwt_extended import JWTManager
from flask_dance.contrib.google import make_google_blueprint
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_cors import CORS
import redis
import ssl

from config import Config
from models import db
from flask_restful import Resource

# Import your resources
from resources.auth import GoogleAuth
from resources.user_info import UserInfo
from resources.tenants import TenantResource
from resources.api_keys import ApiKeyResource, ApiKeyDetailResource
from resources.tenant_wallet import TenantWalletResource
from resources.payment_request import PaymentRequestResource
from resources.mpesa_callback import MpesaCallbackResource, MpesaDisbursementCallback
from resources.payment_request import PaymentStatusResource
from resources.payment_link_detail import PaymentLinkDetailResource
from resources.payment_link import PaymentLinkResource
from resources.link_payment import LinkPayment
from resources.payment_subscriber import PaymentSubscribe
from resources.disbursment_resource import DisbursmentRequestResource, DisbursmentStatus


# test resources
from test_resources.wallet_test_transaction import WalletTransactionResource
from test_resources.example_callback import TestWebhookResource

import sqlalchemy.pool
from celery_app import celery
from celery_app import init_celery
bcrypt = Bcrypt()


def create_app():
    app = Flask(__name__)
    
    app.config.from_object(Config)
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": sqlalchemy.pool.NullPool
    }

    # Extensions
    db.init_app(app)
    # ✅ All keys in UPPERCASE
    app.config.update(
        CELERY_BROKER_URL= app.config["CELERY_BROKER_URL"],
        CELERY_RESULT_BACKEND=app.config["CELERY_RESULT_BACKEND"],
        BROKER_USE_SSL={"ssl_cert_reqs": ssl.CERT_NONE},
        CELERY_REDIS_BACKEND_USE_SSL={"ssl_cert_reqs": ssl.CERT_NONE}
    )

    celery = init_celery(app)
    bcrypt.init_app(app)
    jwt = JWTManager()  
    jwt.init_app(app)
    migrate = Migrate(app, db)
    CORS(app)  # Enable CORS for all routes

    # ---- Caching (Flask-Caching) ----
    cache = Cache(app)              # Uses Config (CACHE_TYPE, etc.)
    app.cache = cache
    
    # ---- (Optional) direct Redis connection if you need it besides caching ----
    redis_url = app.config.get("CACHE_REDIS_URL")
    if redis_url:
        redis_connection_kwargs = {"decode_responses": True}
        if redis_url.startswith("rediss://"):
            redis_connection_kwargs["ssl"] = True
            redis_connection_kwargs["ssl_cert_reqs"] = ssl.CERT_NONE
        app.redis = redis.Redis.from_url(redis_url, **redis_connection_kwargs)
    
    # ---- Google OAuth blueprint ----
    google_bp = make_google_blueprint(
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        scope=[
            "openid",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/userinfo.profile",
        ],
        redirect_url="/auth/google",
    )
    app.register_blueprint(google_bp, url_prefix="/login")

    # ---- API resources ----
    api = Api(app)
    
    # Health check endpoint for Redis
    class HealthCheck(Resource):
        def get(self):
            try:
                app.redis.ping()
                return {"status": "healthy", "redis": "connected"}, 200
            except redis.ConnectionError:
                return {"status": "healthy", "redis": "disconnected"}, 200

    # Register all API resources (routes)
    api.add_resource(HealthCheck, '/health')

    api.add_resource(GoogleAuth, '/auth/google')
    # api.add_resource(Login, '/auth/signin')
    # api.add_resource(Register, '/auth/signup')
    
    api.add_resource(UserInfo, '/user')
    
    # tenants
    # to get the 
    api.add_resource(TenantResource, '/tenants', '/tenants/<string:tenant_id>') 
    
    # api keys
    api.add_resource(ApiKeyResource, '/tenants/key/create','/tenants/<string:tenant_id>/keys') #add and get all keys for a tenant
    api.add_resource(ApiKeyDetailResource, '/tenants/keys/<string:tenant_id>') #put and delete the keys   
    
    # wallets
    api.add_resource(TenantWalletResource, '/tenants/<string:tenant_id>/wallet')
    
    
    # payment callbacks
    
    api.add_resource(MpesaCallbackResource, '/payment/mpesa/call_back/<string:tenant_id>/<string:api_collection_id>')
    # test transaction
    api.add_resource(WalletTransactionResource, '/tenants/<string:tenant_id>/wallet/transactions')
    api.add_resource(TestWebhookResource, "/webhook/test")
    
    # api collection
    api.add_resource(PaymentRequestResource, '/api/payment_request')
    api.add_resource(PaymentStatusResource, '/api/payment/<string:collection_identifier>/status')
    
    # disbursment
    api.add_resource(DisbursmentRequestResource, '/api/disburse_request')
    api.add_resource(DisbursmentStatus, '/api/disburse/<string:collection_identifier>/status')
    api.add_resource(MpesaDisbursementCallback, '/payment/mpesa/disburse_call_back/<string:tenant_id>/<string:api_disbursement_id>/result')
    
    # payment links
    api.add_resource(PaymentLinkResource, '/payment/links', '/payment/links/<string:tenant_id>')
    api.add_resource(PaymentLinkDetailResource, '/payment/links/transactions/<string:link_token>')
    api.add_resource(LinkPayment, '/payment/links/<string:link_token>/pay')
    api.add_resource(PaymentSubscribe, "/subscribe/<string:request_id>")

    return app


# For gunicorn / production import
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)
