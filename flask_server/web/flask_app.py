from flask import Flask, Response, jsonify, request
import cv2
import threading
import time
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

app = Flask(__name__)

# ===== 데이터베이스 설정 =====
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'moble',  # ⚠️ config.py의 DB_PASS와 동일하게
    'database': 'prodmon',  # ⚠️ config.py의 DB_NAME과 동일하게
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci'
}

# ===== 온습도 더미 데이터 =====
current_temperature = 22.5
current_humidity = 45.0

# ===== 카메라 설정 =====
camera1 = None
camera2 = None
camera1_lock = threading.Lock()
camera2_lock = threading.Lock()

# ✅ 프레임 버퍼
latest_frame_1 = None
latest_frame_2 = None
frame_1_lock = threading.Lock()
frame_2_lock = threading.Lock()

# ✅ No Signal 이미지 (1x1 검은 픽셀 JPEG)
no_signal_bytes = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&\'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfc\xfe\xa2\x8a(\x00\xff\xd9'

# ✅ 프레임 age/size 추적
last_frame_time_1 = 0
last_frame_time_2 = 0
frame_size_1 = 0
frame_size_2 = 0

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')


# ===== ✅ video.py에서 사용하는 함수들 =====

def update_frame_1(frame_bytes):
    """카메라 1 프레임 업데이트"""
    global latest_frame_1, last_frame_time_1, frame_size_1
    with frame_1_lock:
        latest_frame_1 = frame_bytes
        last_frame_time_1 = time.time()
        frame_size_1 = len(frame_bytes) if frame_bytes else 0


def update_frame_2(frame_bytes):
    """카메라 2 프레임 업데이트"""
    global latest_frame_2, last_frame_time_2, frame_size_2
    with frame_2_lock:
        latest_frame_2 = frame_bytes
        last_frame_time_2 = time.time()
        frame_size_2 = len(frame_bytes) if frame_bytes else 0


def get_latest_frame_1():
    """카메라 1 최신 프레임 가져오기"""
    with frame_1_lock:
        return latest_frame_1


def get_latest_frame_2():
    """카메라 2 최신 프레임 가져오기"""
    with frame_2_lock:
        return latest_frame_2


def get_frame_age():
    """프레임 age (초)"""
    if last_frame_time_1 == 0:
        return -1
    return time.time() - last_frame_time_1


def get_frame_size():
    """프레임 크기"""
    return frame_size_1


# ✅✅✅ 누락된 함수 추가!
def video_stream_generator_1():
    """카메라 1 MJPEG 스트림 생성"""
    while True:
        frame = get_latest_frame_1()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + no_signal_bytes + b'\r\n')
        time.sleep(0.033)  # ~30fps


def video_stream_generator_2():
    """카메라 2 MJPEG 스트림 생성"""
    while True:
        frame = get_latest_frame_2()
        if frame:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + no_signal_bytes + b'\r\n')
        time.sleep(0.033)


# ===== 데이터베이스 연결 함수 =====
def get_db_connection():
    """MySQL 데이터베이스 연결"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"❌ DB 연결 실패: {e}")
        return None


# ===== 온습도 저장 함수 =====
def save_environment_data(log_type='scheduled'):
    """온습도 데이터를 DB에 저장"""
    connection = get_db_connection()
    if not connection:
        print("❌ DB 연결 실패로 온습도 저장 불가")
        return False
    
    try:
        cursor = connection.cursor()
        now_kst = datetime.now(KST)
        
        query = """
        INSERT INTO environment_logs 
        (temperature, humidity, recorded_at, log_type) 
        VALUES (%s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            current_temperature,
            current_humidity,
            now_kst,
            log_type
        ))
        
        connection.commit()
        
        print(f"✅ 온습도 저장 성공 [{log_type}]: "
              f"온도 {current_temperature}°C, "
              f"습도 {current_humidity}%, "
              f"시간 {now_kst.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return True
        
    except Error as e:
        print(f"❌ 온습도 저장 실패: {e}")
        return False
        
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


# ===== 정기 저장 작업 (매일 00시) =====
def scheduled_save_job():
    """매일 00시에 실행되는 온습도 저장 작업"""
    print(f"⏰ 정기 저장 작업 시작: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}")
    save_environment_data(log_type='scheduled')


# ===== 스케줄러 설정 =====
scheduler = BackgroundScheduler(timezone=KST)
scheduler.add_job(
    func=scheduled_save_job,
    trigger='cron',
    hour=0,
    minute=0,
    id='daily_environment_save',
    name='매일 00시 온습도 저장'
)
scheduler.start()


# ===== 온습도 센서 시뮬레이션 =====
def update_environment_data():
    """온습도 데이터 업데이트"""
    global current_temperature, current_humidity
    
    import random
    
    while True:
        current_temperature += random.uniform(-0.5, 0.5)
        current_humidity += random.uniform(-1.0, 1.0)
        
        current_temperature = max(10, min(40, current_temperature))
        current_humidity = max(20, min(80, current_humidity))
        
        time.sleep(10)


# ===== 서버 시작 시 실행 (main.py에서 호출 전에 실행됨) =====
print("=" * 50)
print("🚀 Flask 앱 초기화")
print("=" * 50)

# 온습도 센서 시뮬레이션 스레드 시작
print("🌡️  온습도 센서 시작...")
sensor_thread = threading.Thread(target=update_environment_data, daemon=True)
sensor_thread.start()

# 서버 시작 시 온습도 저장
print("💾 서버 시작 시 온습도 저장...")
save_environment_data(log_type='startup')

print("=" * 50)
print(f"✅ Flask 앱 준비 완료")
print(f"📊 스케줄러 실행 중 (매일 00시 자동 저장)")
print("=" * 50)