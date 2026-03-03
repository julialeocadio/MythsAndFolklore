from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="viewer", nullable=False)
    is_banned = Column(Boolean, default=False)

    myths = relationship("Myth", back_populates="submitter")
    votes = relationship("Vote", back_populates="user")

class Myth(Base):
    __tablename__ = "myths"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    submitter_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    submitter = relationship("User", back_populates="myths")
    votes = relationship("Vote", back_populates="myth") 

class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    myth_id = Column(Integer, ForeignKey("myths.id"), nullable=False)
    vote = Column(String, nullable=False) #authentic or fiction

    user = relationship("User", back_populates="votes")
    myth = relationship("Myth", back_populates="votes") 

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)
    myth_id = Column(Integer, ForeignKey("myths.id"), nullable=False)
    timestamp = Column(String, default=datetime.utcnow().isoformat(), nullable=False)

    user = relationship("User")
    myth = relationship("Myth")