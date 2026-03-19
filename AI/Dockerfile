FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# [수정] 실제 파일 구조에 맞게 수정
# vector_store.py 제거됨, main_server.py로 변경, vector_db/ 폴더 추가
COPY main_server.py .
COPY transcript.py .
COPY generation.py .
COPY vector_db/ ./vector_db/

# cookies.txt가 있으면 포함 (없어도 동작은 함)
# COPY cookies.txt .

ENV PYTHONUNBUFFERED=1

# [수정] main_server:app 으로 변경
CMD uvicorn main_server:app --host 0.0.0.0 --port $PORT
```

---

### 수정 3: `requirements.txt` (`python-dotenv` 추가)
```
fastapi
uvicorn
openai
langchain-chroma
langchain-huggingface
langchain-text-splitters
sentence-transformers
youtube-transcript-api
python-multipart
huggingface_hub
certifi
chromadb
tiktoken
pypdf
langchain-community
python-dotenv