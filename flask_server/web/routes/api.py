"""
API 엔드포인트 (서버는 컨베이어 '원하는 상태'만 관리)
- 라즈베리파이는 /api/conveyor/desired 를 주기적으로 폴링하여
  run=True(동작) / False(정지)에 맞춰 로컬에서 2.0s 전진 → 1.5s 정지 루프를 제어.
"""

from flask import jsonify, request, send_from_directory, abort, session
import os
import datetime
import threading

# 기존 Flask 앱과 유틸 가져오기 (새 Flask() 만들지 말 것!)
from web.flask_app import app, get_frame_age, get_frame_size

# DB/통계 관련 매니저
from db.manager import (
    get_active_session_count,
    get_active_sessions,
    get_login_history,
    get_login_statistics,
    get_barcode_detections_with_images,
    update_session_activity,
)

# 채팅 서버 접속자 수
from chat.server import get_connected_clients_count

# 설정값
from config import (
    BARCODE_DETECTION_INTERVAL,
    BARCODE_COOLDOWN,
    CONFIDENCE_THRESHOLD,
    BARCODE_IMAGE_DIR,
)

# 바코드 통계
from barcode.detector import (
    get_barcode_stats,
    BARCODE_DETECTION_AVAILABLE,
    barcode_detection_count,
    rejected_barcode_count,
)

# =========================
# 환경 데이터 (온/습도) 저장소
# =========================
latest_environment = {
    "temperature": None,
    "humidity": None,
    "sensor_id": None,
    "location": None,
    "timestamp": None,
}
environment_lock = threading.Lock()


@app.before_request
def before_request_handler():
    """모든 요청 전에 세션 활동 업데이트"""
    try:
        # 정적 이미지/스트림 등은 업데이트 제외
        if request.path.startswith("/barcode_images/"):
            return None
        if request.path.startswith("/video_feed"):
            return None
        if request.path.startswith("/latest_jpeg"):
            return None

        if "session_id" in session:
            session_id = session.get("session_id")
            if session_id:
                update_session_activity(session_id)
    except Exception as e:
        import traceback
        print(f"[WARNING] before_request 오류 (무시): {e}")
        traceback.print_exc()


# ==============
# 기본/상태 API
# ==============
@app.route("/health")
def health():
    """헬스 체크"""
    return "OK", 200


@app.route("/stats")
def stats():
    """시스템 통계"""
    age = get_frame_age()
    sz = get_frame_size()
    active_sessions_count = get_active_session_count()

    barcode_stats_data = get_barcode_stats()
    recent_data = barcode_stats_data["recent_10min"]

    # 환경 데이터 스냅샷
    with environment_lock:
        env_data = latest_environment.copy()

    return jsonify({
        "last_frame_age_sec": age,
        "latest_frame_size": sz,
        "max_stream_fps": 30,
        "active_sessions": active_sessions_count,
        "connected_clients": get_connected_clients_count(),
        "recent_barcode_detections": recent_data["total"],
        "recent_barcode_rejections": recent_data["rejected"],
        "barcode_detection_events": recent_data["events"],
        "barcode_detection_enabled": BARCODE_DETECTION_AVAILABLE,
        "barcode_detection_source": "server_balanced",
        "barcode_detections_count": barcode_detection_count,
        "rejected_barcodes_count": rejected_barcode_count,
        "detection_interval": BARCODE_DETECTION_INTERVAL,
        "cooldown": BARCODE_COOLDOWN,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "balance_mode": True,
        "environment": env_data,
    })


@app.route("/sessions")
def sessions_route():
    """현재 활성 세션 목록"""
    session_list = get_active_sessions()
    return jsonify({
        "active_sessions": len(session_list),
        "sessions": session_list
    })


