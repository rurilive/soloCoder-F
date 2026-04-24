from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
from app.database import get_db
from app.models import User, Question
from app.models.question import QuestionType, Difficulty
from app.security import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter(prefix="/api/questions", tags=["题库管理"])


class QuestionCreate(BaseModel):
    question_type: str
    difficulty: str = Difficulty.MEDIUM
    subject: str
    chapter: Optional[str] = None
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: str
    points: int = 1
    explanation: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionUpdate(BaseModel):
    question_type: Optional[str] = None
    difficulty: Optional[str] = None
    subject: Optional[str] = None
    chapter: Optional[str] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    points: Optional[int] = None
    explanation: Optional[str] = None
    tags: Optional[List[str]] = None


class QuestionResponse(BaseModel):
    id: int
    question_type: str
    difficulty: str
    subject: str
    chapter: Optional[str]
    question_text: str
    options: Optional[List[str]]
    correct_answer: str
    points: int
    explanation: Optional[str]
    tags: Optional[List[str]]
    created_by: Optional[int]

    class Config:
        from_attributes = True

    @classmethod
    def from_orm(cls, obj: Question):
        data = {
            "id": obj.id,
            "question_type": obj.question_type,
            "difficulty": obj.difficulty,
            "subject": obj.subject,
            "chapter": obj.chapter,
            "question_text": obj.question_text,
            "correct_answer": obj.correct_answer,
            "points": obj.points,
            "explanation": obj.explanation,
            "created_by": obj.created_by,
        }
        
        if obj.options:
            data["options"] = json.loads(obj.options)
        else:
            data["options"] = None
        
        if obj.tags:
            data["tags"] = obj.tags.split(",") if obj.tags else None
        else:
            data["tags"] = None
        
        return cls(**data)


@router.get("/", response_model=List[QuestionResponse])
def list_questions(
    skip: int = 0,
    limit: int = 100,
    subject: Optional[str] = None,
    question_type: Optional[str] = None,
    difficulty: Optional[str] = None,
    chapter: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Question)
    
    if subject:
        query = query.filter(Question.subject == subject)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if chapter:
        query = query.filter(Question.chapter == chapter)
    if search:
        query = query.filter(Question.question_text.contains(search))
    
    questions = query.offset(skip).limit(limit).all()
    return [QuestionResponse.from_orm(q) for q in questions]


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    return QuestionResponse.from_orm(question)


@router.post("/", response_model=QuestionResponse)
def create_question(
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    new_question = Question(
        question_type=question_data.question_type,
        difficulty=question_data.difficulty,
        subject=question_data.subject,
        chapter=question_data.chapter,
        question_text=question_data.question_text,
        options=json.dumps(question_data.options) if question_data.options else None,
        correct_answer=question_data.correct_answer,
        points=question_data.points,
        explanation=question_data.explanation,
        tags=",".join(question_data.tags) if question_data.tags else None,
        created_by=current_user.id
    )
    
    db.add(new_question)
    db.commit()
    db.refresh(new_question)
    
    return QuestionResponse.from_orm(new_question)


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    if question_data.question_type is not None:
        question.question_type = question_data.question_type
    if question_data.difficulty is not None:
        question.difficulty = question_data.difficulty
    if question_data.subject is not None:
        question.subject = question_data.subject
    if question_data.chapter is not None:
        question.chapter = question_data.chapter
    if question_data.question_text is not None:
        question.question_text = question_data.question_text
    if question_data.options is not None:
        question.options = json.dumps(question_data.options)
    if question_data.correct_answer is not None:
        question.correct_answer = question_data.correct_answer
    if question_data.points is not None:
        question.points = question_data.points
    if question_data.explanation is not None:
        question.explanation = question_data.explanation
    if question_data.tags is not None:
        question.tags = ",".join(question_data.tags) if question_data.tags else None
    
    db.commit()
    db.refresh(question)
    
    return QuestionResponse.from_orm(question)


@router.delete("/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在")
    
    db.delete(question)
    db.commit()
    
    return {"message": "题目删除成功"}


@router.get("/stats/subjects")
def get_subjects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    subjects = db.query(Question.subject).distinct().all()
    return {"subjects": [s[0] for s in subjects]}


@router.get("/stats/chapters/{subject}")
def get_chapters(
    subject: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chapters = db.query(Question.chapter).filter(
        Question.subject == subject,
        Question.chapter.isnot(None)
    ).distinct().all()
    return {"chapters": [c[0] for c in chapters]}
