from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig, GenericProxyConfig
from typing import List, Dict, Optional
import traceback
from config import YOUTUBE_PROXY_HOST, YOUTUBE_PROXY_PORT, YOUTUBE_PROXY_USER, YOUTUBE_PROXY_PASS


def _make_api(use_proxy: bool) -> YouTubeTranscriptApi:
    """proxy 적용 또는 직접 연결 API 인스턴스 반환 (v1.x 전용)"""
    if use_proxy and YOUTUBE_PROXY_USER and YOUTUBE_PROXY_PASS:
        if YOUTUBE_PROXY_HOST == "p.webshare.io":
            proxy_config = WebshareProxyConfig(
                proxy_username=YOUTUBE_PROXY_USER,
                proxy_password=YOUTUBE_PROXY_PASS,
            )
            print(f"[Transcript] Webshare 프록시 사용")
        else:
            url = f"http://{YOUTUBE_PROXY_USER}:{YOUTUBE_PROXY_PASS}@{YOUTUBE_PROXY_HOST}:{YOUTUBE_PROXY_PORT}"
            proxy_config = GenericProxyConfig(http_url=url, https_url=url)
            print(f"[Transcript] Generic 프록시 사용: {YOUTUBE_PROXY_HOST}:{YOUTUBE_PROXY_PORT}")
        return YouTubeTranscriptApi(proxy_config=proxy_config)

    if use_proxy:
        print("[Transcript] ⚠️  프록시 자격증명 없음 → 직접 연결로 대체")
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

        우선순위:
        1. proxy + 공식 자막 (ko/en)
        2. proxy + 자동생성 자막
        3. 직접 연결 + 공식 자막
        4. 직접 연결 + 자동생성 자막
        """
        if not video_id:
            return None

        print(f"\n[Transcript] 자막 추출 시도: {video_id}")

        for attempt, (use_proxy, label) in enumerate([(True, "proxy"), (False, "직접 연결")]):
            try:
                print(f"[Transcript] 시도 {attempt + 1}: {label}")
                api = _make_api(use_proxy)
                transcript_list = api.list(video_id)

                try:
                    for t in transcript_list:
                        lang = getattr(t, "language", "unknown")
                        code = getattr(t, "language_code", "unknown")
                        print(f"  - {code} ({lang})")
                except Exception:
                    pass

                try:
                    selected = transcript_list.find_transcript(["ko", "en"])
                    print(f"[Transcript] 공식 자막 선택: {getattr(selected, 'language_code', '?')}")
                except Exception:
                    print("[Transcript] 공식 자막 없음 → 자동생성 자막 시도")
                    selected = transcript_list.find_generated_transcript(["ko", "en"])
                    print(f"[Transcript] 자동생성 자막 선택: {getattr(selected, 'language_code', '?')}")

                full_text = " ".join(snippet.text for snippet in selected.fetch()).strip()
                print(f"[Transcript] ✅ 완료 ({label}): {len(full_text):,}자")
                return full_text

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
