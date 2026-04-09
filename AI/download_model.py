# download_model.py
from huggingface_hub import snapshot_download

# BGE-M3: 한국어 완벽 지원 + 1024차원
MODEL_ID = "BAAI/bge-m3"
local_dir = "./local_model"

print(f"\n{'='*60}")
print(f"📥 [{local_dir}] 폴더에 모델 다운로드를 시작합니다...")
print(f"{'='*60}")
print(f"\n모델: {MODEL_ID}")
print(f"사용 이유:")
print(f"  ✅ 한국어 포함 다국어 완벽 지원")
print(f"  ✅ 1024차원 고정 (MRL 폐기)")
print(f"  ✅ 최대 8192 토큰 컨텍스트 지원")
print(f"  ✅ RAG 검색에 최적화됨")

snapshot_download(
    repo_id=MODEL_ID,
    local_dir=local_dir,
    local_dir_use_symlinks=False,
    # 불필요한 포맷 제외 (다운로드 시간 단축)
    ignore_patterns=[
        "*.msgpack",
        "flax_model*",
        "tf_model*",
        "rust_model*",
        "*.onnx"
    ],
)

print(f"\n{'='*60}")
print(f"✅ 다운로드 완료!")
print(f"{'='*60}")
print(f"✅ 로컬 경로: {local_dir}")
print(f"✅ 이제 인터넷 연결 없이도 실행 가능합니다.")
print(f"\n[다음 단계]")
print(f"1. 환경 변수 설정: export HF_TOKEN=your_token")
print(f"2. 서버 실행: python main_local.py")
print(f"3. API 문서: http://localhost:8000/docs")
