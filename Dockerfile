# Dùng bản Python nhẹ nhất
FROM python:3.9-slim

# Setup môi trường
WORKDIR /app
COPY . .

# Cài thư viện
RUN pip install --no-cache-dir fastapi uvicorn firebase-admin psycopg2-binary

# Mở cổng 8080 (Cloud Run thích cổng này)
ENV PORT=8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]