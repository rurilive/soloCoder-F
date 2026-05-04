import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from datetime import date, datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import math

os.makedirs("static", exist_ok=True)

SQLALCHEMY_DATABASE_URL = "mysql+pymysql://OnGMpLtFPNHcSbbtI7lu:lsTiBCoLk3cWvQKMZ4Mq@64.83.36.96:53306/cf?charset=utf8mb4"
engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

jinja_env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=True,
    cache_size=0,
)

def render_template(template_name: str, **context):
    template = jinja_env.get_template(template_name)
    return HTMLResponse(content=template.render(**context))

class Baby(Base):
    __tablename__ = "babies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    gender = Column(String(10))
    birth_date = Column(Date)
    birth_weight = Column(Float)
    birth_height = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    growth_records = relationship("GrowthRecord", back_populates="baby")
    vaccines = relationship("Vaccine", back_populates="baby")
    milestones = relationship("Milestone", back_populates="baby")

class GrowthRecord(Base):
    __tablename__ = "growth_records"
    
    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, ForeignKey("babies.id"))
    record_date = Column(Date)
    weight = Column(Float)
    height = Column(Float)
    head_circumference = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    baby = relationship("Baby", back_populates="growth_records")

class Vaccine(Base):
    __tablename__ = "vaccines"
    
    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, ForeignKey("babies.id"))
    vaccine_name = Column(String(100))
    vaccine_date = Column(Date)
    dose = Column(String(50), nullable=True)
    reaction = Column(Text, nullable=True)
    next_due_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    baby = relationship("Baby", back_populates="vaccines")

class Milestone(Base):
    __tablename__ = "milestones"
    
    id = Column(Integer, primary_key=True, index=True)
    baby_id = Column(Integer, ForeignKey("babies.id"))
    title = Column(String(100))
    description = Column(Text, nullable=True)
    milestone_date = Column(Date)
    category = Column(String(50))
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    baby = relationship("Baby", back_populates="milestones")

class GrowthStandard(Base):
    __tablename__ = "growth_standards"
    
    id = Column(Integer, primary_key=True, index=True)
    gender = Column(String(10), index=True)
    age_months = Column(Integer, index=True)
    measurement_type = Column(String(20), index=True)
    p3 = Column(Float)
    p15 = Column(Float)
    p50 = Column(Float)
    p85 = Column(Float)
    p97 = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="幼儿成长记录系统")

app.mount("/static", StaticFiles(directory="static"), name="static")

def calculate_age_months(birth_date: date, record_date: date) -> int:
    age_days = (record_date - birth_date).days
    return max(0, int(age_days / 30.44))

def calculate_bmi(weight: float, height: float) -> Optional[float]:
    if weight and height and height > 0:
        height_m = height / 100
        return round(weight / (height_m * height_m), 2)
    return None

def get_or_create_standard(db: Session, gender: str, age_months: int, measurement_type: str, 
                            p3: float, p15: float, p50: float, p85: float, p97: float):
    existing = db.query(GrowthStandard).filter(
        GrowthStandard.gender == gender,
        GrowthStandard.age_months == age_months,
        GrowthStandard.measurement_type == measurement_type
    ).first()
    if not existing:
        standard = GrowthStandard(
            gender=gender,
            age_months=age_months,
            measurement_type=measurement_type,
            p3=p3, p15=p15, p50=p50, p85=p85, p97=p97
        )
        db.add(standard)

