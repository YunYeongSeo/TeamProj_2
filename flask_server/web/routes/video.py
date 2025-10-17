"""
영상 스트리밍 관련 라우트
"""
from flask import Response, request
from web.flask_app import (
    app, 
    update_frame_1,
    update_frame_2,
    get_latest_frame_1,
    get_latest_frame_2,
    video_stream_generator_1,
    video_stream_generator_2,
    no_signal_bytes
)
from barcode.detector import detect_balanced_barcodes
from chat.server import broadcast
import threading
import time
import datetime

# 🆕 카메라별 로그 관리
last_upload_log_time_1 = 0
last_upload_log_time_2 = 0
frame_count_1 = 0
frame_count_2 = 0
frame_count_start_time_1 = time.time()
frame_count_start_time_2 = time.time()

# ===== 카메라 1 업로드 =====
@app.route("/upload_frame", methods=["POST"])
@app.route("/upload_frame_1", methods=["POST"])
def upload_frame_1_route():
    """라즈베리파이 #1에서 JPEG 업로드 + 바코드 검출"""
    global last_upload_log_time_1, frame_count_1, frame_count_start_time_1
    
    try:
        data = request.get_data(cache=False)
        if not data:
            return "NoData", 400
        
        update_frame_1(data)
        
        frame_count_1 += 1
        
        # 🆕 5초마다 로그 출력
        current_time = time.time()
        if current_time - last_upload_log_time_1 >= 5.0:
            elapsed = current_time - frame_count_start_time_1
            actual_fps = frame_count_1 / elapsed if elapsed > 0 else 0
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            
            print(f"[{now_str}] [📹 카메라 1] 프레임 수신 중 (크기: {len(data):,}B, FPS: ~{actual_fps:.1f}, 누적: {frame_count_1})")
            
            last_upload_log_time_1 = current_time
            frame_count_1 = 0
            frame_count_start_time_1 = current_time
        
        # 바코드 검출
        threading.Thread(
            target=detect_balanced_barcodes, 
            args=(data, broadcast), 
            daemon=True
        ).start()
        
        return "OK", 200
    except Exception as e:
        print(f"[오류] 카메라 1: {e}")
        return "Error", 500


# ===== 카메라 2 업로드 ===== ← 핵심!
@app.route("/upload_frame_2", methods=["POST"])
def upload_frame_2_route():
    """라즈베리파이 #2에서 JPEG 업로드"""
    global last_upload_log_time_2, frame_count_2, frame_count_start_time_2
    
    try:
        data = request.get_data(cache=False)
        if not data:
            return "NoData", 400
        
        update_frame_2(data)
        
        frame_count_2 += 1
        
        # 🆕 5초마다 로그 출력
        current_time = time.time()
        if current_time - last_upload_log_time_2 >= 5.0:
            elapsed = current_time - frame_count_start_time_2
            actual_fps = frame_count_2 / elapsed if elapsed > 0 else 0
            now_str = datetime.datetime.now().strftime("%H:%M:%S")
            
            print(f"[{now_str}] [📹 카메라 2] 프레임 수신 중 (크기: {len(data):,}B, FPS: ~{actual_fps:.1f}, 누적: {frame_count_2})")
            
            last_upload_log_time_2 = current_time
            frame_count_2 = 0
            frame_count_start_time_2 = current_time
        
        return "OK", 200
    except Exception as e:
        print(f"[오류] 카메라 2: {e}")
        import traceback
        traceback.print_exc()
        return "Error", 500


# ===== 스트리밍 =====
@app.route("/video_feed")
@app.route("/video_feed_1")
def video_feed_1_route():
    """카메라 1 영상 스트리밍"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return Response(video_stream_generator_1(),
                    headers=headers,
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/video_feed_2")
def video_feed_2_route():
    """카메라 2 영상 스트리밍"""
    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return Response(video_stream_generator_2(),
                    headers=headers,
                    mimetype="multipart/x-mixed-replace; boundary=frame")


# ===== 최신 프레임 =====
@app.route("/latest_jpeg")
@app.route("/latest_jpeg_1")
def latest_jpeg_1_route():
    """카메라 1 최신 JPEG"""
    frame = get_latest_frame_1()
    data = frame if frame else no_signal_bytes
    return Response(data, mimetype="image/jpeg")


@app.route("/latest_jpeg_2")
def latest_jpeg_2_route():
    """카메라 2 최신 JPEG"""
    frame = get_latest_frame_2()
    data = frame if frame else no_signal_bytes
    return Response(data, mimetype="image/jpeg")