# =====================
# 환경 데이터 수신/조회
# =====================
@app.route("/api/environment", methods=["POST"])
def receive_environment():
    """라즈베리파이로부터 온습도 센서 데이터 수신"""
    global latest_environment
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data"}), 400

        temperature = data.get("temperature")
        humidity = data.get("humidity")
        if temperature is None or humidity is None:
            return jsonify({"error": "Missing temperature or humidity"}), 400

        with environment_lock:
            latest_environment["temperature"] = temperature
            latest_environment["humidity"] = humidity
            latest_environment["sensor_id"] = data.get("sensor_id", "Unknown")
            latest_environment["location"] = data.get("location", "Unknown")
            latest_environment["timestamp"] = data.get(
                "timestamp",
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )

        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        print(
            f"[{now_str}] 🌡️  [환경 데이터] 온도: {temperature}°C, 습도: {humidity}% "
            f"(센서: {data.get('sensor_id', 'Unknown')})"
        )

        return jsonify({
            "success": True,
            "message": "Environment data received",
            "data": {"temperature": temperature, "humidity": humidity},
        }), 200

    except Exception as e:
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] ❌ [환경 데이터] 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/environment", methods=["GET"])
def get_environment():
    """최신 온습도 데이터 조회"""
    with environment_lock:
        data = latest_environment.copy()

    if data["temperature"] is None:
        return jsonify({"success": False, "message": "No environment data available"}), 404

    return jsonify({"success": True, "data": data}), 200


# ==============
# 바코드 통계
# ==============
@app.route("/barcode_stats")
def barcode_stats_route():
    """바코드 통계 API"""
    try:
        stats = get_barcode_stats()
        return jsonify(stats), 200
    except Exception as e:
        print(f"[ERROR] /barcode_stats 오류: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "recent_10min": {
                "total": 0,
                "rejected": 0,
                "product_distribution": {},
                "events": 0,
                "server_detections": 0,
                "external_detections": 0,
            },
            "recent_1hour": {
                "total": 0,
                "rejected": 0,
                "product_distribution": {},
                "events": 0,
            },
        }), 200


@app.route("/barcode_images/<path:filename>")
def serve_barcode_image(filename):
    """바코드 이미지 제공"""
    try:
        abs_dir = os.path.abspath(BARCODE_IMAGE_DIR)
        if not os.path.exists(abs_dir):
            print(f"[IMAGE] ❌ 디렉토리 없음: {abs_dir}")
            return "Image directory not found", 404

        safe_filename = os.path.basename(filename)
        filepath = os.path.join(abs_dir, safe_filename)
        if not os.path.exists(filepath):
            print(f"[IMAGE] ❌ 파일 없음: {safe_filename}")
            return "Image not found", 404

        real_path = os.path.realpath(filepath)
        real_dir = os.path.realpath(abs_dir)
        if not real_path.startswith(real_dir):
            print("[IMAGE] ❌ 보안 위반")
            return "Access denied", 403

        print(f"[IMAGE] ✅ 서빙: {safe_filename}")
        return send_from_directory(directory=abs_dir, path=safe_filename, mimetype="image/jpeg")

    except Exception as e:
        print(f"[IMAGE] ❌ 오류: {e}")
        import traceback
        traceback.print_exc()
        return f"Server error: {str(e)}", 500


@app.route("/api/barcode_detections_with_images")
def api_barcode_detections_with_images():
    """바코드 검출 이력 (이미지 포함)"""
    limit = request.args.get("limit", 50, type=int)
    barcode = request.args.get("barcode", None)

    detections = get_barcode_detections_with_images(limit=limit, barcode=barcode)
    return jsonify({"count": len(detections), "detections": detections}), 200


@app.route("/api/login_history")
def api_login_history():
    """로그인 이력 API"""
    limit = request.args.get("limit", 50, type=int)
    emp_no = request.args.get("emp_no", None)
    status = request.args.get("status", None)
    days = request.args.get("days", None, type=int)

    history = get_login_history(limit=limit, emp_no=emp_no, status=status, days=days)
    return jsonify({"count": len(history), "history": history}), 200


@app.route("/api/login_statistics")
def api_login_statistics():
    """로그인 통계 API"""
    days = request.args.get("days", 7, type=int)
    stats = get_login_statistics(days=days)
    return jsonify(stats), 200


