"""
시스템 설정 파일
"""
import os

# DB 설정
DB_HOST = "localhost"
DB_PORT = 3306
DB_NAME = "prodmon"
DB_USER = "Project_2"
DB_PASS = "moble"

# HTTP 서버 설정
HTTP_HOST = "0.0.0.0"
HTTP_PORT = 8000

# TCP 채팅 서버 설정
TCP_HOST = "0.0.0.0"
TCP_PORT = 5000

# 🆕 세션 관리 설정
SESSION_TIMEOUT = 3600  # 1시간
SESSION_CLEANUP_INTERVAL = 300  # 5분마다 정리

# 영상 스트리밍 설정
MAX_STREAM_FPS = 30
NO_SIGNAL_AFTER = 5.0

# 바코드 검출 설정
BARCODE_DETECTION_INTERVAL = 0.8
BARCODE_COOLDOWN = 2.5 # 30초 동안 같은 제품 검출 -> 2.5초로 수정
CONFIDENCE_THRESHOLD = 60.0

# 바코드 제품 매핑
BARCODE_PRODUCT_MAP = {
    "8804973304842": "스트로베리향",
    "8804973304835": "피치향",
    "8804973304828": "스피어민트향",
    "8804973304811": "페퍼민트향",
    "8804973308789": "꿀,레몬향",
    "8804973308802": "배,비파향",
}

# 바코드 이미지 저장 설정
SAVE_BARCODE_IMAGES = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BARCODE_IMAGE_DIR = os.path.join(BASE_DIR, "barcode_images")

# ==== 원격 GPIO 제어(라즈베리) ====
PI_GPIO_HOST = "192.168.0.97"   # 라즈베리 IP
CONVEYOR_FORWARD_PIN = 17
CONVEYOR_BACKWARD_PIN = 27