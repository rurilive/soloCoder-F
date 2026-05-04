import pymysql
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Text, ForeignKey, DateTime
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from datetime import date, datetime

MYSQL_CONFIG = {
    'host': '64.83.36.96',
    'port': 53306,
    'user': 'OnGMpLtFPNHcSbbtI7lu',
    'password': 'lsTiBCoLk3cWvQKMZ4Mq',
    'database': 'cf',
    'charset': 'utf8mb4'
}

SQLITE_URL = "sqlite:///./baby_growth.db"

Base = declarative_base()

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

def get_sqlite_session():
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def get_mysql_engine():
    mysql_url = f"mysql+pymysql://{MYSQL_CONFIG['user']}:{MYSQL_CONFIG['password']}@{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}?charset={MYSQL_CONFIG['charset']}"
    return create_engine(mysql_url, echo=True)

def create_mysql_tables(engine):
    Base.metadata.create_all(bind=engine)
    print("MySQL数据库表创建完成")

def migrate_data():
    print("开始数据迁移...")
    
    sqlite_session = get_sqlite_session()
    mysql_engine = get_mysql_engine()
    
    create_mysql_tables(mysql_engine)
    
    MySQLSession = sessionmaker(autocommit=False, autoflush=False, bind=mysql_engine)
    mysql_session = MySQLSession()
    
    try:
        print("\n1. 迁移Baby数据...")
        babies = sqlite_session.query(Baby).all()
        baby_id_map = {}
        
        for baby in babies:
            new_baby = Baby(
                id=baby.id,
                name=baby.name,
                gender=baby.gender,
                birth_date=baby.birth_date,
                birth_weight=baby.birth_weight,
                birth_height=baby.birth_height,
                created_at=baby.created_at
            )
            mysql_session.add(new_baby)
            baby_id_map[baby.id] = baby.id
            print(f"  迁移宝宝: {baby.name}")
        
        mysql_session.commit()
        print(f"  共迁移 {len(babies)} 条Baby记录")
        
        print("\n2. 迁移GrowthRecord数据...")
        growth_records = sqlite_session.query(GrowthRecord).all()
        
        for record in growth_records:
            new_record = GrowthRecord(
                id=record.id,
                baby_id=baby_id_map.get(record.baby_id, record.baby_id),
                record_date=record.record_date,
                weight=record.weight,
                height=record.height,
                head_circumference=record.head_circumference,
                notes=record.notes,
                created_at=record.created_at
            )
            mysql_session.add(new_record)
        
        mysql_session.commit()
        print(f"  共迁移 {len(growth_records)} 条GrowthRecord记录")
        
        print("\n3. 迁移Vaccine数据...")
        vaccines = sqlite_session.query(Vaccine).all()
        
        for vaccine in vaccines:
            new_vaccine = Vaccine(
                id=vaccine.id,
                baby_id=baby_id_map.get(vaccine.baby_id, vaccine.baby_id),
                vaccine_name=vaccine.vaccine_name,
                vaccine_date=vaccine.vaccine_date,
                dose=vaccine.dose,
                reaction=vaccine.reaction,
                next_due_date=vaccine.next_due_date,
                notes=vaccine.notes,
                created_at=vaccine.created_at
            )
            mysql_session.add(new_vaccine)
        
        mysql_session.commit()
        print(f"  共迁移 {len(vaccines)} 条Vaccine记录")
        
        print("\n4. 迁移Milestone数据...")
        milestones = sqlite_session.query(Milestone).all()
        
        for milestone in milestones:
            new_milestone = Milestone(
                id=milestone.id,
                baby_id=baby_id_map.get(milestone.baby_id, milestone.baby_id),
                title=milestone.title,
                description=milestone.description,
                milestone_date=milestone.milestone_date,
                category=milestone.category,
                notes=milestone.notes,
                created_at=milestone.created_at
            )
            mysql_session.add(new_milestone)
        
        mysql_session.commit()
        print(f"  共迁移 {len(milestones)} 条Milestone记录")
        
        print("\n" + "="*50)
        print("数据迁移完成!")
        print(f"  - Baby: {len(babies)} 条")
        print(f"  - GrowthRecord: {len(growth_records)} 条")
        print(f"  - Vaccine: {len(vaccines)} 条")
        print(f"  - Milestone: {len(milestones)} 条")
        print("="*50)
        
    except Exception as e:
        mysql_session.rollback()
        print(f"数据迁移失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sqlite_session.close()
        mysql_session.close()

if __name__ == "__main__":
    migrate_data()
