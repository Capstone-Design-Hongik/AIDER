from youtube_transcript_api import YouTubeTranscriptApi
from typing import List, Dict, Optional
import traceback


class TranscriptManager:
    """YouTube 자막 관리"""

    @staticmethod
    def extract_video_id(url: str) -> str:
        """YouTube URL에서 비디오 ID 추출"""
        try:
            if "youtube.com/watch?v=" in url:
                return url.split("v=")[1].split("&")[0]
            elif "youtu.be/" in url:
                return url.split("youtu.be/")[1].split("?")[0]
            else:
                raise ValueError(f"Invalid YouTube URL: {url}")
        except Exception as e:
            print(f"❌ URL 파싱 오류: {e}")
            raise

    @staticmethod
    def transcript(video_id: str) -> Optional[str]:
        """
        YouTube 자막을 텍스트로 반환.

        우선순위:
        1. 한국어/영어 공식 자막
        2. 한국어/영어 자동생성 자막
        """
        if not video_id:
            return None

        print(f"\n[Transcript] 자막 추출 시도: {video_id}")

        try:
            # ✅ 이미지 코드 기반 — 인스턴스 생성 후 .list() 호출
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            # 사용 가능한 자막 출력
            print("[Transcript] 사용 가능한 자막:")
            try:
                for t in transcript_list:
                    lang = getattr(t, "language", "unknown")
                    code = getattr(t, "language_code", "unknown")
                    print(f"  - {code} ({lang})")
            except Exception:
                pass

            # 공식 자막 우선, 없으면 자동생성
            try:
                selected = transcript_list.find_transcript(["ko", "en"])
                print(f"[Transcript] 공식 자막 선택: {getattr(selected, 'language_code', '?')}")
            except Exception:
                print("[Transcript] 공식 자막 없음 → 자동생성 자막 시도")
                selected = transcript_list.find_generated_transcript(["ko", "en"])
                print(f"[Transcript] 자동생성 자막 선택: {getattr(selected, 'language_code', '?')}")

            # ✅ 이미지 코드 기반 — snippet.text 로 접근
            full_text = ""
            for snippet in selected.fetch():
                full_text += snippet.text + " "

            full_text = full_text.strip()
            print(f"[Transcript] ✅ 완료: {len(full_text):,}자")
            return full_text

        except Exception as e:
            print(f"[Transcript] 자막 추출 실패: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def get_transcript_with_timestamps(
        video_id: str,
        languages: List[str] = ["ko", "en"],
    ) -> List[Dict]:
        """타임스탬프 포함 자막 반환"""
        if not video_id:
            return []

        try:
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            try:
                selected = transcript_list.find_transcript(languages)
            except Exception:
                selected = transcript_list.find_generated_transcript(languages)

            result = []
            for snippet in selected.fetch():
                result.append({
                    "text":     snippet.text,
                    "start":    snippet.start,
                    "duration": snippet.duration,
                })

            print(f"[Transcript] ✅ {len(result)}개 항목 추출")
            return result

        except Exception as e:
            print(f"❌ 타임스탬프 자막 추출 실패: {e}")
            traceback.print_exc()
            return []

    @staticmethod
    def chunk_transcript(
        transcript: str,
        chunk_size: int = 500,
        chunk_overlap: int = 80,
    ) -> List[str]:
        """자막을 청크로 분할"""
        chunks = []
        start  = 0

        while start < len(transcript):
            end = min(start + chunk_size, len(transcript))
            chunks.append(transcript[start:end])
            start = end - chunk_overlap

        print(f"[Transcript] 청킹 완료: {len(chunks)}개 청크")
        return chunks