# backend/models.py
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import Integer
from db import Base
import uuid

def uuid4str():
    return str(uuid.uuid4())

class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=uuid4str)
    original_filename = Column(String)
    status = Column(String, default="uploaded")  # uploaded|in_progress|completed

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=uuid4str)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    original_docx_path = Column(String)  # disk path
    working_docx_path = Column(String)   # disk path
    html_preview = Column(Text, default="")
    session = relationship("Session")

class Placeholder(Base):
    __tablename__ = "placeholders"
    id = Column(String, primary_key=True, default=uuid4str)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    key = Column(String)                 # e.g., [Company Name]
    normalized_key = Column(String)      # lower/slugged
    is_filled = Column(Boolean, default=False)
    value = Column(Text, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=uuid4str)
    session_id = Column(String, ForeignKey("sessions.id"), index=True)
    role = Column(String)     # 'user' | 'assistant' | 'system'
    content = Column(Text)

class Suggestion(Base):
    __tablename__ = "suggestions"
    id = Column(String, primary_key=True, default=uuid4str)
    session_id = Column(String, index=True)
    key = Column(String)                   # exact placeholder key
    value = Column(Text)                   # proposed value
    status = Column(String, default="pending")  # pending|accepted|rejected