def init_growth_standards(db: Session):
    if db.query(GrowthStandard).first():
        return
    
    boys_height = [
        (0, 46.3, 48.2, 50.0, 51.8, 53.7),
        (1, 50.7, 52.8, 54.7, 56.7, 58.6),
        (2, 54.0, 56.2, 58.1, 60.1, 62.1),
        (3, 56.7, 58.9, 61.1, 63.2, 65.4),
        (4, 58.9, 61.1, 63.3, 65.5, 67.7),
        (5, 60.8, 63.0, 65.2, 67.4, 69.6),
        (6, 62.4, 64.7, 66.9, 69.2, 71.5),
        (7, 63.9, 66.2, 68.4, 70.7, 73.0),
        (8, 65.2, 67.5, 69.8, 72.1, 74.4),
        (9, 66.5, 68.7, 71.0, 73.4, 75.7),
        (10, 67.6, 69.9, 72.3, 74.6, 77.0),
        (11, 68.7, 71.0, 73.4, 75.8, 78.2),
        (12, 69.7, 72.1, 74.5, 76.9, 79.3),
        (18, 73.6, 76.1, 78.5, 81.0, 83.5),
        (24, 76.9, 79.5, 82.1, 84.7, 87.3),
        (30, 79.7, 82.4, 85.1, 87.8, 90.5),
        (36, 82.3, 85.0, 87.8, 90.5, 93.2),
    ]
    
    boys_weight = [
        (0, 2.5, 2.9, 3.3, 3.8, 4.3),
        (1, 3.4, 3.9, 4.5, 5.0, 5.6),
        (2, 4.3, 4.9, 5.6, 6.3, 7.0),
        (3, 5.0, 5.7, 6.4, 7.2, 8.0),
        (4, 5.6, 6.2, 7.0, 7.8, 8.7),
        (5, 6.1, 6.7, 7.5, 8.4, 9.3),
        (6, 6.4, 7.1, 7.9, 8.8, 9.8),
        (7, 6.7, 7.4, 8.3, 9.2, 10.2),
        (8, 6.9, 7.7, 8.6, 9.5, 10.6),
        (9, 7.1, 7.9, 8.8, 9.8, 10.9),
        (10, 7.3, 8.2, 9.1, 10.2, 11.2),
        (11, 7.4, 8.4, 9.3, 10.4, 11.5),
        (12, 7.6, 8.6, 9.6, 10.6, 11.8),
        (18, 8.4, 9.6, 10.8, 12.0, 13.3),
        (24, 9.2, 10.5, 11.8, 13.2, 14.7),
        (30, 9.9, 11.3, 12.7, 14.1, 15.6),
        (36, 10.6, 12.0, 13.5, 15.1, 16.7),
    ]
    
    boys_head = [
        (0, 31.5, 32.8, 34.0, 35.2, 36.5),
        (1, 34.1, 35.4, 36.7, 38.0, 39.3),
        (2, 36.0, 37.3, 38.6, 39.9, 41.2),
        (3, 37.5, 38.8, 40.1, 41.4, 42.7),
        (4, 38.7, 40.0, 41.3, 42.6, 43.9),
        (5, 39.7, 41.0, 42.3, 43.5, 44.8),
        (6, 40.4, 41.7, 43.0, 44.2, 45.5),
        (7, 41.0, 42.3, 43.6, 44.8, 46.1),
        (8, 41.5, 42.8, 44.1, 45.3, 46.6),
        (9, 42.0, 43.2, 44.5, 45.7, 47.0),
        (10, 42.3, 43.6, 44.9, 46.1, 47.4),
        (11, 42.6, 43.9, 45.2, 46.4, 47.7),
        (12, 42.9, 44.2, 45.4, 46.7, 47.9),
        (18, 44.1, 45.3, 46.5, 47.8, 49.0),
        (24, 45.0, 46.2, 47.4, 48.6, 49.8),
        (30, 45.7, 46.9, 48.0, 49.2, 50.4),
        (36, 46.2, 47.4, 48.5, 49.7, 50.9),
    ]
    
    girls_height = [
        (0, 45.8, 47.6, 49.1, 50.8, 52.6),
        (1, 49.8, 51.7, 53.5, 55.4, 57.3),
        (2, 53.0, 55.0, 56.8, 58.8, 60.7),
        (3, 55.6, 57.8, 59.8, 61.8, 63.8),
        (4, 57.8, 60.0, 62.0, 64.1, 66.2),
        (5, 59.6, 61.8, 64.0, 66.1, 68.3),
        (6, 61.2, 63.4, 65.7, 67.9, 70.1),
        (7, 62.7, 64.9, 67.3, 69.6, 71.8),
        (8, 64.0, 66.3, 68.7, 71.0, 73.3),
        (9, 65.2, 67.6, 69.9, 72.3, 74.7),
        (10, 66.4, 68.7, 71.1, 73.5, 75.9),
        (11, 67.5, 69.8, 72.2, 74.7, 77.1),
        (12, 68.5, 70.8, 73.3, 75.7, 78.1),
        (18, 72.4, 74.9, 77.4, 79.9, 82.4),
        (24, 75.6, 78.2, 80.8, 83.3, 85.9),
        (30, 78.5, 81.1, 83.7, 86.4, 89.0),
        (36, 81.0, 83.7, 86.4, 89.1, 91.8),
    ]
    
    girls_weight = [
        (0, 2.4, 2.8, 3.2, 3.6, 4.0),
        (1, 3.2, 3.6, 4.2, 4.8, 5.5),
        (2, 4.0, 4.5, 5.1, 5.8, 6.5),
        (3, 4.6, 5.2, 5.8, 6.6, 7.4),
        (4, 5.1, 5.7, 6.4, 7.2, 8.0),
        (5, 5.5, 6.1, 6.9, 7.7, 8.6),
        (6, 5.8, 6.5, 7.3, 8.2, 9.1),
        (7, 6.1, 6.8, 7.6, 8.5, 9.5),
        (8, 6.3, 7.0, 7.8, 8.8, 9.8),
        (9, 6.5, 7.2, 8.1, 9.0, 10.1),
        (10, 6.7, 7.4, 8.3, 9.3, 10.4),
        (11, 6.9, 7.6, 8.5, 9.5, 10.6),
        (12, 7.0, 7.7, 8.7, 9.7, 10.8),
        (18, 7.8, 8.8, 9.9, 11.0, 12.2),
        (24, 8.5, 9.6, 10.8, 12.0, 13.3),
        (30, 9.1, 10.3, 11.6, 12.9, 14.2),
        (36, 9.7, 10.9, 12.3, 13.7, 15.1),
    ]
    
    girls_head = [
        (0, 31.3, 32.5, 33.7, 34.9, 36.1),
        (1, 33.7, 34.9, 36.1, 37.3, 38.5),
        (2, 35.4, 36.7, 37.9, 39.1, 40.3),
        (3, 36.8, 38.1, 39.3, 40.5, 41.8),
        (4, 38.0, 39.2, 40.5, 41.7, 42.9),
        (5, 38.9, 40.1, 41.4, 42.6, 43.8),
        (6, 39.7, 40.9, 42.1, 43.3, 44.6),
        (7, 40.3, 41.5, 42.7, 44.0, 45.2),
        (8, 40.8, 42.0, 43.3, 44.5, 45.7),
        (9, 41.3, 42.5, 43.7, 45.0, 46.2),
        (10, 41.7, 42.9, 44.1, 45.3, 46.6),
        (11, 42.0, 43.2, 44.5, 45.7, 46.9),
        (12, 42.3, 43.5, 44.7, 46.0, 47.2),
        (18, 43.4, 44.6, 45.8, 47.0, 48.3),
        (24, 44.2, 45.4, 46.6, 47.8, 49.0),
        (30, 44.8, 46.0, 47.2, 48.4, 49.6),
        (36, 45.3, 46.5, 47.7, 48.9, 50.1),
    ]
    
    for age, p3, p15, p50, p85, p97 in boys_height:
        get_or_create_standard(db, "男", age, "height", p3, p15, p50, p85, p97)
    
    for age, p3, p15, p50, p85, p97 in boys_weight:
        get_or_create_standard(db, "男", age, "weight", p3, p15, p50, p85, p97)
    
    for age, p3, p15, p50, p85, p97 in boys_head:
        get_or_create_standard(db, "男", age, "head_circumference", p3, p15, p50, p85, p97)
    
    for age, p3, p15, p50, p85, p97 in girls_height:
        get_or_create_standard(db, "女", age, "height", p3, p15, p50, p85, p97)
    
    for age, p3, p15, p50, p85, p97 in girls_weight:
        get_or_create_standard(db, "女", age, "weight", p3, p15, p50, p85, p97)
    
    for age, p3, p15, p50, p85, p97 in girls_head:
        get_or_create_standard(db, "女", age, "head_circumference", p3, p15, p50, p85, p97)
    
    db.commit()

