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

# 1. LOAD BIẾN MÔI TRƯỜNG (BẢO MẬT)
load_dotenv() # Đọc file .env ở local

# Lấy Key từ môi trường (Render hoặc .env)
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Fix lỗi link DB của Render/Neon
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Cấu hình AI
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-1.5-flash")
else:
    print("CẢNH BÁO: Chưa có GEMINI_API_KEY!")

# 2. SETUP DATABASE
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True, index=True)
    user_uid = Column(String, index=True)
    title = Column(String)       # Ví dụ: "Đọc sách Nhà Giả Kim"
    description = Column(Text)   # Ví dụ: "Một cuốn sách về ước mơ..."
    image_url = Column(String)   # Link ảnh
    is_completed = Column(Boolean, default=False) # True = Đã làm xong (Achievement)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

Base.metadata.create_all(bind=engine)

# 3. SETUP APP
if not firebase_admin._apps:
    firebase_admin.initialize_app()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# 4. UTILS
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

# 5. API AI THÔNG MINH
@app.get("/api/suggestions")
def get_ai_suggestions(user_uid: str = None, db: Session = Depends(get_db)):
    # Lấy sở thích cũ (những cái đã completed hoặc saved)
    history_text = "người dùng mới"
    if user_uid:
        past = db.query(Activity).filter(Activity.user_uid == user_uid).order_by(Activity.id.desc()).limit(5).all()
        if past:
            titles = ", ".join([p.title for p in past])
            history_text = f"Người dùng đã thích: {titles}"

    # Prompt: Yêu cầu cụ thể để tạo Achievement
    prompt = f"""
    Đóng vai trợ lý lối sống (Lifestyle Assistant). {history_text}.
    Hãy gợi ý 5 hoạt động tiếp theo thật CỤ THỂ (Specific). 
    Ví dụ: Thay vì "Đọc sách", hãy gợi ý "Đọc cuốn Rừng Na Uy". Thay vì "Đi cafe", hãy "Đi cafe trứng Giảng Võ".
    
    Yêu cầu trả về JSON format chính xác như sau:
    [
        {{
            "title": "Tên hoạt động cụ thể",
            "desc": "Mô tả ngắn gọn, hấp dẫn (1 câu)",
            "keyword": "Từ khóa tiếng Anh ngắn gọn để tìm ảnh (ví dụ: book, coffee, running)"
        }}
    ]
    Chỉ trả về JSON thuần, không markdown.
    """
    
    try:
        if not GEMINI_API_KEY: raise Exception("No API Key")
        
        response = model.generate_content(prompt)
        text_clean = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text_clean)
        
        # Xử lý ảnh và ID
        results = []
        for idx, item in enumerate(data):
            # Dùng Pollinations AI để tạo ảnh từ keyword (Miễn phí, đẹp)
            img_url = f"https://image.pollinations.ai/prompt/{item['keyword']}?width=400&height=600&nologo=true"
            results.append({
                "id": idx + 9999,
                "title": item['title'],
                "desc": item['desc'],
                "image_url": img_url # Ảnh thật thay vì Icon
            })
        return results

    except Exception as e:
        print(f"Lỗi AI: {e}")
        # Dữ liệu dự phòng nếu AI lỗi
        fallback_img = "https://image.pollinations.ai/prompt/relax?width=400&height=600"
        return [
            {"id": 1, "title": "Kết nối AI...", "desc": "Đang gọi Gemini, thử lại sau nhé!", "image_url": fallback_img}
        ]

# 6. CÁC API KHÁC
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
def save_activity(item: ActivityCreate, user = Depends(verify_token), db: Session = Depends(get_db)):
    # Lưu vào DB
    new_act = Activity(user_uid=user['uid'], title=item.title, description=item.description, image_url=item.image_url)
    db.add(new_act)
    db.commit()
    return {"msg": "Saved"}

@app.put("/api/activities/{act_id}")
def update_status(act_id: int, item: ActivityUpdate, user = Depends(verify_token), db: Session = Depends(get_db)):
    # Đánh dấu đã xong (Achievement unlocked)
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