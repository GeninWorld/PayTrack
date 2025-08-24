from flask import redirect, jsonify, url_for, request
from flask_restful import Resource
from flask_dance.contrib.google import google
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from models import db, User
from flask_bcrypt import Bcrypt
import phonenumbers
from urllib.parse import urlencode

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
