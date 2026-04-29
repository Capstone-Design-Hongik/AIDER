# Agentic RAG 투자 조언 시스템 - 파이프라인 및 아키텍처 가이드

## 📋 각 파일의 역할

### 1️⃣ **config.py** - 설정 관리

**역할:**
- API 키 관리 (Anthropic, Mistral)
- LLM 모델 선택 (각 역할별 최적 모델)
- 벡터DB 경로 설정
- 임베딩 모델 설정
- RAG 하이퍼파라미터 설정

**하는 일:**
1. .env 파일에서 API 키 로드
2. 각 LLM의 역할에 맞는 모델 정의
   - Agent: Mistral Small (빠른 의사결정)
   - 분석: Claude Sonnet (정확성)
   - 최종: Claude Sonnet (품질)
3. ChromaDB 경로 설정
4. 검색 임계값, 토큰 제한 등 설정

---

### 2️⃣ **models.py** - 데이터 구조 정의

**역할:**
- 시스템 전체에서 사용할 데이터 모델 정의
- Pydantic 기반으로 타입 검증

**정의하는 데이터:**

1. **Trade** - 사용자의 한 건의 매매 기록
   - 날짜, 종목명, 매매 유형, 가격, 수량

2. **StockPrice** - 종가 데이터
   - 날짜, 종가

3. **UserData** - 사용자 전체 데이터
   - 매매 기록 리스트
   - 종가 리스트
   - YouTube URL

4. **UserAnalysisResult** - 사용자 분석 결과
   - 감지된 패턴
   - 패턴 강도
   - 위험도
   - 신뢰도

5. **TranscriptSection** - YouTube 자막 한 섹션
   - 섹션명, 내용, 요약
   - 핵심 포인트
   - 감정, 대상 투자자

6. **TranscriptAnalysisResult** - 자막 분석 전체 결과
   - 섹션 리스트
   - 키워드
   - 신뢰도

7. **VectorSearchResult** - 벡터 검색 결과 한 건
   - ID, 내용, 유사도
   - 메타데이터

8. **AgentDecision** - Agent의 의사결정
   - 다음 액션
   - 이유
   - 신뢰도

9. **RAGOutput** - 최종 출력
   - 분석 결과
   - 자막 분석
   - 검색 결과
   - Agent 의사결정
   - 최종 조언

---

### 3️⃣ **transcript.py** - YouTube 자막 추출

**역할:**
- YouTube 영상에서 자막 추출
- 다양한 언어 및 형식 지원

**주요 함수:**

1. **extract_video_id(url)**
   - YouTube URL → 비디오 ID 추출

2. **transcript(video_id)**
   - YouTube API로 자막 목록 조회
   - 공식/자동생성 자막 우선순위 판단
   - 한국어/영어 선택
   - 최종 텍스트 반환

3. **get_transcript_with_timestamps(video_id)**
   - 타임스탬프 포함 자막 반환
   - 형식: `[{text, start, duration}, ...]`

4. **chunk_transcript(transcript, chunk_size, overlap)**
   - 긴 자막을 작은 청크로 분할
   - 오버랩 처리로 문맥 유지
   - 청크 리스트 반환

---

### 4️⃣ **download_model.py** - 임베딩 모델 관리

**역할:**
- Hugging Face에서 임베딩 모델 다운로드
- 로컬 캐싱으로 재다운로드 방지

**주요 함수:**

1. **download_model(model_name)**
   - 모델이 로컬에 있으면 로드
   - 없으면 Hugging Face에서 다운로드
   - SentenceTransformer 객체 반환

2. **list_available_models()**
   - 사용 가능한 모델 목록 출력

3. **check_model_exists(model_name)**
   - 모델 설치 여부 확인

4. **get_model_size(model_name)**
   - 모델 디스크 크기 반환

5. **get_dimension(model_name)**
   - 임베딩 차원 반환 (384, 768 등)

**사용 모델:**
- small: MiniLM (384차원, 빠름)
- medium: MPNet (768차원)
- large: RoBERTa (768차원)
- korean: XLM-R (다국어 지원)

---

### 5️⃣ **chromadb_manager.py** - 벡터DB 관리

**역할:**
- 문서를 벡터로 변환해 벡터DB에 저장
- 의미 기반 검색 수행
- DB 통계 및 관리

**주요 함수:**

1. **add_documents(documents, doc_type)**
   - 문서 → 임베딩 변환
   - ChromaDB에 저장
   - 추가된 개수 반환

2. **search(query, k, metadata_filter)**
   - 쿼리 임베딩 생성
   - 유사도 검색
   - 커버리지 계산
   - VectorSearchResult 리스트 반환

3. **delete_by_source(source)**
   - 특정 소스의 문서 모두 삭제

4. **count_documents()**
   - 전체 문서 개수

5. **get_stats()**
   - 소스별 문서 개수
   - 임베딩 차원
   - 컬렉션 이름

6. **clear()**
   - DB 초기화

**내부 구조:**
- ChromaDB (DuckDB 기반)
- 각 문서 저장 시 메타데이터도 함께 저장
- Cosine 유사도로 검색

