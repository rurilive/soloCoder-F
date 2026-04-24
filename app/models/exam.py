from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    STARTED = "started"
    ENDED = "ended"


class ExamAnswerStatus(str, enum.Enum):
    PENDING = "pending"
    AUTO_GRADED = "auto_graded"
    MANUALLY_GRADED = "manually_graded"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    subject = Column(String(100), nullable=False)
    duration = Column(Integer, default=60)  # 分钟
    
    total_points = Column(Integer, default=100)
    pass_score = Column(Integer, default=60)
    
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    
    shuffle_questions = Column(Boolean, default=False)
    shuffle_options = Column(Boolean, default=False)
    
    allow_review = Column(Boolean, default=True)
    show_score = Column(Boolean, default=True)
    
    strategy_config = Column(Text)  # JSON格式的组卷策略配置
    
    created_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String(20), default=ExamStatus.DRAFT)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="exams")
    exam_questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")
    answers = relationship("ExamAnswer", back_populates="exam")

    def __repr__(self):
        return f"<Exam {self.id} - {self.title}>"


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_order = Column(Integer, default=0)
    
    points = Column(Integer, default=1)
    options_shuffled = Column(Text)  # 打乱后的选项JSON

    exam = relationship("Exam", back_populates="exam_questions")
    question = relationship("Question", back_populates="exam_questions")
    answers = relationship("ExamAnswer", back_populates="exam_question")

    def __repr__(self):
        return f"<ExamQuestion {self.id}>"


class ExamAnswer(Base):
    __tablename__ = "exam_answers"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    exam_question_id = Column(Integer, ForeignKey("exam_questions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    answer_text = Column(Text)
    is_correct = Column(Boolean)
    auto_score = Column(Float, default=0)
    manual_score = Column(Float)
    total_score = Column(Float, default=0)
    
    status = Column(String(20), default=ExamAnswerStatus.PENDING)
    grader_comment = Column(Text)
    
    started_at = Column(DateTime)
    submitted_at = Column(DateTime)
    graded_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    exam = relationship("Exam", back_populates="answers")
    exam_question = relationship("ExamQuestion", back_populates="answers")
    user = relationship("User", back_populates="answers")

    def __repr__(self):
        return f"<ExamAnswer {self.id}>"
