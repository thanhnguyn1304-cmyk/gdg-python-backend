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

Base.metadata.create_all(bind=engine)

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

# --- DANH SÁCH DỰ PHÒNG (BACKUP) KHI AI LỖI ---
# Danh sách này có sẵn LINK ẢNH để đảm bảo app luôn đẹp
BACKUP_ACTIVITIES = [
    {"title": "Cafe làm việc", "desc": "Tìm một góc yên tĩnh và tập trung.", "keyword": "coffee shop working"},
    {"title": "Chạy bộ công viên", "desc": "Hít thở không khí trong lành.", "keyword": "running park morning"},
    {"title": "Nấu ăn tại gia", "desc": "Thử làm món Pasta hoặc Steak.", "keyword": "cooking pasta home kitchen"},
    {"title": "Đọc sách bên cửa sổ", "desc": "Thả hồn vào những trang sách.", "keyword": "reading book window rain"},
    {"title": "Đi dạo phố đêm", "desc": "Ngắm nhìn thành phố lên đèn.", "keyword": "city night street walking"},
    {"title": "Cắm trại cuối tuần", "desc": "Về với thiên nhiên.", "keyword": "camping tent forest fire"},
    {"title": "Chơi Guitar", "desc": "Học một bản nhạc mới.", "keyword": "playing guitar acoustic"},
    {"title": "Vẽ tranh", "desc": "Sáng tạo với màu nước.", "keyword": "painting watercolor art"},
    {"title": "Yoga buổi sáng", "desc": "Thư giãn gân cốt.", "keyword": "yoga woman morning sun"},
    {"title": "Chụp ảnh Film", "desc": "Lưu giữ khoảnh khắc hoài cổ.", "keyword": "film photography camera street"}
]

# 4. API GỢI Ý (Đã nâng cấp)
@app.get("/api/suggestions")
def get_ai_suggestions(user_uid: str = None, db: Session = Depends(get_db)):
    # --- CÁCH 1: DÙNG AI (NẾU CÓ KEY) ---
    if GEMINI_API_KEY:
        try:
            # Lấy lịch sử để AI học
            history_text = ""
            if user_uid:
                past = db.query(Activity).filter(Activity.user_uid == user_uid).order_by(Activity.id.desc()).limit(3).all()
                if past:
                    titles = ", ".join([p.title for p in past])
                    history_text = f"User thích: {titles}."

            # Prompt ngẫu nhiên để tránh lặp lại
            random_vibe = random.choice(["năng động", "thư giãn", "sáng tạo", "học tập", "khám phá"])
            
            prompt = f"""
            Đóng vai trợ lý. {history_text}. Hãy gợi ý 5 hoạt động theo phong cách '{random_vibe}'.
            Trả về JSON list: [{{ "title": "...", "desc": "...", "keyword": "english keyword for image generation" }}]
            Keyword phải là tiếng Anh để tạo ảnh (ví dụ: 'coffee', 'sunset', 'gym').
            Chỉ trả về JSON.
            """
            
            response = model.generate_content(prompt)
            text_clean = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(text_clean)
            
            results = []
            for idx, item in enumerate(data):
                # Tạo link ảnh Pollinations
                kw = item.get('keyword', 'lifestyle').replace(" ", "%20")
                img = f"https://image.pollinations.ai/prompt/{kw}?width=400&height=600&nologo=true"
                results.append({"id": idx + 9000, "title": item['title'], "desc": item['desc'], "image_url": img})
            
            return results

        except Exception as e:
            print(f"AI Lỗi (Dùng Backup): {e}")
            # Nếu AI lỗi -> Chạy xuống CÁCH 2
    
    # --- CÁCH 2: DÙNG DANH SÁCH DỰ PHÒNG (BACKUP) ---
    # Lấy ngẫu nhiên 5 cái từ danh sách backup
    shuffled = random.sample(BACKUP_ACTIVITIES, 5)
    results = []
    for idx, item in enumerate(shuffled):
        kw = item['keyword'].replace(" ", "%20")
        img = f"https://image.pollinations.ai/prompt/{kw}?width=400&height=600&nologo=true"
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