"""
AI/data/ 폴더의 모든 PDF를 실행 중인 서버의 /add-pdf 엔드포인트로 업로드합니다.

사용법:
  python seed_pdfs.py                                           # 기본 (localhost:8000)
  python seed_pdfs.py https://your-app.railway.app             # Railway 서버
  python seed_pdfs.py https://your-app.railway.app --reset     # DB 초기화 후 업로드
  python seed_pdfs.py https://your-app.railway.app --reset-only  # DB 초기화만
"""

import sys
import os
import requests

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

args = sys.argv[1:]
SERVER_URL = (args[0].rstrip("/") if args and not args[0].startswith("--") else "http://localhost:8000")
DO_RESET = "--reset" in args or "--reset-only" in args
RESET_ONLY = "--reset-only" in args


def reset_db() -> bool:
    print(f"\n🗑️  DB 초기화 중...")
    try:
        resp = requests.delete(f"{SERVER_URL}/clear-db")
        if resp.status_code == 200:
            print(f"  ✅ DB 초기화 완료")
            return True
        else:
            print(f"  ❌ 실패 ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False


def upload_pdf(pdf_path: str) -> bool:
    file_name = os.path.basename(pdf_path)
    print(f"\n📄 업로드 중: {file_name}")
    try:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                f"{SERVER_URL}/add-pdf",
                files={"file": (file_name, f, "application/pdf")},
            )
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✅ 완료 — {data.get('added_count', '?')}개 문서 추가")
            return True
        else:
            print(f"  ❌ 실패 ({resp.status_code}): {resp.text}")
            return False
    except Exception as e:
        print(f"  ❌ 오류: {e}")
        return False


def main():
    print(f"서버: {SERVER_URL}")

    if DO_RESET:
        if not reset_db():
            sys.exit(1)

    if RESET_ONLY:
        return

    if not os.path.isdir(DATA_DIR):
        print(f"❌ data 폴더 없음: {DATA_DIR}")
        sys.exit(1)

    pdf_files = sorted(
        os.path.join(DATA_DIR, f)
        for f in os.listdir(DATA_DIR)
        if f.lower().endswith(".pdf")
    )

    if not pdf_files:
        print(f"⚠️  {DATA_DIR} 에 PDF 없음")
        sys.exit(0)

    print(f"PDF: {len(pdf_files)}개 발견\n")

    # 서버 상태 확인
    try:
        r = requests.get(f"{SERVER_URL}/health", timeout=10)
        status = r.json().get("status", "unknown")
        if status != "healthy":
            print(f"⚠️  서버 상태: {status} — 계속 진행합니다")
        else:
            print(f"✅ 서버 상태: healthy")
    except Exception as e:
        print(f"⚠️  헬스체크 실패: {e} — 계속 진행합니다")

    ok = sum(1 for p in pdf_files if upload_pdf(p))
    print(f"\n{'='*40}")
    print(f"완료: {ok}/{len(pdf_files)}개 성공")


if __name__ == "__main__":
    main()