@app.route("/test_barcode_now", methods=["POST"])
def test_barcode_now():
    """바코드 검출 강제 실행 (테스트용)"""
    try:
        from web.flask_app import get_latest_frame_1
        from barcode.detector import detect_balanced_barcodes

        frame = get_latest_frame_1()
        if not frame:
            return jsonify({"success": False, "error": "프레임 없음"}), 200

        detections = detect_balanced_barcodes(frame, None)
        return jsonify({
            "success": True,
            "detections_count": len(detections),
            "detections": detections,
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================
# 컨베이어 '원하는 상태' 관리 (서버는 상태만 제공)
# - 라즈베리파이는 /api/conveyor/desired 를 폴링
# - /api/conveyor/start|stop|set|toggle 로 상태 갱신
# ============================================

_conveyor_state_lock = threading.Lock()
_CONVEYOR_DESIRED_RUN = True       # 서버 시작 시 기본값: 동작
_CONVEYOR_UPDATED_AT = datetime.datetime.utcnow()

def _set_desired_run(run: bool):
    global _CONVEYOR_DESIRED_RUN, _CONVEYOR_UPDATED_AT
    with _conveyor_state_lock:
        _CONVEYOR_DESIRED_RUN = bool(run)
        _CONVEYOR_UPDATED_AT = datetime.datetime.utcnow()

def _snapshot():
    with _conveyor_state_lock:
        return {
            "run": _CONVEYOR_DESIRED_RUN,
            "updated_at_utc": _CONVEYOR_UPDATED_AT.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

@app.route("/api/conveyor/desired", methods=["GET"])
def conveyor_desired():
    """라즈베리가 주기적으로 읽는 엔드포인트"""
    return jsonify(_snapshot()), 200

@app.route("/api/conveyor/status", methods=["GET"])
def conveyor_status():
    """사람/클라이언트 확인용 상태 엔드포인트"""
    snap = _snapshot()
    return jsonify({
        "desired": snap,
        "note": "Server manages desired run/stop only. Motor is controlled on Raspberry Pi.",
    }), 200

@app.route("/api/conveyor/start", methods=["GET", "POST"])
def conveyor_start():
    _set_desired_run(True)
    print("[Conveyor] START (desired run=True)")
    return jsonify({"success": True, "action": "start", **_snapshot()}), 200

@app.route("/api/conveyor/stop", methods=["GET", "POST"])
def conveyor_stop():
    _set_desired_run(False)
    print("[Conveyor] STOP (desired run=False)")
    return jsonify({"success": True, "action": "stop", **_snapshot()}), 200

@app.route("/api/conveyor/set", methods=["GET", "POST"])
def conveyor_set():
    """
    run 상태를 명시적으로 설정
      - GET  : /api/conveyor/set?run=1  또는 run=0
      - POST : {"run": true} 또는 {"run": false}
    """
    val = None
    if request.method == "GET":
        q = request.args.get("run")
        if q is not None:
            val = str(q).lower() in ("1", "true", "on", "start", "run")
    else:
        if request.is_json:
            body = request.get_json(silent=True) or {}
            if "run" in body:
                val = bool(body["run"])
            elif "mode" in body:
                val = str(body["mode"]).lower() in ("start", "run", "on", "1", "true")

    if val is None:
        return jsonify({"success": False, "error": "missing run parameter"}), 400

    _set_desired_run(val)
    print(f"[Conveyor] SET desired run={val}")
    return jsonify({"success": True, **_snapshot()}), 200

@app.route("/api/conveyor/toggle", methods=["POST", "GET"])
def conveyor_toggle():
    """현재 상태 토글"""
    with _conveyor_state_lock:
        new_val = not _CONVEYOR_DESIRED_RUN
    _set_desired_run(new_val)
    print(f"[Conveyor] TOGGLE → {new_val}")
    return jsonify({"success": True, **_snapshot()}), 200
