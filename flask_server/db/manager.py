"""
데이터베이스 연결 및 세션 관리
"""
from sqlalchemy import create_engine, text
import bcrypt
import datetime
import time
import uuid
import hashlib
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS, SESSION_TIMEOUT, SESSION_CLEANUP_INTERVAL

# DB 엔진 생성
DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800, echo=False)


def init_session_table():
    """세션 테이블 및 로그인 히스토리 테이블 생성"""
    try:
        with engine.begin() as conn:
            # 세션 테이블 (session_type 포함)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS user_session (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emp_no VARCHAR(20) NOT NULL,
                    session_id VARCHAR(64) UNIQUE NOT NULL,
                    session_type ENUM('WEB', 'TCP') DEFAULT 'TCP',
                    client_ip VARCHAR(45),
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_temporary BOOLEAN DEFAULT FALSE,
                    INDEX idx_emp_no (emp_no),
                    INDEX idx_session_id (session_id),
                    INDEX idx_session_type (session_type),
                    INDEX idx_last_activity (last_activity)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            
            # 🆕 is_temporary 컬럼 추가 (없으면)
            try:
                conn.execute(text("""
                    ALTER TABLE user_session 
                    ADD COLUMN is_temporary BOOLEAN DEFAULT FALSE AFTER is_active
                """))
                print("[DB] user_session 테이블에 is_temporary 컬럼 추가")
            except:
                pass
            
            # 기존 테이블에 session_type 컬럼 추가 (없으면)
            try:
                conn.execute(text("""
                    ALTER TABLE user_session 
                    ADD COLUMN session_type ENUM('WEB', 'TCP') DEFAULT 'TCP' AFTER session_id
                """))
                print("[DB] user_session 테이블에 session_type 컬럼 추가")
            except:
                pass
            
            # 로그인 히스토리 테이블 (session_type 포함)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    emp_no VARCHAR(20) NOT NULL,
                    session_id VARCHAR(64) NULL,
                    session_type ENUM('WEB', 'TCP') DEFAULT 'TCP',
                    client_ip VARCHAR(45),
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP NULL,
                    session_duration INT DEFAULT 0,
                    login_status ENUM('SUCCESS', 'FAIL') DEFAULT 'SUCCESS',
                    fail_reason VARCHAR(100) NULL,
                    user_agent VARCHAR(200) NULL,
                    INDEX idx_emp_no (emp_no),
                    INDEX idx_session_id (session_id),
                    INDEX idx_session_type (session_type),
                    INDEX idx_login_time (login_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            
            # 기존 테이블에 session_type 컬럼 추가
            try:
                conn.execute(text("""
                    ALTER TABLE login_history 
                    ADD COLUMN session_type ENUM('WEB', 'TCP') DEFAULT 'TCP' AFTER session_id
                """))
                print("[DB] login_history 테이블에 session_type 컬럼 추가")
            except:
                pass
            
            # 바코드 검출 로그 테이블
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS barcode_detection_log (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    barcode VARCHAR(20) NOT NULL,
                    product_name VARCHAR(100),
                    confidence DECIMAL(5,2),
                    image_path VARCHAR(255),
                    image_filename VARCHAR(100),
                    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bbox_x1 INT,
                    bbox_y1 INT,
                    bbox_x2 INT,
                    bbox_y2 INT,
                    INDEX idx_barcode (barcode),
                    INDEX idx_detected_at (detected_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            
        print("[DB] 세션 테이블 및 로그인 히스토리 테이블 초기화 완료")
    except Exception as e:
        print(f"[DB] 테이블 초기화 오류: {e}")


def verify_user(emp_no: str, password: str, client_ip: str, session_type: str = 'TCP'):
    """사용자 인증 및 세션 생성"""
    try:
        with engine.begin() as conn:
            # 1. 사용자 인증
            row = conn.execute(
                text("SELECT password_hash, is_active, role FROM user_account WHERE emp_no = :e LIMIT 1"),
                {"e": emp_no}
            ).first()

            if not row:
                save_login_history(emp_no, client_ip, 'FAIL', '존재하지_않는_계정', None, None, session_type, record_anyway=True)
                return False, None, None

            pwd_hash, is_active, role = row[0], row[1], row[2]
            
            if isinstance(pwd_hash, (bytes, bytearray, memoryview)):
                pwd_hash = bytes(pwd_hash).decode("utf-8", errors="ignore")

            if not is_active:
                save_login_history(emp_no, client_ip, 'FAIL', '비활성화된_계정', None, None, session_type, record_anyway=True)
                return False, None, None

            if not bcrypt.checkpw(password.encode("utf-8"), pwd_hash.encode("utf-8")):
                save_login_history(emp_no, client_ip, 'FAIL', '비밀번호_불일치', None, None, session_type, record_anyway=True)
                return False, None, None

            # 🆕 2. 같은 사원번호의 임시 세션 모두 삭제
            conn.execute(
                text("""
                    DELETE FROM user_session 
                    WHERE emp_no = :e 
                    AND session_type = :type 
                    AND is_temporary = 1
                """),
                {"e": emp_no, "type": session_type}
            )

            # 3. 5초 이상 된 정규 세션 정리
            existing = conn.execute(
                text("""
                    SELECT session_id, login_time 
                    FROM user_session 
                    WHERE emp_no = :e 
                    AND session_type = :type 
                    AND is_active = 1
                    AND is_temporary = 0
                    AND TIMESTAMPDIFF(SECOND, login_time, NOW()) > 5
                """),
                {"e": emp_no, "type": session_type}
            ).fetchall()

            for old_session in existing:
                old_sid, login_time = old_session[0], old_session[1]
                logout_time = datetime.datetime.now()
                duration = int((logout_time - login_time).total_seconds())
                
                conn.execute(
                    text("""
                        UPDATE login_history 
                        SET logout_time = :logout, 
                            session_duration = :duration,
                            fail_reason = '중복_로그인'
                        WHERE session_id = :sid AND logout_time IS NULL
                    """),
                    {"logout": logout_time, "duration": duration, "sid": old_sid}
                )
            
            conn.execute(
                text("""
                    UPDATE user_session 
                    SET is_active = 0 
                    WHERE emp_no = :e 
                    AND session_type = :type 
                    AND is_active = 1
                    AND is_temporary = 0
                    AND TIMESTAMPDIFF(SECOND, login_time, NOW()) > 5
                """),
                {"e": emp_no, "type": session_type}
            )

            # 🆕 4. 1초 이내의 최근 세션을 임시로 변경
            recent_sessions = conn.execute(
                text("""
                    SELECT session_id 
                    FROM user_session 
                    WHERE emp_no = :e 
                    AND session_type = :type 
                    AND is_active = 1 
                    AND is_temporary = 0
                    AND TIMESTAMPDIFF(SECOND, login_time, NOW()) <= 1
                    ORDER BY login_time DESC
                """),
                {"e": emp_no, "type": session_type}
            ).fetchall()

            # 모든 최근 세션을 임시로 변경
            for (old_sid,) in recent_sessions:
                conn.execute(
                    text("UPDATE user_session SET is_temporary = 1 WHERE session_id = :sid"),
                    {"sid": old_sid}
                )
                
                # 히스토리에서 삭제
                conn.execute(
                    text("DELETE FROM login_history WHERE session_id = :sid"),
                    {"sid": old_sid}
                )
                
                now = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
                print(f"[{now}] [LOGIN] 이전 세션을 임시로 변경: {old_sid[:16]}... (히스토리 삭제)")

            # 5. 새 세션 생성 (항상 정규 세션)
            new_session_id = hashlib.sha256(
                f"{emp_no}_{session_type}_{uuid.uuid4()}_{datetime.datetime.now().isoformat()}".encode()
            ).hexdigest()
            
            conn.execute(
                text("""
                    INSERT INTO user_session(emp_no, session_id, session_type, client_ip, is_temporary) 
                    VALUES (:e, :s, :type, :ip, 0)
                """),
                {"e": emp_no, "s": new_session_id, "type": session_type, "ip": client_ip}
            )

            # 로그인 기록
            save_login_history(emp_no, client_ip, 'SUCCESS', None, None, new_session_id, session_type, record_anyway=True)

            return True, (role or "STAFF").upper(), new_session_id
            
    except Exception as e:
        print(f"[AUTH] 인증 오류: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None


def cleanup_session(session_id: str):
    """세션 정리 (로그아웃)"""
    if not session_id:
        return
    
    try:
        with engine.begin() as conn:
            # 🆕 임시 세션 확인
            session_info = conn.execute(
                text("SELECT login_time, is_temporary FROM user_session WHERE session_id = :s AND is_active = 1"),
                {"s": session_id}
            ).first()
            
            if session_info:
                login_time, is_temporary = session_info[0], session_info[1]
                
                # 정규 세션만 히스토리 업데이트
                if not is_temporary:
                    logout_time = datetime.datetime.now()
                    duration = int((logout_time - login_time).total_seconds())
                    
                    conn.execute(
                        text("""
                            UPDATE login_history 
                            SET logout_time = :logout, session_duration = :duration
                            WHERE session_id = :sid AND logout_time IS NULL
                        """),
                        {"logout": logout_time, "duration": duration, "sid": session_id}
                    )
            
            # 세션 삭제 (임시든 정규든)
            conn.execute(
                text("DELETE FROM user_session WHERE session_id = :s"),
                {"s": session_id}
            )
            
    except Exception as e:
        print(f"[SESSION] 정리 오류: {e}")


def update_session_activity(session_id: str):
    """세션 활동 시간 업데이트"""
    if not session_id:
        return
    
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE user_session 
                    SET last_activity = CURRENT_TIMESTAMP 
                    WHERE session_id = :s AND is_active = 1
                """),
                {"s": session_id}
            )
    except Exception:
        pass


def session_cleanup_worker():
    """세션 정리 워커 (백그라운드)"""
    while True:
        time.sleep(SESSION_CLEANUP_INTERVAL)
        
        try:
            with engine.begin() as conn:
                # 🆕 임시 세션 중 5초 이상 된 것은 즉시 삭제 (히스토리 기록 안 함)
                conn.execute(
                    text("""
                        DELETE FROM user_session 
                        WHERE is_temporary = 1 
                        AND TIMESTAMPDIFF(SECOND, login_time, NOW()) > 5
                    """)
                )
                
                # 만료된 정규 세션 조회
                expired = conn.execute(
                    text("""
                        SELECT session_id, login_time 
                        FROM user_session 
                        WHERE is_active = 1 
                        AND is_temporary = 0
                        AND TIMESTAMPDIFF(SECOND, last_activity, NOW()) > :timeout
                    """),
                    {"timeout": SESSION_TIMEOUT}
                ).fetchall()
                
                for session_id, login_time in expired:
                    logout_time = datetime.datetime.now()
                    duration = int((logout_time - login_time).total_seconds())
                    
                    conn.execute(
                        text("""
                            UPDATE login_history 
                            SET logout_time = :logout, 
                                session_duration = :duration,
                                fail_reason = '타임아웃'
                            WHERE session_id = :sid AND logout_time IS NULL
                        """),
                        {"logout": logout_time, "duration": duration, "sid": session_id}
                    )
                    
                    conn.execute(
                        text("UPDATE user_session SET is_active = 0 WHERE session_id = :s"),
                        {"s": session_id}
                    )
                    
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] [SESSION_CLEANUP] 만료된 세션 정리: {session_id[:16]}...")
                    
        except Exception as e:
            print(f"[SESSION_CLEANUP] 오류: {e}")


def save_login_history(emp_no: str, client_ip: str, status: str, fail_reason: str = None, user_agent: str = None, session_id: str = None, session_type: str = 'TCP', record_anyway: bool = False):
    """로그인 이력 저장"""
    try:
        # 🆕 record_anyway=False이고 임시 세션이면 기록 안 함
        if not record_anyway:
            with engine.connect() as conn:
                if session_id:
                    is_temp = conn.execute(
                        text("SELECT is_temporary FROM user_session WHERE session_id = :s LIMIT 1"),
                        {"s": session_id}
                    ).scalar()
                    
                    if is_temp:
                        return  # 임시 세션은 히스토리에 기록 안 함
        
        with engine.begin() as conn:
            # 중복 체크
            if status == 'SUCCESS' and session_id:
                recent = conn.execute(
                    text("SELECT COUNT(*) FROM login_history WHERE session_id = :sid"),
                    {"sid": session_id}
                ).scalar()
                
                if recent > 0:
                    return
            
            conn.execute(
                text("""
                    INSERT INTO login_history(emp_no, session_id, session_type, client_ip, login_status, fail_reason, user_agent)
                    VALUES (:e, :sid, :type, :ip, :status, :reason, :agent)
                """),
                {
                    "e": emp_no,
                    "sid": session_id,
                    "type": session_type,
                    "ip": client_ip,
                    "status": status,
                    "reason": fail_reason,
                    "agent": user_agent
                }
            )
            
            now = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] [LOGIN_HISTORY] ✅ {status} ({session_type}): {emp_no} from {client_ip}")
    except Exception as e:
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}] [LOGIN_HISTORY] ❌ 저장 오류: {e}")


def save_chat_message(emp_no: str, content: str):
    """채팅 메시지 저장"""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO chat_message(sender_emp_no, content) VALUES (:e, :c)"),
                {"e": emp_no, "c": content}
            )
    except Exception:
        pass


def get_active_sessions():
    """활성 세션 목록 (정규 세션만)"""
    try:
        with engine.connect() as conn:
            sessions = conn.execute(
                text("""
                    SELECT emp_no, session_type, client_ip, login_time, last_activity 
                    FROM user_session 
                    WHERE is_active = 1 
                    AND is_temporary = 0
                    ORDER BY login_time DESC
                """)
            ).fetchall()
            
            return [{
                "emp_no": s[0],
                "session_type": s[1],
                "client_ip": s[2],
                "login_time": s[3].isoformat() if s[3] else None,
                "last_activity": s[4].isoformat() if s[4] else None
            } for s in sessions]
    except Exception:
        return []


def get_active_session_count():
    """활성 세션 수 (정규 세션만)"""
    try:
        with engine.connect() as conn:
            return conn.execute(
                text("SELECT COUNT(*) FROM user_session WHERE is_active = 1 AND is_temporary = 0")
            ).scalar()
    except Exception:
        return 0


def get_login_history(limit=50, emp_no=None, status=None, days=None):
    """로그인 이력 조회"""
    try:
        with engine.connect() as conn:
            query = """
                SELECT emp_no, session_type, client_ip, login_time, logout_time, 
                       session_duration, login_status, fail_reason, user_agent
                FROM login_history WHERE 1=1
            """
            params = {}
            
            if emp_no:
                query += " AND emp_no = :emp_no"
                params["emp_no"] = emp_no
            
            if status:
                query += " AND login_status = :status"
                params["status"] = status
            
            if days:
                query += " AND login_time >= DATE_SUB(NOW(), INTERVAL :days DAY)"
                params["days"] = days
            
            query += " ORDER BY login_time DESC LIMIT :limit"
            params["limit"] = limit
            
            rows = conn.execute(text(query), params).fetchall()
            
            return [{
                "emp_no": row[0],
                "session_type": row[1],
                "client_ip": row[2],
                "login_time": row[3].isoformat() if row[3] else None,
                "logout_time": row[4].isoformat() if row[4] else None,
                "session_duration": row[5],
                "login_status": row[6],
                "fail_reason": row[7],
                "user_agent": row[8]
            } for row in rows]
    except Exception:
        return []


def get_login_statistics(days=7):
    """로그인 통계"""
    try:
        with engine.connect() as conn:
            total = conn.execute(
                text("SELECT COUNT(*) FROM login_history WHERE login_time >= DATE_SUB(NOW(), INTERVAL :days DAY) AND login_status = 'SUCCESS'"),
                {"days": days}
            ).scalar() or 0
            
            failed = conn.execute(
                text("SELECT COUNT(*) FROM login_history WHERE login_time >= DATE_SUB(NOW(), INTERVAL :days DAY) AND login_status = 'FAIL'"),
                {"days": days}
            ).scalar() or 0
            
            avg_duration = conn.execute(
                text("SELECT AVG(session_duration) FROM login_history WHERE login_time >= DATE_SUB(NOW(), INTERVAL :days DAY) AND session_duration > 0"),
                {"days": days}
            ).scalar()
            
            return {
                "days": days,
                "total_logins": total,
                "failed_logins": failed,
                "success_rate": round((total / (total + failed) * 100), 2) if (total + failed) > 0 else 0,
                "avg_session_duration": int(avg_duration) if avg_duration else 0
            }
    except Exception:
        return {"days": days, "total_logins": 0, "failed_logins": 0, "success_rate": 0, "avg_session_duration": 0}


def save_barcode_detection(barcode_data, product_name, confidence, image_filename, bbox):
    """바코드 검출 저장"""
    try:
        from config import BARCODE_IMAGE_DIR
        
        with engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO barcode_detection_log
                    (barcode, product_name, confidence, image_path, image_filename, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                    VALUES (:barcode, :product, :conf, :path, :filename, :x1, :y1, :x2, :y2)
                """),
                {
                    "barcode": barcode_data,
                    "product": product_name,
                    "conf": confidence,
                    "path": f"{BARCODE_IMAGE_DIR}/{image_filename}",
                    "filename": image_filename,
                    "x1": bbox[0] if bbox else None,
                    "y1": bbox[1] if bbox else None,
                    "x2": bbox[2] if bbox else None,
                    "y2": bbox[3] if bbox else None
                }
            )
    except Exception:
        pass


def get_barcode_detections_with_images(limit=50, barcode=None):
    """바코드 검출 이력 조회"""
    try:
        with engine.connect() as conn:
            query = """
                SELECT id, barcode, product_name, confidence, 
                       image_path, image_filename, detected_at,
                       bbox_x1, bbox_y1, bbox_x2, bbox_y2
                FROM barcode_detection_log WHERE 1=1
            """
            params = {}
            
            if barcode:
                query += " AND barcode = :barcode"
                params["barcode"] = barcode
            
            query += " ORDER BY detected_at DESC LIMIT :limit"
            params["limit"] = limit
            
            rows = conn.execute(text(query), params).fetchall()
            
            return [{
                "id": row[0],
                "barcode": row[1],
                "product_name": row[2],
                "confidence": float(row[3]) if row[3] else 0,
                "image_path": row[4],
                "image_filename": row[5],
                "detected_at": row[6].isoformat() if row[6] else None,
                "bbox": [row[7], row[8], row[9], row[10]] if row[7] else None
            } for row in rows]
    except Exception:
        return []