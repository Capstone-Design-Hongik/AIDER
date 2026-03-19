# 모델 먼저 다운로드
from huggingface_hub import snapshot_download

# [수정] chroma_client.py 에서 사용하는 모델과 동일하게 맞춤
# 기존: jhgan/ko-sroberta-multitask (다른 모델 → dimension mismatch 위험)
# 수정: BAAI/bge-m3 (다국어 지원, chroma_client.py 와 동일)
local_dir = "./local_model"

print(f"[{local_dir}] 폴더에 모델 다운로드를 시작합니다...")
print("모델: BAAI/bge-m3 (한국어/영어 다국어 지원)")

snapshot_download(
    repo_id="BAAI/bge-m3",
    local_dir=local_dir,
    local_dir_use_symlinks=False
)

print("✅ 다운로드 완료! 이제 인터넷 연결 없이도 실행 가능합니다.")
print(f"   로컬 경로: {local_dir}")