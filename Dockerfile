# backend/Dockerfile

# 1. Dùng Python 3.9
FROM python:3.9

# 2. Tạo thư mục làm việc
WORKDIR /app

# 3. Copy file thư viện vào trước (để tận dụng cache)
COPY requirements.txt .

# 4. Cài đặt thư viện
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy toàn bộ code vào
COPY . .

# 6. Mở cổng 8080 (Render cần cổng này)
EXPOSE 8080

# 7. Lệnh chạy server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]