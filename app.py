from flask import Flask, jsonify, request, current_app
from flask_restful import Api, Resource
from flask_jwt_extended import (JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt)  
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from flasgger import Swagger
from config import Config
from sqlalchemy.orm import Session
from database import Base, engine, get_db
import models, schemas, auth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

Base.metadata.create_all(bind=engine)

app = Flask(__name__)
app.config.from_object("config.Config")

limiter = Limiter(get_remote_address, app=app)

api = Api(app)
jwt = JWTManager(app)
bcrypt = Bcrypt(app)
#CORS setup
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:3000"]}},
    supports_credentials=False,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)
swagger = Swagger(app, template_file="swagger.yaml")

app.config["JWT_TOKEN_LOCATION"] = ["headers"]
app.config["JWT_HEADER_NAME"] = "Authorization"
app.config["JWT_HEADER_TYPE"] = "Bearer"
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2MB

@app.before_request
def require_api_key():
    # Allow Swagger and health endpoint without API key
    if request.path.startswith("/apidocs") or request.path == "/health":
        return

    api_key = request.headers.get("X-API-KEY")

    if not api_key or api_key != current_app.config["API_KEY"]:
        return jsonify({"error": "Invalid or missing API Key"}), 401

#Security headers
@app.after_request
def set_security_headers(response):
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Cache-Control"] = "no-store"
    return response

# Helper: Role Check
def role_required(required_role):
    def decorator(func):
        @jwt_required()
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            db: Session = next(get_db())
            user = db.query(models.User).filter(models.User.username == identity).first()
            db.close()

            if not user:
                return jsonify({"error": "User not found"}), 404

            if user.is_banned:
                return jsonify({"message": "User banned"}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Authentication endpoints
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    user = schemas.UserCreate(**data)
    hashed_pw = auth.hash_password(user.password)

    db: Session = next(get_db())
    db_user = models.User(username=user.username, email=user.email, password=hashed_pw)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    db.close()

    return jsonify({"id": db_user.id, "username": db_user.username, "email": db_user.email, "message": "User registered"}), 201

@app.route("/auth/login", methods=["POST"])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    user = schemas.UserLogin(**data)

    db: Session = next(get_db())
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    db.close()

    if not db_user or not auth.verify_password(user.password, db_user.password):
        return jsonify({"error": "Invalid credentials"}), 401
    
    if request.content_type != "application/json":
        return jsonify({"error": "Unsupported Media Type"}), 415

    access_token = create_access_token(
        identity=db_user.username,
        additional_claims={"role": db_user.role}
    )

    return jsonify({"access_token": access_token}), 200
# Myth endpoints

@app.route("/myths", methods=["POST"])
@jwt_required()
def submit_myth():
    identity = get_jwt_identity()
    claims = get_jwt()
    
    if claims.get("role") not in ["submitter", "admin"]:
        return jsonify({"error": "Forbidden"}), 403
    
    if request.content_type != "application/json":
        return jsonify({"error": "Unsupported Media Type"}), 415

    data = request.get_json()
    myth = schemas.MythCreate(**data)

    if "badword" in myth.description.lower():
        return jsonify({"detail": "Inappropriate content"}), 400

    db: Session = next(get_db())

    user = db.query(models.User).filter(models.User.username == identity).first()

    if user.is_banned:
        db.close()
        return jsonify({"error": "User banned"}), 403

    db_myth = models.Myth(**myth.dict(), submitter_id=user.id)
    db.add(db_myth)

    # ✅ Add audit log
    log = models.AuditLog(
        user_id=user.id,
        action="submit_myth",
        myth_id=None
    )
    db.add(log)

    db.commit()
    db.refresh(db_myth)
    db.close()

    return jsonify({
        "id": db_myth.id,
        "title": db_myth.title,
        "message": "Myth submitted"
    }), 201

@app.route("/myths", methods=["GET"])
def list_myths():
    db: Session = next(get_db())
    myths = db.query(models.Myth).all()
    db.close()
    # Convert SQLAlchemy objects to dicts
    myth_list = [{"id": m.id, "title": m.title, "description": m.description} for m in myths]
    return jsonify(myth_list)

@app.route("/myths/<int:myth_id>/vote", methods=["POST"])
@jwt_required()
def vote_myth(myth_id):
    identity = get_jwt_identity()
    claims = get_jwt()

    data = request.get_json()
    vote_data = schemas.VoteCreate(**data)

    db: Session = next(get_db())
    user = db.query(models.User).filter(models.User.username == identity).first()

    existing_vote = db.query(models.Vote).filter_by(
        myth_id=myth_id,
        user_id=user.id
    ).first()

    if existing_vote:
        db.close()
        return jsonify({"error": "Already voted"}), 400

    vote = models.Vote(
        myth_id=myth_id,
        user_id=user.id,
        vote=vote_data.vote
    )

    db.add(vote)

    # Audit log
    log = models.AuditLog(
        user_id=user.id,
        action="vote_myth",
        myth_id=myth_id
    )
    db.add(log)

    db.commit()
    db.close()

    return jsonify({"message": "Vote recorded"}), 200

@app.route("/myths/<int:myth_id>", methods=["DELETE"])
@jwt_required()
def delete_myth(myth_id):
    claims = get_jwt()

    if claims.get("role") not in ["moderator", "admin"]:
        return jsonify({"error": "Forbidden"}), 403

    db: Session = next(get_db())
    myth = db.query(models.Myth).filter(models.Myth.id == myth_id).first()

    if not myth:
        db.close()
        return jsonify({"error": "Not found"}), 404

    db.delete(myth)

    log = models.AuditLog(
        user_id=None,
        action="delete_myth",
        myth_id=myth_id
    )
    db.add(log)

    db.commit()
    db.close()

    return jsonify({"message": "Deleted"}), 200

@app.route("/admin/logs", methods=["GET"])
@jwt_required()
def view_logs():
    claims = get_jwt()

    if claims.get("role") != "admin":
        return jsonify({"error": "Admins only"}), 403

    db: Session = next(get_db())
    logs = db.query(models.AuditLog).all()
    db.close()

    return jsonify([
        {
            "user_id": l.user_id,
            "action": l.action,
            "myth_id": l.myth_id,
            "timestamp": l.timestamp
        } for l in logs
    ])

@jwt.unauthorized_loader
def unauthorized_callback(callback):
    return jsonify({"error": "Missing or invalid token"}), 401


@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return jsonify({"error": "Token expired"}), 401


@jwt.invalid_token_loader
def invalid_token_callback(callback):
    return jsonify({"error": "Invalid token"}), 401

# Global error handler
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# Main
if __name__ == '__main__':
    app.run(debug=False)
