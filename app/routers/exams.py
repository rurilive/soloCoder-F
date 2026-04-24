from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import json
import random
from app.database import get_db
from app.models import User, Question, Exam, ExamQuestion, ExamAnswer, MonitorRecord
from app.models.question import QuestionType, Difficulty
from app.models.exam import ExamStatus, ExamAnswerStatus
from app.models.user import UserRole
from app.security import get_current_user, require_role

router = APIRouter(prefix="/api/exams", tags=["考试管理"])


class StrategyRule(BaseModel):
    question_type: str
    difficulty: Optional[str] = None
    count: int
    points: int


class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject: str
    duration: int = 60
    total_points: int = 100
    pass_score: int = 60
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    shuffle_questions: bool = False
    shuffle_options: bool = False
    allow_review: bool = True
    show_score: bool = True
    strategy_rules: List[StrategyRule]


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    duration: Optional[int] = None
    total_points: Optional[int] = None
    pass_score: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    shuffle_questions: Optional[bool] = None
    shuffle_options: Optional[bool] = None
    allow_review: Optional[bool] = None
    show_score: Optional[bool] = None


class ExamResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    subject: str
    duration: int
    total_points: int
    pass_score: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    shuffle_questions: bool
    shuffle_options: bool
    allow_review: bool
    show_score: bool
    status: str
    created_by: int
    strategy_config: Optional[str]

    class Config:
        from_attributes = True


class ExamQuestionResponse(BaseModel):
    id: int
    exam_question_id: int
    question_type: str
    question_text: str
    options: Optional[List[str]]
    points: int
    order: int

    class Config:
        from_attributes = True


class AnswerSubmit(BaseModel):
    exam_question_id: int
    answer_text: str


class ManualGrade(BaseModel):
    score: float
    comment: Optional[str] = None


def generate_exam_questions(db: Session, exam: Exam, strategy_rules: List[StrategyRule]):
    selected_question_ids = set()
    current_order = 0
    
    for rule in strategy_rules:
        query = db.query(Question).filter(
            Question.question_type == rule.question_type,
            Question.subject == exam.subject
        )
        
        if rule.difficulty:
            query = query.filter(Question.difficulty == rule.difficulty)
        
        if selected_question_ids:
            query = query.filter(Question.id.notin_(selected_question_ids))
        
        questions = query.all()
        
        if len(questions) < rule.count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"题目数量不足：{rule.question_type} 类型（{rule.difficulty or '所有难度'}）需要 {rule.count} 题，实际只有 {len(questions)} 题可用"
            )
        
        new_selected = random.sample(questions, rule.count)
        
        for q in new_selected:
            selected_question_ids.add(q.id)
            current_order += 1
            options_shuffled = None
            
            if exam.shuffle_options and q.options:
                options = json.loads(q.options)
                random.shuffle(options)
                options_shuffled = json.dumps(options)
            
            exam_question = ExamQuestion(
                exam_id=exam.id,
                question_id=q.id,
                question_order=current_order,
                points=rule.points,
                options_shuffled=options_shuffled
            )
            
            db.add(exam_question)
    
    db.commit()


@router.get("/", response_model=List[ExamResponse])
def list_exams(
    status: Optional[str] = None,
    subject: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Exam)
    
    if current_user.role == UserRole.STUDENT:
        query = query.filter(Exam.status == ExamStatus.PUBLISHED)
    else:
        query = query.filter(Exam.created_by == current_user.id)
    
    if status:
        query = query.filter(Exam.status == status)
    if subject:
        query = query.filter(Exam.subject == subject)
    
    exams = query.all()
    return exams


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if current_user.role == UserRole.STUDENT and exam.status != ExamStatus.PUBLISHED:
        raise HTTPException(status_code=403, detail="无权访问该考试")
    
    return exam


