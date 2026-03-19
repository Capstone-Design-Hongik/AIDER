# 유튜브 영상에서 자막 추출
import os
import re
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str):
    """
    유튜브 URL에서 video_id를 추출하는 함수
    지원 형식:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    try:
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"[Error] video_id 추출 실패: {e}")
        return None


def transcript(video_id: str):
    try:
        print(f"[Transcript] 자막 추출 시도: {video_id}")

        # ── 1. cookies.txt 경로 확인 ──────────────────────
        cookies_path = "cookies.txt"
        if not os.path.exists(cookies_path):
            print("[Warning] 'cookies.txt' 파일이 없습니다! IP 차단될 확률이 높습니다.")
            cookies_path = None
        else:
            print("[Info] 'cookies.txt'를 발견하여 인증을 시도합니다.")

        # ── 2. API 초기화 (쿠키 실제로 전달) ──────────────
        # [수정] cookies_path를 생성자에 실제로 전달
        api = YouTubeTranscriptApi(cookies=cookies_path) if cookies_path else YouTubeTranscriptApi()

        transcript_list = api.list(video_id)

        print("[Transcript] 자막 목록 조회 성공!")
        try:
            for t in transcript_list:
                lang = getattr(t, 'language', 'unknown')
                code = getattr(t, 'language_code', 'unknown')
                print(f"  - {code} ({lang})")
        except Exception:
            pass  # 자막 목록 출력 실패는 무시

        # ── 3. 한국어 → 영어 순으로 자막 탐색 ────────────
        try:
            selected = transcript_list.find_transcript(['ko', 'en'])
        except Exception:
            print("[Info] 공식 자막이 없어 자동 생성 자막을 가져옵니다.")
            selected = transcript_list.find_generated_transcript(['ko', 'en'])

        lang = getattr(selected, 'language', 'unknown')
        print(f"\n[Transcript] 선택된 자막: {lang}")

        # ── 4. 자막 텍스트 합치기 ──────────────────────────
        full_text = " ".join(snippet.text for snippet in selected.fetch())
        print(f"[Transcript] ✅ 자막 추출 완료! 총 {len(full_text)}자")
        return full_text

    except Exception as e:
        print(f"[Error] 자막 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None