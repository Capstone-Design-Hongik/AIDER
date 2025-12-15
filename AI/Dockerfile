# 1. 파이썬 3.11 슬림 버전 사용 (가볍고 빠름)
FROM python:3.11-slim

# 2. 시스템 패키지 설치 (빌드 도구 및 git 등 필수 요소)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# 3. 작업 디렉토리 설정
WORKDIR /app

# 4. 의존성 파일 복사 및 설치
# (AI 폴더 안에 있는 requirements.txt를 컨테이너의 /app으로 복사)
COPY AI/requirements.txt .

# 5. 라이브러리 설치
RUN pip install --no-cache-dir -r requirements.txt

# 6. 소스 코드 복사
# (AI 폴더 안의 모든 코드를 컨테이너의 /app으로 복사)
COPY AI/ .

# 7. 환경 변수 설정 (로그가 버퍼링 없이 바로 출력되도록 함)
ENV PYTHONUNBUFFERED=1

# 8. 서버 실행 명령
# Railway는 자동으로 $PORT 환경변수를 주입하므로 이를 사용해야 함
CMD uvicorn main_api:app --host 0.0.0.0 --port $PORT