@router.post("/", response_model=ExamResponse)
def create_exam(
    exam_data: ExamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    new_exam = Exam(
        title=exam_data.title,
        description=exam_data.description,
        subject=exam_data.subject,
        duration=exam_data.duration,
        total_points=exam_data.total_points,
        pass_score=exam_data.pass_score,
        start_time=exam_data.start_time,
        end_time=exam_data.end_time,
        shuffle_questions=exam_data.shuffle_questions,
        shuffle_options=exam_data.shuffle_options,
        allow_review=exam_data.allow_review,
        show_score=exam_data.show_score,
        strategy_config=json.dumps([r.model_dump() for r in exam_data.strategy_rules]),
        created_by=current_user.id,
        status=ExamStatus.DRAFT
    )
    
    db.add(new_exam)
    db.commit()
    db.refresh(new_exam)
    
    generate_exam_questions(db, new_exam, exam_data.strategy_rules)
    
    db.refresh(new_exam)
    return new_exam


@router.put("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: int,
    exam_data: ExamUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if exam.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权修改该考试")
    
    if exam.status != ExamStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能修改草稿状态的考试")
    
    update_data = exam_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(exam, key, value)
    
    db.commit()
    db.refresh(exam)
    
    return exam


@router.post("/{exam_id}/publish")
def publish_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if exam.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权发布该考试")
    
    if exam.status != ExamStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能发布草稿状态的考试")
    
    if not exam.exam_questions:
        raise HTTPException(status_code=400, detail="考试没有题目，无法发布")
    
    exam.status = ExamStatus.PUBLISHED
    db.commit()
    
    return {"message": "考试发布成功"}


@router.delete("/{exam_id}")
def delete_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if exam.created_by != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权删除该考试")
    
    if exam.status != ExamStatus.DRAFT:
        raise HTTPException(status_code=400, detail="只能删除草稿状态的考试")
    
    db.delete(exam)
    db.commit()
    
    return {"message": "考试删除成功"}


@router.get("/{exam_id}/questions", response_model=List[ExamQuestionResponse])
def get_exam_questions(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if current_user.role == UserRole.STUDENT:
        if exam.status != ExamStatus.PUBLISHED:
            raise HTTPException(status_code=403, detail="无权访问该考试")
        
        existing_answers = db.query(ExamAnswer).filter(
            ExamAnswer.exam_id == exam_id,
            ExamAnswer.user_id == current_user.id
        ).first()
        
        if not existing_answers:
            for eq in exam.exam_questions:
                answer = ExamAnswer(
                    exam_id=exam_id,
                    exam_question_id=eq.id,
                    user_id=current_user.id,
                    started_at=datetime.utcnow()
                )
                db.add(answer)
            db.commit()
    
    exam_questions = db.query(ExamQuestion).filter(
        ExamQuestion.exam_id == exam_id
    ).order_by(ExamQuestion.question_order).all()
    
    if exam.shuffle_questions and current_user.role == UserRole.STUDENT:
        random.shuffle(exam_questions)
    
    result = []
    for eq in exam_questions:
        q = eq.question
        options = None
        
        if eq.options_shuffled:
            options = json.loads(eq.options_shuffled)
        elif q.options:
            options = json.loads(q.options)
        
        result.append(ExamQuestionResponse(
            id=q.id,
            exam_question_id=eq.id,
            question_type=q.question_type,
            question_text=q.question_text,
            options=options,
            points=eq.points,
            order=eq.question_order
        ))
    
    return result


@router.post("/{exam_id}/submit")
def submit_exam(
    exam_id: int,
    answers: List[AnswerSubmit],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if exam.status != ExamStatus.PUBLISHED:
        raise HTTPException(status_code=400, detail="考试未发布")
    
    for answer_data in answers:
        exam_answer = db.query(ExamAnswer).filter(
            ExamAnswer.exam_id == exam_id,
            ExamAnswer.exam_question_id == answer_data.exam_question_id,
            ExamAnswer.user_id == current_user.id
        ).first()
        
        if not exam_answer:
            raise HTTPException(status_code=400, detail="答案记录不存在")
        
        exam_answer.answer_text = answer_data.answer_text
        exam_answer.submitted_at = datetime.utcnow()
        
        eq = exam_answer.exam_question
        q = eq.question
        
        is_auto_graded = False
        auto_score = 0.0
        
        if q.question_type in [QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.TRUE_FALSE]:
            is_auto_graded = True
            if answer_data.answer_text == q.correct_answer:
                auto_score = eq.points
                exam_answer.is_correct = True
            else:
                exam_answer.is_correct = False
            
            exam_answer.auto_score = auto_score
            exam_answer.total_score = auto_score
            exam_answer.status = ExamAnswerStatus.AUTO_GRADED
        
        db.commit()
    
    return {"message": "答案提交成功"}


@router.get("/{exam_id}/results")
def get_exam_results(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="考试不存在")
    
    if current_user.role == UserRole.STUDENT:
        if not exam.show_score:
            raise HTTPException(status_code=403, detail="成绩未开放查看")
        
        answers = db.query(ExamAnswer).filter(
            ExamAnswer.exam_id == exam_id,
            ExamAnswer.user_id == current_user.id
        ).all()
        
        total_score = sum(a.total_score for a in answers)
        is_passed = total_score >= exam.pass_score
        
        return {
            "exam_id": exam_id,
            "total_score": total_score,
            "max_score": exam.total_points,
            "pass_score": exam.pass_score,
            "is_passed": is_passed,
            "answers": [
                {
                    "exam_question_id": a.exam_question_id,
                    "answer_text": a.answer_text,
                    "is_correct": a.is_correct,
                    "auto_score": a.auto_score,
                    "manual_score": a.manual_score,
                    "total_score": a.total_score,
                    "status": a.status,
                    "grader_comment": a.grader_comment
                }
                for a in answers
            ]
        }
    else:
        user_answers = db.query(ExamAnswer).filter(
            ExamAnswer.exam_id == exam_id
        ).all()
        
        user_scores = {}
        for a in user_answers:
            if a.user_id not in user_scores:
                user_scores[a.user_id] = 0
            user_scores[a.user_id] += a.total_score
        
        results = []
        for user_id, score in user_scores.items():
            user = db.query(User).filter(User.id == user_id).first()
            results.append({
                "user_id": user_id,
                "username": user.username if user else None,
                "real_name": user.real_name if user else None,
                "score": score,
                "max_score": exam.total_points,
                "is_passed": score >= exam.pass_score
            })
        
        return {"results": results}


@router.post("/{exam_id}/grade/{exam_question_id}")
def grade_subjective_question(
    exam_id: int,
    exam_question_id: int,
    grade_data: ManualGrade,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.TEACHER))
):
    exam_answer = db.query(ExamAnswer).filter(
        ExamAnswer.exam_id == exam_id,
        ExamAnswer.exam_question_id == exam_question_id
    ).first()
    
    if not exam_answer:
        raise HTTPException(status_code=404, detail="答案记录不存在")
    
    eq = exam_answer.exam_question
    if grade_data.score > eq.points:
        raise HTTPException(status_code=400, detail="分数不能超过题目总分")
    
    exam_answer.manual_score = grade_data.score
    exam_answer.total_score = grade_data.score
    exam_answer.grader_comment = grade_data.comment
    exam_answer.graded_at = datetime.utcnow()
    exam_answer.status = ExamAnswerStatus.MANUALLY_GRADED
    
    db.commit()
    
    return {"message": "评分成功"}
