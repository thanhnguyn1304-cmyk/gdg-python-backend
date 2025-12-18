import os
import random
import json
import firebase_admin
from firebase_admin import auth
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# 1. SETUP
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")

# 2. DATABASE
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_uid = Column(String, index=True)
    title = Column(String)
    description = Column(Text)
    image_url = Column(String) # Cột chứa link ảnh
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

# 3. APP
if not firebase_admin._apps:
    firebase_admin.initialize_app()
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

# --- DANH SÁCH DỰ PHÒNG (BACKUP) - ẢNH THẬT ---
BACKUP_ACTIVITIES = [
    {"title": "Cafe làm việc", "desc": "Tìm một góc yên tĩnh và tập trung.", "keyword": "coffee"},
    {"title": "Chạy bộ công viên", "desc": "Hít thở không khí trong lành.", "keyword": "running"},
    {"title": "Nấu ăn tại gia", "desc": "Thử làm món Pasta hoặc Steak.", "keyword": "cooking"},
    {"title": "Đọc sách", "desc": "Thả hồn vào những trang sách.", "keyword": "book"},
    {"title": "Dạo phố đêm", "desc": "Ngắm nhìn thành phố lên đèn.", "keyword": "city,night"},
    {"title": "Cắm trại", "desc": "Về với thiên nhiên.", "keyword": "camping"},
    {"title": "Chơi Guitar", "desc": "Học một bản nhạc mới.", "keyword": "guitar"},
    {"title": "Vẽ tranh", "desc": "Sáng tạo với màu nước.", "keyword": "painting"},
    {"title": "Yoga", "desc": "Thư giãn gân cốt buổi sáng.", "keyword": "yoga"},
    {"title": "Chụp ảnh", "desc": "Lưu giữ khoảnh khắc đời thường.", "keyword": "camera"}
]

# Hàm lấy link ảnh thật từ LoremFlickr
def get_real_image(keyword, lock_id):
    # lock_id giúp ảnh cố định không bị nhảy lung tung khi refresh
    return f"https://loremflickr.com/400/600/{keyword}?lock={lock_id}"

# 4. API GỢI Ý
@app.get("/api/suggestions")
def get_suggestions(user_uid: str = None, db: Session = Depends(get_db)):
    # --- ƯU TIÊN 1: DÙNG AI ĐỂ LẤY Ý TƯỞNG MỚI ---
    if GEMINI_API_KEY:
        try:
            # Prompt ngắn gọn
            prompt = """
            Gợi ý 5 hoạt động giải trí/học tập thú vị.
            Trả về JSON list: [{"title": "...", "desc": "...", "keyword": "english_one_word"}]
            Keyword phải là 1 từ tiếng Anh đơn giản để tìm ảnh (vd: 'cat', 'sky', 'food').
            """
            response = model.generate_content(prompt)
            text_clean = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text_clean)
            
            results = []
            for idx, item in enumerate(data):
                # Tạo link ảnh thật
                img = get_real_image(item.get('keyword', 'life'), idx + 9000)
                results.append({"id": idx + 9000, "title": item['title'], "desc": item['desc'], "image_url": img})
            
            return results
        except Exception as e:
            print(f"AI Error: {e}")
            # Nếu AI lỗi -> Tự động xuống dùng Backup
    
    # --- ƯU TIÊN 2: DÙNG DANH SÁCH CỐ ĐỊNH (Rất nhanh) ---
    shuffled = random.sample(BACKUP_ACTIVITIES, 5)
    results = []
    for idx, item in enumerate(shuffled):
        img = get_real_image(item['keyword'], idx)
        results.append({
            "id": idx + 1000,
            "title": item['title'],
            "desc": item['desc'],
            "image_url": img
        })
    return results

# 5. CÁC API CRUD KHÁC (Giữ nguyên)
class ActivityCreate(BaseModel):
    title: str
    description: str
    image_url: str

class ActivityUpdate(BaseModel):
    is_completed: bool

@app.get("/api/activities")
def get_my_list(user = Depends(verify_token), db: Session = Depends(get_db)):
    return db.query(Activity).filter(Activity.user_uid == user['uid']).order_by(Activity.id.desc()).all()

@app.post("/api/activities")
def create_activity(item: ActivityCreate, user = Depends(verify_token), db: Session = Depends(get_db)):
    # Tự tạo bảng nếu chưa có (Backup logic)
    Base.metadata.create_all(bind=engine)
    
    new_act = Activity(user_uid=user['uid'], title=item.title, description=item.description, image_url=item.image_url)
    db.add(new_act)
    db.commit()
    return {"msg": "Saved"}

@app.put("/api/activities/{act_id}")
def update_status(act_id: int, item: ActivityUpdate, user = Depends(verify_token), db: Session = Depends(get_db)):
    act = db.query(Activity).filter(Activity.id == act_id, Activity.user_uid == user['uid']).first()
    if act:
        act.is_completed = item.is_completed
        db.commit()
    return {"msg": "Updated"}

@app.delete("/api/activities/{act_id}")
def delete_activity(act_id: int, user = Depends(verify_token), db: Session = Depends(get_db)):
    db.query(Activity).filter(Activity.id == act_id, Activity.user_uid == user['uid']).delete()
    db.commit()
    return {"msg": "Deleted"}