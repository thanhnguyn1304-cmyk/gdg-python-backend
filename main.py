import os
import random
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
    priority = Column(String, default="Medium")
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

# --- 3. KHO DỮ LIỆU MẪU (DATA SEED) ---
SAMPLE_ACTIVITIES = [
    {"title": "Chạy bộ 5km", "desc": "Xỏ giày vào và ra công viên ngay.", "icon": "🔥", "color": "from-cyan-400 to-blue-500"},
    {"title": "Cafe làm việc", "desc": "Đổi gió ra Highlands/Starbucks ngồi.", "icon": "☕", "color": "from-orange-400 to-red-500"},
    {"title": "Xem phim rạp", "desc": "Check CGV xem có bom tấn gì mới.", "icon": "🎬", "color": "from-purple-400 to-pink-500"},
    {"title": "Nhậu lai rai", "desc": "Alo hội bạn thân làm vài ly.", "icon": "🍺", "color": "from-yellow-400 to-orange-500"},
    {"title": "Đọc sách 30p", "desc": "Tắt điện thoại, mở sách ra.", "icon": "📚", "color": "from-green-400 to-emerald-500"},
    {"title": "Dọn dẹp nhà", "desc": "Bật nhạc to lên và dọn phòng.", "icon": "🧹", "color": "from-gray-400 to-gray-600"},
    {"title": "Đi bơi", "desc": "Hạ nhiệt mùa hè tại bể bơi.", "icon": "🏊", "color": "from-blue-400 to-cyan-300"},
    {"title": "Leo núi trong nhà", "desc": "Thử thách bản thân với bộ môn mới.", "icon": "🧗", "color": "from-stone-500 to-stone-700"},
    {"title": "Nấu ăn món mới", "desc": "Tìm công thức và vào bếp trổ tài.", "icon": "🍳", "color": "from-orange-500 to-yellow-500"},
    {"title": "Chơi Board Game", "desc": "Rủ bạn bè chơi Ma Sói, Mèo Nổ.", "icon": "🎲", "color": "from-red-500 to-purple-600"},
    {"title": "Đi bảo tàng", "desc": "Khám phá văn hóa và lịch sử.", "icon": "🏛️", "color": "from-amber-600 to-amber-800"},
    {"title": "Nghe Podcast", "desc": "Vừa làm việc nhà vừa nạp kiến thức.", "icon": "🎧", "color": "from-violet-500 to-purple-500"},
    {"title": "Viết nhật ký", "desc": "Ghi lại những suy nghĩ trong ngày.", "icon": "✍️", "color": "from-neutral-500 to-neutral-700"},
    {"title": "Học nhạc cụ", "desc": "Tập chơi Guitar hoặc Ukulele.", "icon": "🎸", "color": "from-rose-400 to-rose-600"},
    {"title": "Thiền định", "desc": "Dành 10 phút tịnh tâm, thư giãn.", "icon": "🧘", "color": "from-teal-400 to-teal-600"}
]

# --- 4. UTILS ---
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

# --- 5. DATA MODELS (Pydantic) ---
class ActivityCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "Medium"

# --- 6. APIs ---

@app.get("/")
def home(): return {"msg": "Autonomy API Ready"}

# --- API MỚI: LẤY GỢI Ý NGẪU NHIÊN ---
@app.get("/api/suggestions")
def get_suggestions():
    # Lấy ngẫu nhiên tối đa 10 hoạt động từ kho mẫu
    num_to_select = min(len(SAMPLE_ACTIVITIES), 10)
    shuffled = random.sample(SAMPLE_ACTIVITIES, num_to_select)
    
    results = []
    for idx, item in enumerate(shuffled):
        results.append({
            "id": idx + 1000, # ID giả để Frontend dùng làm key
            "title": item["title"],
            "desc": item["desc"],
            "icon": item["icon"],
            "color": item["color"]
        })
    return results

# Lấy danh sách hoạt động ĐÃ LƯU của User
@app.get("/api/activities")
def get_activities(user = Depends(verify_token), db: Session = Depends(get_db)):
    return db.query(Activity).filter(Activity.user_uid == user['uid']).order_by(Activity.id.desc()).all()

# Lưu hoạt động (Khi quẹt phải)
@app.post("/api/activities")
def create_activity(item: ActivityCreate, user = Depends(verify_token), db: Session = Depends(get_db)):
    new_act = Activity(user_uid=user['uid'], title=item.title, description=item.description, priority=item.priority)
    db.add(new_act)
    db.commit()
    return {"msg": "Success", "data": new_act}

# Xóa hoạt động
@app.delete("/api/activities/{act_id}")
def delete_activity(act_id: int, user = Depends(verify_token), db: Session = Depends(get_db)):
    act = db.query(Activity).filter(Activity.id == act_id, Activity.user_uid == user['uid']).first()
    if not act: raise HTTPException(404, "Not found")
    db.delete(act)
    db.commit()
    return {"msg": "Deleted"}