def get_growth_standards_by_gender(db: Session, gender: str, measurement_type: str) -> List[GrowthStandard]:
    return db.query(GrowthStandard).filter(
        GrowthStandard.gender == gender,
        GrowthStandard.measurement_type == measurement_type
    ).order_by(GrowthStandard.age_months).all()

def get_baby_growth_data(db: Session, baby_id: int):
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        return None
    
    growth_records = db.query(GrowthRecord).filter(
        GrowthRecord.baby_id == baby_id
    ).order_by(GrowthRecord.record_date).all()
    
    data = {
        "baby": {
            "id": baby.id,
            "name": baby.name,
            "gender": baby.gender,
            "birth_date": str(baby.birth_date),
            "birth_weight": baby.birth_weight,
            "birth_height": baby.birth_height
        },
        "records": []
    }
    
    for record in growth_records:
        age_months = calculate_age_months(baby.birth_date, record.record_date)
        bmi = calculate_bmi(record.weight, record.height)
        
        data["records"].append({
            "id": record.id,
            "record_date": str(record.record_date),
            "age_months": age_months,
            "weight": record.weight,
            "height": record.height,
            "head_circumference": record.head_circumference,
            "bmi": bmi,
            "notes": record.notes
        })
    
    return data

def get_standard_data_for_chart(standards: List[GrowthStandard]):
    return {
        "age_months": [s.age_months for s in standards],
        "p3": [s.p3 for s in standards],
        "p15": [s.p15 for s in standards],
        "p50": [s.p50 for s in standards],
        "p85": [s.p85 for s in standards],
        "p97": [s.p97 for s in standards]
    }

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request, db: Session = Depends(get_db)):
    babies = db.query(Baby).all()
    return render_template("index.html", request=request, babies=babies)