---

### 6️⃣ **add_youtube.py** - YouTube 자막 추가

**역할:**
- YouTube 자막을 처리해 벡터DB에 추가
- 섹션 정보와 함께 저장

**주요 함수:**

1. **add_youtube_url(youtube_url, section_analysis)**
   - URL → 비디오 ID 추출
   - 자막 추출
   - 청킹
   - 문서 생성
   - 벡터DB에 추가

2. **add_youtube_with_sections(youtube_url, sections)**
   - 섹션 정보와 함께 추가
   - 각 청크를 섹션에 매칭
   - 섹션 메타데이터 저장

3. **_match_chunk_to_section(chunk, sections)**
   - 청크가 어느 섹션에 속하는지 판단
   - 키워드 매칭으로 판단
   - 감정, 대상 정보 할당

**처리 흐름:**
YouTube URL
↓
자막 추출 (transcript.py)
↓
청킹 분할
↓
Document 객체 생성 (메타데이터 포함)
↓
벡터DB 저장 (chromadb_manager.py)
---

### 7️⃣ **add_pdf.py** - PDF 추가

**역할:**
- PDF 파일을 벡터DB에 추가
- PDF에서 텍스트 추출

**주요 함수:**

1. **add_pdf_file(pdf_path, title, category)**
   - PDF 파일 읽음
   - 텍스트 추출
   - 청킹
   - 벡터DB에 추가

2. **add_multiple_pdfs(pdf_directory, category)**
   - 디렉토리의 모든 PDF 처리
   - 총 추가된 문서 수 반환

3. **_extract_text_from_pdf(pdf_path)**
   - PyPDF2 사용
   - 페이지별로 텍스트 추출
   - 페이지 구분 마크 추가

**사용 라이브러리:** PyPDF2

---

### 8️⃣ **tools.py** - RAG 도구 정의

**역할:**
- Agentic RAG의 각 도구 정의
- Agent가 호출할 수 있는 함수들

**5가지 도구:**

1. **UserAnalysisTool**
   - 사용자 매매 데이터 분석
   - 패턴 감지
   - 위험도 판단
   - Claude Sonnet 사용

2. **TranscriptAnalysisTool**
   - YouTube 자막 분석
   - 섹션화
   - 요약 생성
   - Claude Sonnet 사용

3. **VectorSearchTool**
   - 벡터DB에서 검색
   - 관련 내용 추출
   - 커버리지 계산

4. **RefinedSearchTool**
   - 커버리지가 낮으면 재검색
   - 개선된 쿼리 생성
   - Mistral Small 사용
   - 추가 검색 결과 반환

5. **ValidationTool**
   - 검색 결과 검증
   - 신뢰도 판단
   - 문제점 감지
   - Claude Sonnet 사용

**특징:**
- 각 Tool은 독립적으로 실행 가능
- 입력과 출력이 명확함
- Agent가 필요시 호출

---

### 9️⃣ **agent.py** - Agent Manager (핵심)

**역할:**
- Agentic RAG의 최상위 조정자
- 상황에 맞게 도구 선택 및 실행
- 반복적으로 최적의 결과 추구

**주요 함수:**

1. **run(user_data)**
   - 전체 파이프라인 실행
   - 최대 5회 반복
   - RAGOutput 반환

2. **_make_initial_plan(user_data)**
   - 초기 계획 수립
   - Mistral Small 사용
   - 어떤 도구를 먼저 할지 결정

3. **_agent_decide(execution_state, user_data)**
   - 현재 상황 판단
   - 다음 액션 결정
     - `vector_search`: 벡터 검색
     - `refined_search`: 추가 검색
     - `validation`: 검증
     - `stop`: 종료
   - Mistral Small 사용 (빠른 의사결정)
   - AgentDecision 반환

4. **_execute_search(execution_state, decision)**
   - 검색 쿼리 생성
   - 벡터 검색 실행
   - 결과 및 커버리지 반환

5. **_generate_search_query(user_analysis, iteration)**
   - 사용자 분석 결과 → 검색 쿼리
   - 반복할수록 더 깊게 검색
   - Mistral Small 사용
   - 자연어 쿼리 반환

6. **_generate_final_advice(execution_state, user_data)**
   - 모든 정보 종합
   - Claude Sonnet 사용 (최고 품질)
   - 최종 조언 텍스트 반환

**의사결정 흐름:**
┌─ 초기 계획 수립
├─ 병렬: 사용자 분석 + 자막 분석
├─ 반복문 (최대 5회):
│  ├─ Agent 의사결정
│  ├─ 다음 액션 실행
│  ├─ 결과 평가
│  └─ 충분하면 break
└─ 최종 조언 생성
---

### 🔟 **main_server.py** - FastAPI 서버

**역할:**
- HTTP API 제공
- Railway에 배포 가능
- 사용자 요청 처리

**주요 엔드포인트:**

1. **GET /health**
   - 헬스 체크 + DB 통계

