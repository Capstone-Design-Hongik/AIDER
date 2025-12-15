# 1. 파이썬 3.11 슬림 버전 (기반 이미지)
FROM python:3.11-slim

# 2. 시스템 필수 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. requirements.txt 복사 및 설치
COPY requirements.txt .

# [중요] PyTorch CPU 버전 강제 설치 (용량 2GB -> 200MB로 감소 효과)
# requirements.txt 설치 시 --extra-index-url로 CPU 버전을 찾게 함
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 5. [핵심 수정] 소스 코드 파일을 '콕 집어서' 복사
# (COPY . . 대신 필요한 파일명만 적습니다. venv나 model 폴더가 들어올 수 없게 원천 차단합니다.)
COPY main_api.py .
COPY transcript.py .
COPY vector_store.py .
COPY generation.py .
# 혹시 .env 파일이 있다면 제외해야 하므로 여기 적지 않습니다.

# 6. 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 7. 서버 실행
CMD uvicorn main_api:app --host 0.0.0.0 --port $PORT