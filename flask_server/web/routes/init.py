"""
라우트 모듈 통합 - 순서 중요!
"""
# video.py를 가장 먼저 import (우선순위 높게)
from web.routes import video
from web.routes import api
from web.routes import internal
from web.routes import dashboard

print("[ROUTES] ✅ 모듈화된 라우트 로드 완료")