"""
메인 실행 파일
"""
import sys
import threading
import logging
from chat.server import start_tcp_server
from web.flask_app import app
from db.manager import init_session_table, engine, session_cleanup_worker
from config import HTTP_PORT

# Flask 로깅 조정
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# 🆕 모듈화된 라우트만 import (routes.py 제거)
import web.routes.video     # 카메라 업로드
import web.routes.api       # API 엔드포인트
import web.routes.dashboard # 대시보드
import web.routes.internal  # 내부 페이지

def run_flask():
    """Flask 서버 실행"""
    print(f"[HTTP] Flask 서버 시작: http://0.0.0.0:{HTTP_PORT}")
    print(f"[HTTP] 통합 대시보드: http://localhost:{HTTP_PORT}/dashboard")
    print(f"[HTTP] 카메라 1: /upload_frame_1")
    print(f"[HTTP] 카메라 2: /upload_frame_2")
    app.run(host="0.0.0.0", port=HTTP_PORT, debug=False, threaded=True)

if __name__ == "__main__":
    try:
        # DB 연결 테스트
        with engine.connect() as conn:
            print("[DB] ✅ 데이터베이스 연결 성공")
        
        # 세션 테이블 초기화
        init_session_table()
        
        # 세션 정리 워커 시작
        cleanup_thread = threading.Thread(target=session_cleanup_worker, daemon=True)
        cleanup_thread.start()
        print("[DB] 세션 정리 워커 시작")
        
        # TCP 채팅 서버 시작
        tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
        tcp_thread.start()
        
        # Flask 서버 시작 (메인 스레드)
        run_flask()
        
    except KeyboardInterrupt:
        print("\n[SYSTEM] 서버 종료 중...")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] 서버 시작 실패: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)