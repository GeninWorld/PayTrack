from flask import request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_restful import Resource
from sqlalchemy.exc import IntegrityError
from models import db, Tenant, ApiKey
import uuid
from datetime import datetime
from flask import current_app   # import cache instance



class ApiKeyResource(Resource):
    @jwt_required()
    def post(self):
        cache = current_app.cache  
        data = request.get_json()
        tenant_id = data.get("tenant_id")

        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        if tenant.api_key:
            return {"error": "Tenant already has an API key"}, 400

        api_key = ApiKey(
            key=str(uuid.uuid4()),
            tenant_id=tenant.id,
            created_at=datetime.utcnow()
        )
        db.session.add(api_key)

        try:
            db.session.commit()
            # cache the new key
            cache.set(f"api_key:{tenant.id}", {
                "key": api_key.key,
                "created_at": api_key.created_at.isoformat(),
                "revoked_at": None
            }, timeout=3600)
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create API key"}, 500

        return {
            "tenant_id": str(tenant.id),
            "api_key": api_key.key,
            "created_at": api_key.created_at.isoformat()
        }, 201

    @jwt_required()
    def get(self, tenant_id):
        cache = current_app.cache  
        # 1. Try cache first
        cached_key = cache.get(f"api_key:{tenant_id}")
        if cached_key:
            return cached_key, 200

        # 2. Fallback to DB
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key found"}, 404

        api_key = tenant.api_key
        result = {
            "key": api_key.key,
            "created_at": api_key.created_at.isoformat(),
            "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None
        }

        # 3. Store in cache for next time
        cache.set(f"api_key:{tenant_id}", result, timeout=3600)

        return result, 200


class ApiKeyDetailResource(Resource):
    @jwt_required()
    def put(self, tenant_id):
        cache = current_app.cache  
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key to regenerate"}, 404

        api_key = tenant.api_key
        api_key.key = str(uuid.uuid4())
        api_key.created_at = datetime.utcnow()
        api_key.revoked_at = None

        try:
            db.session.commit()
            # update cache
            cache.set(f"api_key:{tenant_id}", {
                "key": api_key.key,
                "created_at": api_key.created_at.isoformat(),
                "revoked_at": None
            }, timeout=3600)
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to regenerate key"}, 500

        return {"new_key": api_key.key}, 200

    @jwt_required()
    def delete(self, tenant_id):
        cache = current_app.cache  
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key to revoke"}, 404

        tenant.api_key.revoked_at = datetime.utcnow()

        try:
            db.session.commit()
            # invalidate cache
            cache.delete(f"api_key:{tenant_id}")
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to revoke key"}, 500

        return {"message": "API key revoked"}, 200


class ApiKeyResourceTenant(Resource):
    @jwt_required()
    def post(self):
        cache = current_app.cache  
        data = request.get_json()

        action = data.get("action", "generate")
        if action != "generate":
            return {"error": "Invalid action"}, 400
        tenant_id = get_jwt_identity()

        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        if tenant.api_key:
            return {"error": "Tenant already has an API key"}, 400

        api_key = ApiKey(
            key=str(uuid.uuid4()),
            tenant_id=tenant.id,
            created_at=datetime.utcnow()
        )
        db.session.add(api_key)

        try:
            db.session.commit()
            # cache the new key
            cache.set(f"api_key:{tenant.id}", {
                "key": api_key.key,
                "created_at": api_key.created_at.isoformat(),
                "revoked_at": None
            }, timeout=3600)
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to create API key"}, 500

        return {
            "tenant_id": str(tenant.id),
            "api_key": api_key.key,
            "created_at": api_key.created_at.isoformat()
        }, 201

    @jwt_required()
    def get(self):
        cache = current_app.cache  
        tenant_id = get_jwt_identity()
        # 1. Try cache first
        cached_key = cache.get(f"api_key:{tenant_id}")
        if cached_key:
            return cached_key, 200

        # 2. Fallback to DB
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key found"}, 404

        api_key = tenant.api_key
        result = {
            "key": api_key.key,
            "created_at": api_key.created_at.isoformat(),
            "revoked_at": api_key.revoked_at.isoformat() if api_key.revoked_at else None
        }

        # 3. Store in cache for next time
        cache.set(f"api_key:{tenant_id}", result, timeout=3600)

        return result, 200


class ApiKeyDetailResourceTenant(Resource):
    @jwt_required()
    def patch(self):
        cache = current_app.cache  
        tenant_id = get_jwt_identity()
        data = request.get_json()
        action = data.get("action", "regenerate")
        if action != "regenerate":
            return {"error": "Invalid action"}, 400
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key to regenerate"}, 404

        api_key = tenant.api_key
        api_key.key = str(uuid.uuid4())
        api_key.created_at = datetime.utcnow()
        api_key.revoked_at = None

        try:
            db.session.commit()
            # update cache
            cache.set(f"api_key:{tenant_id}", {
                "key": api_key.key,
                "created_at": api_key.created_at.isoformat(),
                "revoked_at": None
            }, timeout=3600)
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to regenerate key"}, 500

        return {"new_key": api_key.key}, 200

    @jwt_required()
    def delete(self):
        tenant_id = get_jwt_identity()
        cache = current_app.cache  
        tenant = Tenant.query.get(tenant_id)
        if not tenant or not tenant.api_key:
            return {"error": "No API key to revoke"}, 404

        tenant.api_key.revoked_at = datetime.utcnow()

        try:
            db.session.commit()
            # invalidate cache
            cache.delete(f"api_key:{tenant_id}")
        except IntegrityError:
            db.session.rollback()
            return {"error": "Failed to revoke key"}, 500

        return {"message": "API key revoked"}, 200
