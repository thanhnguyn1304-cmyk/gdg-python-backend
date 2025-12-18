# backend/main.py
import os
import firebase_admin
from firebase_admin import auth
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime

# --- 1. SETUP DATABASE ---
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Model Activities (Khớp với bảng SQL)
class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_uid = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    priority = Column(String, default="Medium") # High, Medium, Low
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# --- 2. SETUP APP ---
if not firebase_admin._apps:
    firebase_admin.initialize_app()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# --- 3. UTILS ---
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

async def verify_token(authorization: str = Header(...)):
    try:
        token = authorization.split("Bearer ")[1]
        return auth.verify_id_token(token)
    except:
        raise HTTPException(status_code=401, detail="Token invalid")

# --- 4. DATA MODELS (Pydantic) ---
class ActivityCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "Medium"

class ActivityUpdate(BaseModel):
    is_completed: bool

# --- 5. APIs ---

@app.get("/")
def home(): return {"msg": "Autonomy API Ready"}

# Lấy danh sách hoạt động
@app.get("/api/activities")
def get_activities(user = Depends(verify_token), db: Session = Depends(get_db)):
    return db.query(Activity).filter(Activity.user_uid == user['uid']).order_by(Activity.id.desc()).all()

# Tạo hoạt động mới
@app.post("/api/activities")
def create_activity(item: ActivityCreate, user = Depends(verify_token), db: Session = Depends(get_db)):
    new_act = Activity(user_uid=user['uid'], title=item.title, description=item.description, priority=item.priority)
    db.add(new_act)
    db.commit()
    return {"msg": "Success", "data": new_act}

# Đánh dấu hoàn thành / chưa hoàn thành
@app.put("/api/activities/{act_id}")
def update_status(act_id: int, item: ActivityUpdate, user = Depends(verify_token), db: Session = Depends(get_db)):
    act = db.query(Activity).filter(Activity.id == act_id, Activity.user_uid == user['uid']).first()
    if not act: raise HTTPException(404, "Not found")
    act.is_completed = item.is_completed
    db.commit()
    return {"msg": "Updated"}

# Xóa hoạt động
@app.delete("/api/activities/{act_id}")
def delete_activity(act_id: int, user = Depends(verify_token), db: Session = Depends(get_db)):
    act = db.query(Activity).filter(Activity.id == act_id, Activity.user_uid == user['uid']).first()
    if not act: raise HTTPException(404, "Not found")
    db.delete(act)
    db.commit()
    return {"msg": "Deleted"}