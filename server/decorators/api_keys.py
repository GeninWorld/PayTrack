from functools import wraps
from flask import request
from models import ApiKey

def api_key_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth or not auth.startswith("Bearer "):
            return {"error": "Missing or invalid Authorization header"}, 401

        token = auth.split(" ")[1]
        print(f"Received API key: {token}")
        # Check API key validity
        api_key = ApiKey.query.filter_by(key=token, revoked_at=None).first()
        if not api_key:
            return {"error": "Invalid or revoked API key"}, 403

        # Optionally pass tenant_id to the route
        kwargs["tenant_id"] = api_key.tenant_id
        return fn(*args, **kwargs)
    return wrapper


# from functools import wraps
# from flask import request
# from models import ApiKey

# def api_key_required(fn):
#     @wraps(fn)
#     def wrapper(*args, **kwargs):
#         auth = request.headers.get("Authorization")
#         if not auth or not auth.startswith("Bearer "):
#             return {"error": "Missing or invalid Authorization header"}, 401

#         token = auth.split(" ")[1]

#         # Check API key validity
#         api_key = ApiKey.query.filter_by(key=token, revoked_at=None).first()
#         if not api_key:
#             return {"error": "Invalid or revoked API key"}, 403

#         # Optionally pass tenant_id to the route
#         kwargs["tenant_id"] = api_key.tenant_id
#         return fn(*args, **kwargs)
#     return wrapper
