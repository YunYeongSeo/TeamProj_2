import cv2
import numpy as np
import time
import threading
import datetime
import os
from collections import deque, Counter
from config import (
    BARCODE_PRODUCT_MAP,
    BARCODE_DETECTION_INTERVAL,
    BARCODE_COOLDOWN,
    CONFIDENCE_THRESHOLD,
    BARCODE_IMAGE_DIR,
    SAVE_BARCODE_IMAGES
)
from barcode.utils import validate_barcode_balanced, calculate_barcode_confidence_balanced

# 채팅 알림 on/off 플래그 (config에 없으면 기본 False)
try:
    from config import BARCODE_BROADCAST_ENABLED
except Exception:
    BARCODE_BROADCAST_ENABLED = False

# pyzbar 초기화
try:
    from pyzbar import pyzbar
    BARCODE_DETECTION_AVAILABLE = True
    print("[INIT] ✅ 서버측 바코드 검출 라이브러리 로드 성공 (Balance 모드)")
    _test = pyzbar.decode(np.zeros((100, 100), dtype=np.uint8))
    print(f"[INIT] ✅ pyzbar Balance 기능 테스트 성공: {len(_test)}개 (빈 이미지)")
except ImportError:
    BARCODE_DETECTION_AVAILABLE = False
    print("[WARNING] ❌ pyzbar 라이브러리 없음 - 바코드 검출 비활성화 (pip install pyzbar)")
except Exception as e:
    BARCODE_DETECTION_AVAILABLE = False
    print(f"[WARNING] ❌ pyzbar 라이브러리 오류: {e}")

# 검출 히스토리 및 상태 변수
barcode_detection_history = deque(maxlen=500)
barcode_detection_lock = threading.Lock()
last_barcode_detection_time = 0
last_detected_barcode = None
barcode_detection_count = 0
rejected_barcode_count = 0

# 이미지 폴더 생성 보장
os.makedirs(BARCODE_IMAGE_DIR, exist_ok=True)
print(f"[INIT] 바코드 이미지 저장 폴더 준비: {BARCODE_IMAGE_DIR} (저장 활성화: {SAVE_BARCODE_IMAGES})")


def _compute_bbox(barcode_obj):
    """
    바코드 객체로부터 bbox를 계산합니다.
    polygon 정보가 충분하지 않으면 rect 정보로 대체(fallback)합니다.
    """
    try:
        points = getattr(barcode_obj, "polygon", [])
        if len(points) >= 4:
            xs = [int(p.x) for p in points]
            ys = [int(p.y) for p in points]
            return [min(xs), min(ys), max(xs), max(ys)]
        
        # Fallback to rect
        rect = barcode_obj.rect
        return [int(rect.left), int(rect.top), int(rect.left + rect.width), int(rect.top + rect.height)]
    except Exception:
        return None