@app.get("/baby/add", response_class=HTMLResponse)
async def add_baby_form(request: Request):
    return render_template("add_baby.html", request=request)

@app.post("/baby/add")
async def add_baby(
    request: Request,
    name: str = Form(...),
    gender: str = Form(...),
    birth_date: str = Form(...),
    birth_weight: float = Form(...),
    birth_height: float = Form(...),
    db: Session = Depends(get_db)
):
    baby = Baby(
        name=name,
        gender=gender,
        birth_date=date.fromisoformat(birth_date),
        birth_weight=birth_weight,
        birth_height=birth_height
    )
    db.add(baby)
    db.commit()
    db.refresh(baby)
    return RedirectResponse(url=f"/baby/{baby.id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/baby/{baby_id}", response_class=HTMLResponse)
async def view_baby(request: Request, baby_id: int, db: Session = Depends(get_db)):
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    
    growth_records = db.query(GrowthRecord).filter(GrowthRecord.baby_id == baby_id).order_by(GrowthRecord.record_date.desc()).all()
    vaccines = db.query(Vaccine).filter(Vaccine.baby_id == baby_id).order_by(Vaccine.vaccine_date.desc()).all()
    milestones = db.query(Milestone).filter(Milestone.baby_id == baby_id).order_by(Milestone.milestone_date.desc()).all()
    
    return render_template(
        "baby_detail.html",
        request=request,
        baby=baby,
        growth_records=growth_records,
        vaccines=vaccines,
        milestones=milestones
    )

@app.get("/growth/add/{baby_id}", response_class=HTMLResponse)
async def add_growth_form(request: Request, baby_id: int, db: Session = Depends(get_db)):
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    return render_template("add_growth.html", request=request, baby=baby)

