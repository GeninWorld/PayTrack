from flask import redirect, jsonify, url_for, request
from flask_restful import Resource
from flask_dance.contrib.google import google
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from models import db, User, Tenant, TenantConfig
from flask_bcrypt import Bcrypt
import phonenumbers
from urllib.parse import urlencode
import random
import re

def slugify_username(name):
    """Convert tenant name into username-like link_id."""
    # lowercase, replace spaces with "_", remove bad chars
    base = re.sub(r'[^a-zA-Z0-9_]', '', name.lower().replace(" ", "_"))

    if not base:
        base = "tenant"

    return base
bcrypt = Bcrypt()
class GoogleAuth(Resource):
    def get(self):
        if not google.authorized:
            return redirect(url_for("google.login"))

        resp = google.get("/oauth2/v2/userinfo")
        if not resp.ok:
            return {"error": "Failed to fetch user info from Google"}, 400

        user_info = resp.json()
        email = user_info["email"]
        name = user_info.get("name", "")
        avatar_url = user_info.get("picture", "")

        # Check if user exists, else create
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(email=email, name=name, avatar_url=avatar_url)
            db.session.add(user)
            db.session.commit()

        # Create JWT token
        
        access_token = create_access_token(identity=str(user.id))
        
        # for the frontend to handle the redirect
        # This is optional, you can return the token directly instead
        # redirect_url = f"https://blubbb.vercel.app/auth?{urlencode({'token': access_token, 'email': user.email, 'id': user.id, 'name': user.name, 'avatar_url': user.avatar_url})}"
        # return redirect(redirect_url)
        return {"access_token": access_token, "user": {"id": str(user.id), "email": user.email, "avatar_url":user.avatar_url, "name": user.name}}, 200



class TenantLogin(Resource):
    def post(self):
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return {"error": "Email and password are required"}, 400

        tenant = Tenant.query.filter_by(email=email).first()
        if not tenant or not tenant.password:
            return {"error": "Invalid credentials"}, 401

        if not bcrypt.check_password_hash(tenant.password, password):
            return {"error": "Invalid credentials"}, 401

        access_token = create_access_token(identity=str(tenant.id))
        return {"access_token": access_token, "user": {"id": str(tenant.id), "email": tenant.email, "name": tenant.name}}, 200
    
class TenantSignup(Resource):
    def post(self):
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")
        name = data.get("name")

        if not email or not password or not name:
            return {"error": "Email, password, and name are required"}, 400

        if Tenant.query.filter_by(email=email).first():
            return {"error": "Email already registered"}, 400

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        tenant = Tenant(email=email, password=hashed_password, name=name)
        account_no = str(random.randint(100000, 999999))
        base_link_id = slugify_username(name)

        # Ensure link_id is unique
        link_id = base_link_id
        counter = 1
        while TenantConfig.query.filter_by(link_id=link_id).first():
            link_id = f"{base_link_id}_{counter}"
            counter += 1

        tenant_config = TenantConfig(
            tenant=tenant,
            account_no=account_no,
            link_id=link_id
        )

        db.session.add(tenant)
        db.session.add(tenant_config)
        db.session.commit()  # ✅ One commit only


        access_token = create_access_token(identity=str(tenant.id))
        return {"access_token": access_token, "user": {"id": str(tenant.id), "email": tenant.email, "name": tenant.name}}, 201