import os
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
from typing import List, Dict, Optional
import traceback


def _make_api(use_proxy: bool) -> YouTubeTranscriptApi:
    """proxy 적용 또는 직접 연결 API 인스턴스 반환"""
    proxy_url = os.environ.get("HTTPS_PROXY")
    if use_proxy and proxy_url:
        print(f"[Transcript] 프록시 사용: {proxy_url.split('@')[-1]}")
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(https_url=proxy_url)
        )
    if use_proxy and not proxy_url:
        print("[Transcript] ⚠️  HTTPS_PROXY 미설정 → 직접 연결로 대체")
    return YouTubeTranscriptApi()


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
        proxy 실패 시 직접 연결로 fallback.
        """
        if not video_id:
            return None

        print(f"\n[Transcript] 자막 추출 시도: {video_id}")

        for attempt, (use_proxy, label) in enumerate([(True, "proxy"), (False, "직접 연결")]):
            try:
                print(f"[Transcript] 시도 {attempt + 1}: {label}")
                api = _make_api(use_proxy)
                result = api.fetch(video_id, languages=["ko", "en"])
                full_text = " ".join(s.text for s in result).strip()
                print(f"[Transcript] ✅ 완료 ({label}): {len(full_text):,}자")
                return full_text

            except (TranscriptsDisabled, NoTranscriptFound) as e:
                print(f"[Transcript] 자막 없음: {e}")
                return None

            except VideoUnavailable as e:
                print(f"[Transcript] 영상 없음: {e}")
                return None

            except Exception as e:
                print(f"[Transcript] {label} 실패: {e}")
                if attempt == 1:
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
            api = _make_api(use_proxy=True)
            result = api.fetch(video_id, languages=languages)
            snippets = [
                {"text": s.text, "start": s.start, "duration": s.duration}
                for s in result
            ]
            print(f"[Transcript] ✅ {len(snippets)}개 항목 추출")
            return snippets

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
        start = 0
        while start < len(transcript):
            end = min(start + chunk_size, len(transcript))
            chunks.append(transcript[start:end])
            start = end - chunk_overlap
        print(f"[Transcript] 청킹 완료: {len(chunks)}개 청크")
        return chunks
