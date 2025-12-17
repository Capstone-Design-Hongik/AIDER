import os
import re
from youtube_transcript_api import YouTubeTranscriptApi

def extract_video_id(url):
    """
    유튜브 URL에서 video_id를 추출하는 함수
    지원 형식:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    """
    try:
        # 정규표현식을 사용하여 11자리의 ID 추출
        regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
        match = re.search(regex, url)
        if match:
            return match.group(1)
        return None
    except:
        return None

def transcript(video_id):
    try:
        print(f"[Transcript] 자막 추출 시도: {video_id}")
        
        # 1. cookies.txt 파일 경로 설정
        # Railway 서버에 올렸을 때 같은 폴더에 있다고 가정
        cookies_path = "cookies.txt"
        
        if not os.path.exists(cookies_path):
            print("[Warning] 'cookies.txt' 파일이 없습니다! IP 차단될 확률이 높습니다.")
            cookies_path = None # 파일 없으면 쿠키 없이 시도
        else:
            print("[Info] 'cookies.txt'를 발견하여 인증을 시도합니다.")
        
        api = YouTubeTranscriptApi()

        transcript_list = api.list(video_id)

        print("[Transcript] 자막 추출 성공 !")
        print("사용 가능한 자막:")
        try:
            for t in transcript_list:
                # 객체에 language 속성이 있는지 확인
                lang = getattr(t, 'language', 'unknown')
                code = getattr(t, 'language_code', 'unknown')
                print(f"  - {code} ({lang})")
        except:
            pass

        # 한국어 또는 영어 자막 찾기
        try:
            transcript = transcript_list.find_transcript(['ko', 'en'])
        except:
            print("[Info] 공식 자막이 없어 자동 생성 자막을 가져옵니다.")
            transcript = transcript_list.find_generated_transcript(['ko', 'en'])

        lang = getattr(transcript, 'language', 'unknown')
        print(f"\n선택된 자막: {lang}")

        # 자막 텍스트 합치기
        full_text = ""
        for snippet in transcript.fetch():
            full_text += snippet.text + " " # 문장 이어 붙이기
            
        return full_text

    except Exception as e:
        print(f"[Error] 자막 추출 실패: {e}")
        import traceback
        traceback.print_exc()
        return None