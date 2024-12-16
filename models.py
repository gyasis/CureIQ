# models.py
from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

# Base class for SQLAlchemy models
Base = declarative_base()

class Question(Base):
    __tablename__ = 'questions'
    
    # Define columns for the questions table
    id = Column(Integer, primary_key=True)
    question_text = Column(Text, nullable=False, unique=True)
    options = Column(Text, nullable=False)  # Stored as JSON string
    correct_option = Column(String(255), nullable=False)
    subject = Column(String(100), nullable=False)
    sub_subject = Column(String(100), nullable=True)
    difficulty = Column(String(50), nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationship with UserPerformance
    performance = relationship("UserPerformance", back_populates="question", uselist=False)

class UserPerformance(Base):
    __tablename__ = 'user_performance'
    
    # Define columns for the user_performance table
    id = Column(Integer, primary_key=True)
    question_id = Column(Integer, ForeignKey('questions.id'), unique=True)
    last_seen = Column(DateTime, nullable=True)
    times_seen = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    times_incorrect = Column(Integer, default=0)
    average_response_time = Column(Float, default=0.0)  # In seconds
    next_review = Column(DateTime, nullable=True)
    current_rank = Column(Float, default=1.0)  # Lower rank = higher priority
    
    # New fields for trend analysis
    previous_times_correct = Column(Integer, default=0)
    previous_average_response_time = Column(Float, default=0.0)  # In seconds
    
    # Relationship with Question
    question = relationship("Question", back_populates="performance")
