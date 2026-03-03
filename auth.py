from flask import request, jsonify, current_app
from functools import wraps
from jose import jwt, JWTError
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(password, hashed):
    return pwd_context.verify(password, hashed)


def create_access_token(data: dict, expires_delta: timedelta = None):
    SECRET_KEY = current_app.config["SECRET_KEY"]
    ALGORITHM = "HS256"

    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=60)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str):
    try:
        SECRET_KEY = current_app.config["SECRET_KEY"]
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        return None


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"detail": "Missing or invalid token"}), 401

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)

        if not payload:
            return jsonify({"detail": "Invalid or expired token"}), 401

        return f(payload, *args, **kwargs)

    return decorated