@app.post("/growth/add/{baby_id}")
async def add_growth(
    request: Request,
    baby_id: int,
    record_date: str = Form(...),
    weight: float = Form(...),
    height: float = Form(...),
    head_circumference: Optional[float] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    growth_record = GrowthRecord(
        baby_id=baby_id,
        record_date=date.fromisoformat(record_date),
        weight=weight,
        height=height,
        head_circumference=head_circumference,
        notes=notes
    )
    db.add(growth_record)
    db.commit()
    return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/vaccine/add/{baby_id}", response_class=HTMLResponse)
async def add_vaccine_form(request: Request, baby_id: int, db: Session = Depends(get_db)):
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    return render_template("add_vaccine.html", request=request, baby=baby)

@app.post("/vaccine/add/{baby_id}")
async def add_vaccine(
    request: Request,
    baby_id: int,
    vaccine_name: str = Form(...),
    vaccine_date: str = Form(...),
    dose: Optional[str] = Form(None),
    reaction: Optional[str] = Form(None),
    next_due_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    vaccine = Vaccine(
        baby_id=baby_id,
        vaccine_name=vaccine_name,
        vaccine_date=date.fromisoformat(vaccine_date),
        dose=dose,
        reaction=reaction,
        next_due_date=date.fromisoformat(next_due_date) if next_due_date else None,
        notes=notes
    )
    db.add(vaccine)
    db.commit()
    return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/milestone/add/{baby_id}", response_class=HTMLResponse)
async def add_milestone_form(request: Request, baby_id: int, db: Session = Depends(get_db)):
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    return render_template("add_milestone.html", request=request, baby=baby)

@app.post("/milestone/add/{baby_id}")
async def add_milestone(
    request: Request,
    baby_id: int,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    milestone_date: str = Form(...),
    category: str = Form(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    milestone = Milestone(
        baby_id=baby_id,
        title=title,
        description=description,
        milestone_date=date.fromisoformat(milestone_date),
        category=category,
        notes=notes
    )
    db.add(milestone)
    db.commit()
    return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/growth/delete/{record_id}")
async def delete_growth(record_id: int, db: Session = Depends(get_db)):
    record = db.query(GrowthRecord).filter(GrowthRecord.id == record_id).first()
    if record:
        baby_id = record.baby_id
        db.delete(record)
        db.commit()
        return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)
    raise HTTPException(status_code=404, detail="记录不存在")

@app.post("/vaccine/delete/{vaccine_id}")
async def delete_vaccine(vaccine_id: int, db: Session = Depends(get_db)):
    vaccine = db.query(Vaccine).filter(Vaccine.id == vaccine_id).first()
    if vaccine:
        baby_id = vaccine.baby_id
        db.delete(vaccine)
        db.commit()
        return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)
    raise HTTPException(status_code=404, detail="疫苗记录不存在")

@app.post("/milestone/delete/{milestone_id}")
async def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    if milestone:
        baby_id = milestone.baby_id
        db.delete(milestone)
        db.commit()
        return RedirectResponse(url=f"/baby/{baby_id}", status_code=status.HTTP_303_SEE_OTHER)
    raise HTTPException(status_code=404, detail="里程碑不存在")

@app.get("/api/growth/{baby_id}", response_class=JSONResponse)
async def get_growth_chart_data(baby_id: int, db: Session = Depends(get_db)):
    init_growth_standards(db)
    
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    
    baby_growth_data = get_baby_growth_data(db, baby_id)
    
    height_standards = get_growth_standards_by_gender(db, baby.gender, "height")
    weight_standards = get_growth_standards_by_gender(db, baby.gender, "weight")
    head_standards = get_growth_standards_by_gender(db, baby.gender, "head_circumference")
    
    return {
        "baby": baby_growth_data["baby"],
        "records": baby_growth_data["records"],
        "standards": {
            "height": get_standard_data_for_chart(height_standards),
            "weight": get_standard_data_for_chart(weight_standards),
            "head_circumference": get_standard_data_for_chart(head_standards)
        }
    }

@app.get("/growth/chart/{baby_id}", response_class=HTMLResponse)
async def view_growth_chart(request: Request, baby_id: int, db: Session = Depends(get_db)):
    init_growth_standards(db)
    
    baby = db.query(Baby).filter(Baby.id == baby_id).first()
    if not baby:
        raise HTTPException(status_code=404, detail="宝宝不存在")
    
    return render_template("growth_chart.html", request=request, baby=baby)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6555)
