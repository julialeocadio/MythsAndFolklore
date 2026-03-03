from pydantic import BaseModel, EmailStr, Field, ValidationError
from typing import Optional
from flask import request, jsonify

# --- Schemas ---
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class MythCreate(BaseModel):
    title: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    category: str
    latitude: float
    longitude: float

class VoteCreate(BaseModel):
    vote: str  # "authentic" or "fiction"

# --- Example usage in Flask route ---
def parse_schema(schema_class):
    """Helper to parse and validate JSON with Pydantic."""
    try:
        return schema_class(**request.get_json()), None
    except ValidationError as e:
        return None, e.json()