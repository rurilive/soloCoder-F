import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel

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

Base.metadata.create_all(bind=engine)

app = FastAPI(title="幼儿成长记录系统")

app.mount("/static", StaticFiles(directory="static"), name="static")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=6555)
