import os
import firebase_admin
from firebase_admin import auth, credentials
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

# 1. Khởi tạo Firebase (Tự động tìm credentials nếu chạy trên Cloud Run)
firebase_admin.initialize_app()

app = FastAPI()

# Cho phép React gọi vào (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Sau này thay bằng domain Vercel của bạn
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Hàm bảo vệ: Chỉ cho qua nếu Token chuẩn
async def verify_token(authorization: str = Header(...)):
    try:
        token = authorization.split("Bearer ")[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token # Trả về info user (uid, email...)
    except Exception:
        raise HTTPException(status_code=401, detail="Token dỏm hoặc hết hạn")

# 3. API Test
@app.get("/api/data")
def get_protected_data(user = Depends(verify_token)):
    return {
        "message": "Chào người anh em GDG!",
        "user_uid": user['uid'],
        "data_from_postgres": "Kết nối DB ở bước sau nhé!"
    }