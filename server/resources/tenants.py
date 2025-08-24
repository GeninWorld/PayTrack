from flask import request, current_app
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from models import db, Tenant, TenantConfig
import uuid
import random
import json
import re

def slugify_username(name):
    """Convert tenant name into username-like link_id."""
    # lowercase, replace spaces with "_", remove bad chars
    base = re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(" ", "_"))

    if not base:
        base = "tenant"

    return base


def serialize_tenant(tenant, config):
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "wallet_balance": float(tenant.wallet_balance or 0),
        "config": {
            "account_no": config.account_no,
            "link_id": config.link_id,
            "callback_url": config.api_callback_url
        }
    }


class TenantResource(Resource):
    @jwt_required()
    def post(self):
        """Create a new tenant quickly and efficiently."""
        data = request.get_json()
        name = data.get("name")

        if not name:
            return {"error": "Name is required"}, 400

        # Generate account + link id
        account_no = str(random.randint(100000, 999999))
        base_link_id = slugify_username(name)

        # Ensure link_id is unique
        link_id = base_link_id
        counter = 1
        while TenantConfig.query.filter_by(link_id=link_id).first():
            link_id = f"{base_link_id}_{counter}"
            counter += 1

        # Create tenant + config
        tenant = Tenant(name=name)
        tenant_config = TenantConfig(
            tenant=tenant,
            account_no=account_no,
            link_id=link_id
        )

        db.session.add(tenant)
        db.session.add(tenant_config)
        db.session.commit()  # ✅ One commit only

        tenant_data = serialize_tenant(tenant, tenant_config)

        # Cache (async could be even better, but keep simple for now)
        cache = current_app.cache
        cache.set(f"tenant:{tenant.id}", json.dumps(tenant_data), timeout=3600)

        index = cache.get("tenants:index")
        ids = json.loads(index) if index else []
        ids.append(str(tenant.id))
        cache.set("tenants:index", json.dumps(ids), timeout=3600)

        return tenant_data, 201


    @jwt_required()
    def get(self, tenant_id=None):
        """Get all tenants (cached) OR a single tenant."""
        cache = current_app.cache

        if tenant_id:
            # Try per-tenant cache
            cached = cache.get(f"tenant:{tenant_id}")
            if cached:
                return json.loads(cached), 200

            # Fallback to DB
            result = (
                db.session.query(Tenant, TenantConfig)
                .join(TenantConfig)
                .filter(Tenant.id == tenant_id)
                .first()
            )
            if not result:
                return {"error": "Tenant not found"}, 404

            tenant, config = result
            tenant_data = serialize_tenant(tenant, config)

            cache.set(f"tenant:{tenant.id}", json.dumps(tenant_data), timeout=3600)
            return tenant_data, 200

        # Fetch all tenants
        index = cache.get("tenants:index")
        tenants = []
        if index:
            ids = json.loads(index)
            # Bulk load cached tenants
            for tid in ids:
                cached = cache.get(f"tenant:{tid}")
                if cached:
                    tenants.append(json.loads(cached))

        # If cache miss (first load), query DB
        if not tenants:
            results = db.session.query(Tenant, TenantConfig).join(TenantConfig).all()
            ids = []
            for tenant, config in results:
                tenant_data = serialize_tenant(tenant, config)
                ids.append(str(tenant.id))
                tenants.append(tenant_data)
                cache.set(f"tenant:{tenant.id}", json.dumps(tenant_data), timeout=3600)
            cache.set("tenants:index", json.dumps(ids), timeout=3600)

        # Filtering
        name_filter = request.args.get("name")
        if name_filter:
            tenants = [t for t in tenants if name_filter.lower() in t["name"].lower()]

        return tenants, 200

    @jwt_required()
    def put(self, tenant_id):
        """Update tenant by ID."""
        data = request.get_json()
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        tenant.name = data.get("name", tenant.name)
        db.session.commit()

        tenant_config = TenantConfig.query.filter_by(tenant_id=tenant_id).first()
        if "account_no" in data:
            tenant_config.account_no = data["account_no"]
        if "callback_url" in data:
            tenant_config.api_callback_url = data["callback_url"]
        db.session.commit()

        tenant_data = serialize_tenant(tenant, tenant_config)

        # Update tenant cache only
        cache = current_app.cache
        cache.set(f"tenant:{tenant.id}", json.dumps(tenant_data), timeout=3600)

        return tenant_data, 200

    @jwt_required()
    def delete(self, tenant_id):
        """Delete tenant by ID."""
        tenant = Tenant.query.get(tenant_id)
        if not tenant:
            return {"error": "Tenant not found"}, 404

        TenantConfig.query.filter_by(tenant_id=tenant.id).delete()
        db.session.delete(tenant)
        db.session.commit()

        cache = current_app.cache
        cache.delete(f"tenant:{tenant.id}")

        # Update index
        index = cache.get("tenants:index")
        if index:
            ids = json.loads(index)
            ids = [tid for tid in ids if tid != str(tenant.id)]
            cache.set("tenants:index", json.dumps(ids), timeout=3600)

        return {"message": "Tenant deleted"}, 200