2. **POST /analyze**
   - 요청: `{trades, stockPrices, externalUrl}`
   - Agent 실행
   - 응답: 분석 결과 + 최종 조언

3. **POST /add-youtube**
   - 요청: `{url}`
   - YouTube 자막 추가
   - 응답: 추가된 문서 수

4. **POST /add-pdf**
   - 요청: PDF 파일
   - PDF 추가
   - 응답: 추가된 문서 수

5. **GET /db-stats**
   - DB 통계 반환

6. **DELETE /clear-db**
   - DB 초기화

**시작 시:**
- 모델 다운로드
- ChromaDB 초기화
- Agent, YouTube, PDF Manager 생성

**배포 대상:** Railway
**포트:** 8000 (또는 환경변수)

---

## 🔄 전체 파이프라인

### **사용자 요청부터 조언까지의 흐름**
사용자 요청
1️⃣ HTTP 요청 수신 (main_server.py)
POST /analyze
{
"trades": [...],
"stockPrices": [...],
"externalUrl": "https://youtube.com/watch?v=..."
}

2️⃣ Agent 실행 (agent.py)
┌─ 초기 계획 수립
│  └─ Mistral Small: "뭘 먼저 할까?"
│
├─ 병렬 처리 (속도 ⬆️)
│  │
│  ├─ LLM A: 사용자 분석 (tools.py → UserAnalysisTool)
│  │  ├─ 매매 기록 파싱
│  │  ├─ 14개 패턴 감지
│  │  │  ├─ 물타기?
│  │  │  ├─ 손실 매매?
│  │  │  ├─ DCA?
│  │  │  └─ ...
│  │  ├─ 위험도 판단
│  │  └─ Claude Sonnet: 결과 생성
│  │     └─ UserAnalysisResult 반환
│  │
│  └─ LLM B: YouTube 자막 분석 (tools.py → TranscriptAnalysisTool)
│     ├─ URL → 비디오 ID 추출 (transcript.py)
│     ├─ YouTube에서 자막 다운로드 (transcript.py)
│     ├─ 자막 청킹
│     ├─ Claude Sonnet: 섹션화 + 요약
│     │  ├─ "물타기" 섹션: ...
│     │  ├─ "손절" 섹션: ...
│     │  └─ ...
│     └─ TranscriptAnalysisResult 반환

3️⃣ Agent 의사결정 루프 (agent.py, 최대 5회)
반복 1️⃣:
├─ Agent (Mistral Small): 현재 상황 평가
│  ├─ 사용자 분석: ✅ 완료
│  ├─ 자막 분석: ✅ 완료
│  ├─ 검색: ❌ 아직
│  └─ 결정: "vector_search 실행!"
│
├─ 검색 쿼리 생성 (agent.py)
│  └─ Mistral Small:
│     "사용자가 감정적 물타기를 하고 있으며,
│      손실을 보고 있는 상황"
│
├─ 벡터 검색 (tools.py → VectorSearchTool)
│  ├─ 쿼리 임베딩 생성 (download_model.py 의 모델)
│  ├─ ChromaDB에서 검색 (chromadb_manager.py)
│  │  ├─ 자막 섹션 5개 찾음
│  │  └─ 커버리지: 85%
│  └─ VectorSearchResult 리스트 반환
│
└─ 결과 평가
├─ 커버리지 > 80%? → 충분함
└─ 신뢰도 > 90%? → 양호함
반복 2️⃣:
├─ Agent (Mistral Small): 상황 재평가
│  ├─ 검색 결과: ✅ 있음 (커버리지 85%)
│  └─ 결정: "validation 실행!"
│
├─ 검증 (tools.py → ValidationTool)
│  ├─ Claude Sonnet: 결과 검증
│  ├─ 신뢰도: 92%
│  └─ 이상 없음
│
└─ Agent 최종 결정: "stop"

4️⃣ 최종 조언 생성 (agent.py)
모든 정보 수집:
├─ 사용자 분석: {패턴, 강도, 위험도}
├─ YouTube 자막: {섹션, 요약, 감정}
├─ 검색 결과: {5개 관련 내용}
└─ Agent 판단: {2회 반복, 신뢰도 92%}
Claude Sonnet이 최종 조언 생성:
"당신의 매매를 분석한 결과,
감정적 물타기가 주된 문제입니다.

당신의 패턴:
- 삼성전자를 2번 매수 (강도 7/10)
- 평균 손실 -3%
- 평균 보유기간 45일

YouTube 조언:
[검색 결과 1] 물타기의 위험성...
[검색 결과 2] 손절 기준...
[검색 결과 3] 심리 관리...

종합 조언:
1. 물타기를 즉시 멈추세요
2. 손절 기준을 3%로 설정하세요
3. 하락장에서는 24시간 대기하세요

신뢰도: 92%"

5️⃣ 응답 반환 (main_server.py)
HTTP 200 OK
{
"success": true,
"analysis": {
"patterns": ["물타기", "손실_매매"],
"risk_level": "높음",
"confidence": 0.95
},
"search_results_count": 5,
"final_advice": "[위의 조언 텍스트]",
"confidence_score": 0.92
}