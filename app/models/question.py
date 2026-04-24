from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_type = Column(String(20), nullable=False)
    difficulty = Column(String(10), default=Difficulty.MEDIUM)
    subject = Column(String(100), nullable=False)
    chapter = Column(String(100))
    question_text = Column(Text, nullable=False)
    
    options = Column(Text)  # JSON格式存储选项
    correct_answer = Column(Text, nullable=False)
    points = Column(Integer, default=1)
    
    explanation = Column(Text)
    tags = Column(String(500))  # 逗号分隔的标签
    
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    exam_questions = relationship("ExamQuestion", back_populates="question")

    def __repr__(self):
        return f"<Question {self.id} - {self.question_type}>"