def save_barcode_image(frame_data, barcode_data, bbox, product_name):
    """
    바코드 검출 이미지 저장 (한글 경로 문제 해결 버전)
    """
    if not SAVE_BARCODE_IMAGES:
        return None

    try:
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            print(f"[{datetime.datetime.now():%H:%M:%S}] [ERROR] 프레임 디코딩 실패")
            return None

        if bbox and len(bbox) == 4:
            x1, y1, x2, y2 = map(int, bbox)
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
            cv2.putText(frame, str(barcode_data), (x1, max(0, y1 - 30)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            cv2.putText(frame, str(product_name), (x1, max(0, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{ts}_{barcode_data}.jpg"
        filepath = os.path.join(BARCODE_IMAGE_DIR, filename)

        # --- ✨ 핵심 수정 ✨ ---
        # cv2.imwrite 대신 imencode와 python의 open을 사용하여 한글 경로 문제를 해결합니다.
        extension = '.jpg'
        result, encoded_img = cv2.imencode(extension, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

        if not result:
            print(f"[{datetime.datetime.now():%H:%M:%S}] [ERROR] 이미지 인코딩 실패: {filename}")
            return None
        
        with open(filepath, mode='wb') as f:
            encoded_img.tofile(f)
        # --- ✨ ---

        print(f"[{datetime.datetime.now():%H:%M:%S}] [IMAGE] 바코드 이미지 저장: {filename}")
        return filename
        
    except Exception as e:
        print(f"[{datetime.datetime.now():%H:%M:%S}] [ERROR] 바코드 이미지 저장 중 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


def detect_balanced_barcodes(frame_data, broadcast_fn=None):
    """🎯 Balance 바코드 검출 (등록 제품 우선 + 안정적인 bbox 및 저장 로직)"""
    global last_barcode_detection_time, last_detected_barcode, barcode_detection_count, rejected_barcode_count

    if not BARCODE_DETECTION_AVAILABLE:
        return []

    current_time = time.time()
    if current_time - last_barcode_detection_time < BARCODE_DETECTION_INTERVAL:
        return []

    try:
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None: return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        barcodes = pyzbar.decode(gray)
        if not barcodes:
            enhanced = cv2.convertScaleAbs(gray, alpha=1.1, beta=10)
            barcodes = pyzbar.decode(enhanced)
        if not barcodes: return []
        
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now_str}] [BALANCE] 검출된 바코드: {len(barcodes)}개")

        registered, unregistered = [], []
        seen, rejected_log = set(), []

        for bc in barcodes:
            try:
                code = bc.data.decode("utf-8")
                if code in seen: continue
                seen.add(code)

                is_valid, reason = validate_barcode_balanced(code)
                if not is_valid:
                    rejected_log.append({"barcode_data": code, "reason": reason})
                    continue

                conf = calculate_barcode_confidence_balanced(bc)
                if conf < CONFIDENCE_THRESHOLD:
                    rejected_log.append({"barcode_data": code, "reason": f"낮은_신뢰도_{conf:.1f}%"})
                    continue
                
                candidate_info = (bc, code, conf, reason)
                if code in BARCODE_PRODUCT_MAP:
                    registered.append(candidate_info)
                else:
                    unregistered.append(candidate_info)
            except Exception as e:
                print(f"[{now_str}] [BALANCE] ❌ 후보 처리 오류: {e}")
        
        rejected_barcode_count += len(rejected_log)

        final_candidates = registered or unregistered
        if registered and unregistered:
            print(f"[{now_str}] [BALANCE] 🚫 미등록 {len(unregistered)}개 무시 (등록 제품 우선)")

        valid_after_cooldown = [
            cand for cand in final_candidates
            if not (last_detected_barcode and last_detected_barcode["data"] == cand[1] and \
                    current_time - last_detected_barcode["time"] < BARCODE_COOLDOWN)
        ]

        if len(valid_after_cooldown) > 1:
            valid_after_cooldown.sort(key=lambda x: x[2], reverse=True)
            print(f"[{now_str}] [BALANCE] 🎯 최고 신뢰도 선택: {valid_after_cooldown[0][1]}")
            valid_after_cooldown = [valid_after_cooldown[0]]

        if not valid_after_cooldown: return []

        detections = []
        for bc, code, conf, reason in valid_after_cooldown:
            product_name = BARCODE_PRODUCT_MAP.get(code, f"미등록제품({code})")
            
            # --- ✨ 핵심 수정 ✨ ---
            # 1. bbox를 항상 계산 (rect fallback 포함)
            bbox = _compute_bbox(bc)
            
            # 2. 이미지 저장을 항상 시도
            image_filename = save_barcode_image(frame_data, code, bbox, product_name)
            
            # 3. DB 저장을 항상 시도 (이미지 저장 실패와 무관)
            try:
                from db.manager import save_barcode_detection
                save_barcode_detection(code, product_name, conf, image_filename, bbox)
            except Exception as e:
                print(f"[{now_str}] [ERROR] DB 저장 오류: {e}")
            # --- ✨ ---
            
            detection_result = {
                "barcode_data": code, "barcode_type": bc.type, "product_name": product_name,
                "is_registered": code in BARCODE_PRODUCT_MAP, "bbox": bbox, "confidence": conf,
                "points": [(p.x, p.y) for p in getattr(bc, "polygon", [])] or None,
                "timestamp": current_time, "detection_source": "server_balanced",
                "validation_reason": reason, "image_filename": image_filename
            }
            detections.append(detection_result)
            last_detected_barcode = {"data": code, "time": current_time}
            print(f"[{now_str}] [BALANCE] 🎉 검출 성공: {code} → {product_name} ({conf:.1f}%)")

        if detections:
            last_barcode_detection_time = current_time
            barcode_detection_count += len(detections)
            
            with barcode_detection_lock:
                product_counts = Counter([d["product_name"] for d in detections])
                barcode_detection_history.append({
                    "timestamp": current_time, "total_count": len(detections),
                    "product_distribution": dict(product_counts), "detections": detections,
                    "rejected_barcodes": rejected_log[:3], "rejected_count": len(rejected_log),
                    "detection_source": "server_balanced"
                })

            if BARCODE_BROADCAST_ENABLED and broadcast_fn:
                try:
                    msg = f"🎯 {detections[0]['product_name']} 검출!"
                    final_msg = f"[{datetime.datetime.now():%H:%M:%S}] BALANCE > {msg}"
                    broadcast_fn(final_msg.encode("utf-8"), None)
                except Exception as e:
                    print(f"[BALANCE] broadcast 실패: {e}")

        return detections

    except Exception as e:
        print(f"[{datetime.datetime.now():%H:%M:%S}] [ERROR] Balance 바코드 검출 오류: {e}")
        import traceback; traceback.print_exc()
        return []

# get_barcode_stats, get_barcode_history, add_external_barcode_data 함수는 변경 없음
# ... (기존 코드와 동일) ...
def get_barcode_stats():
    """바코드 검출 통계 반환"""
    with barcode_detection_lock:
        recent_data = [d for d in barcode_detection_history 
                      if time.time() - d['timestamp'] < 600]
        hourly_data = [d for d in barcode_detection_history 
                      if time.time() - d['timestamp'] < 3600]
        
        total_recent = sum(d['total_count'] for d in recent_data)
        total_hourly = sum(d['total_count'] for d in hourly_data)
        
        rejected_recent = sum(d.get('rejected_count', 0) for d in recent_data)
        rejected_hourly = sum(d.get('rejected_count', 0) for d in hourly_data)
        
        product_stats_recent = Counter()
        for data in recent_data:
            product_stats_recent.update(data.get('product_distribution', {}))
        
        product_stats_hourly = Counter()
        for data in hourly_data:
            product_stats_hourly.update(data.get('product_distribution', {}))
        
        server_detections = sum(1 for d in recent_data if d.get('detection_source') == 'server_balanced')
        external_detections = len(recent_data) - server_detections
        
        return {
            'recent_10min': {
                'total': total_recent, 'rejected': rejected_recent,
                'product_distribution': dict(product_stats_recent), 'events': len(recent_data),
                'server_detections': server_detections, 'external_detections': external_detections
            },
            'recent_1hour': {
                'total': total_hourly, 'rejected': rejected_hourly,
                'product_distribution': dict(product_stats_hourly), 'events': len(hourly_data)
            }
        }

def get_barcode_history(limit=50):
    """바코드 검출 이력 반환"""
    with barcode_detection_lock:
        return list(barcode_detection_history)[-min(limit, 150):]

def add_external_barcode_data(data):
    """외부 바코드 데이터 추가"""
    with barcode_detection_lock:
        barcode_detection_history.append(data)