# transcript.py
import os
import re
import traceback
from youtube_transcript_api import YouTubeTranscriptApi


def extract_video_id(url: str) -> str | None:
    """
    유튜브 URL에서 video ID 추출
    
    지원 형식:
    - https://www.youtube.com/watch?v=dQw4w9WgXcQ
    - https://youtu.be/dQw4w9WgXcQ
    - https://www.youtube.com/embed/dQw4w9WgXcQ
    """
    if not url:
        return None
    
    try:
        # 정규식: v=, youtu.be/, /embed/ 뒤의 11자리 ID
        regex = r"(?:v=|youtu\.be\/|\/embed\/)([0-9A-Za-z_-]{11})"
        match = re.search(regex, url)
        return match.group(1) if match else None
    except Exception as e:
        print(f"[Transcript] video_id 추출 실패: {e}")
        return None


def transcript(video_id: str) -> str | None:
    """
    YouTube 영상의 자막을 텍스트로 반환
    
    우선순위:
    1. 한국어 공식 자막
    2. 영어 공식 자막
    3. 한국어 자동생성 자막
    4. 영어 자동생성 자막
    
    Args:
        video_id: YouTube 영상 ID
    
    Returns:
        자막 텍스트 또는 None
    """
    if not video_id:
        return None

    print(f"\n[Transcript] 자막 추출 시도: {video_id}")

    # cookies.txt 확인 (IP 차단 방지)
    cookies_path = "cookies.txt"
    if os.path.exists(cookies_path):
        print("[Transcript] cookies.txt 발견 → 인증 사용")
        try:
            api = YouTubeTranscriptApi(cookies=cookies_path)
        except Exception:
            print("[Transcript] cookies 로드 실패 → 인증 없이 시도")
            api = YouTubeTranscriptApi()
    else:
        api = YouTubeTranscriptApi()

    try:
        # 자막 목록 조회
        transcript_list = api.list(video_id)

        # 사용 가능한 자막 출력
        print("[Transcript] 사용 가능한 자막:")
        for t in transcript_list:
            lang = getattr(t, "language", "unknown")
            code = getattr(t, "language_code", "unknown")
            is_generated = getattr(t, "is_generated", False)
            tag = "(자동생성)" if is_generated else "(공식)"
            print(f"  - {code} ({lang}) {tag}")

        # 자막 선택 (공식 자막 우선)
        try:
            selected = transcript_list.find_transcript(["ko", "en"])
            print(f"[Transcript] 공식 자막 선택: {getattr(selected, 'language_code', '?')}")
        except Exception:
            print("[Transcript] 공식 자막 없음 → 자동생성 자막 시도")
            try:
                selected = transcript_list.find_generated_transcript(["ko", "en"])
                print(f"[Transcript] 자동생성 자막 선택: {getattr(selected, 'language_code', '?')}")
            except Exception as e:
                print(f"[Transcript] 자막 선택 실패: {e}")
                return None

        # 자막 데이터 추출 및 결합
        snippets = selected.fetch()
        full_text = " ".join(s.get("text", "") for s in snippets)
        
        print(f"[Transcript] ✅ 완료: {len(full_text):,}자")
        return full_text

    except Exception as e:
        print(f"[Transcript] 자막 추출 실패: {e}")
        traceback.print_exc()
        return None
