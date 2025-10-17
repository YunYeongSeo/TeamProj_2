"""
TCP 채팅 서버
"""
import socket
import threading
import datetime
from config import TCP_HOST, TCP_PORT
from db.manager import verify_user, cleanup_session, update_session_activity, save_chat_message

# 클라이언트 목록 (전역)
clients = []
clients_lock = threading.Lock()


def broadcast(message_bytes: bytes, sender_sock: socket.socket):
    """모든 클라이언트에게 메시지 브로드캐스트"""
    with clients_lock:
        dead = []
        for client_info in clients:
            csock, addr, _authed = client_info[:3]
            if csock is sender_sock:
                continue
            try:
                csock.sendall(message_bytes)
            except:
                dead.append(client_info)
        for d in dead:
            clients.remove(d)
            try: 
                d[0].close()
            except: 
                pass


def force_disconnect_duplicate_sessions(emp_no: str, current_socket: socket.socket):
    """중복 세션의 기존 소켓 연결 강제 종료"""
    with clients_lock:
        disconnected = []
        for client_info in list(clients):
            if len(client_info) >= 3 and client_info[2] == emp_no:
                if client_info[0] != current_socket:
                    try:
                        client_info[0].sendall(
                            "SERVER: DUPLICATE_LOGIN - 다른 곳에서 로그인되어 연결을 종료합니다.\n".encode("utf-8")
                        )
                        client_info[0].close()
                        disconnected.append(client_info)
                    except:
                        pass
        
        for client_info in disconnected:
            if client_info in clients:
                clients.remove(client_info)
        
        if disconnected:
            print(f"[AUTH] {emp_no} 중복 연결 {len(disconnected)}개 강제 종료")


def handle_client(client_socket: socket.socket, addr):
    """클라이언트 연결 처리"""
    print(f"[TCP 연결] {addr} 접속")
    authed_emp = None
    session_id = None
    login_time_obj = None  # 🆕 로그인 시간 저장
    
    try:
        first = client_socket.recv(1024)
        if not first:
            print("[TCP] 첫 패킷 없음")
            return

        first_msg = first.decode("utf-8").strip()
        if not first_msg.startswith("LOGIN "):
            client_socket.sendall(
                "SERVER: LOGIN 먼저 수행하세요. 형식: LOGIN <emp_no> <password>\n".encode("utf-8")
            )
            return

        parts = first_msg.split(" ", 2)
        if len(parts) != 3:
            client_socket.sendall("SERVER: 형식 오류. LOGIN <emp_no> <password>\n".encode("utf-8"))
            return
        
        emp_no, password = parts[1].strip(), parts[2]
        client_ip = addr[0]
        
        # 🆕 로그인 시간 기록
        import datetime
        login_time_obj = datetime.datetime.now()
        
        ok, role, sess_id = verify_user(emp_no, password, client_ip)

        if not ok:
            client_socket.sendall(b"SERVER: LOGIN_FAIL\n")
            return

        authed_emp = emp_no
        session_id = sess_id
        
        # 기존 중복 연결 강제 종료
        force_disconnect_duplicate_sessions(emp_no, client_socket)
        
        # 새 클라이언트 등록
        with clients_lock:
            clients.append([client_socket, addr, authed_emp, session_id])

        client_socket.sendall(f"SERVER: 로그인 성공 {emp_no} {role}\n".encode("utf-8"))
        client_socket.sendall(f"SERVER: LOGIN_OK {role}\n".encode("ascii"))
        
        # 메시지 수신 루프
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            decoded = data.decode("utf-8").strip()
            if not decoded:
                continue
            
            # 세션 활동 업데이트
            update_session_activity(session_id)
            
            save_chat_message(authed_emp, decoded)
            now = datetime.datetime.now().strftime("%H:%M:%S")
            final = f"[{now}] {authed_emp} > {decoded}"
            broadcast(final.encode("utf-8"), client_socket)

    except Exception as e:
        print(f"[TCP 오류] {addr} : {e}")
    finally:
        # 🆕 세션 지속 시간 확인
        if session_id and login_time_obj:
            import datetime
            session_duration = (datetime.datetime.now() - login_time_obj).total_seconds()
            
            # 5초 이내에 끊긴 세션은 히스토리에서 삭제
            if session_duration < 5:
                try:
                    from db.manager import engine, text
                    with engine.begin() as conn:
                        conn.execute(
                            text("DELETE FROM login_history WHERE session_id = :sid"),
                            {"sid": session_id}
                        )
                    now = datetime.datetime.now().strftime("%H:%M:%S")
                    print(f"[{now}] [CLEANUP] 짧은 세션 히스토리 삭제: {authed_emp} (지속시간: {session_duration:.1f}초)")
                except Exception as e:
                    print(f"[CLEANUP] 히스토리 삭제 오류: {e}")
        
        # 세션 정리
        if session_id:
            cleanup_session(session_id)
        
        # 클라이언트 목록에서 제거
        with clients_lock:
            for i, client_info in enumerate(list(clients)):
                if len(client_info) >= 4 and client_info[3] == session_id:
                    clients.pop(i)
                    break
                elif len(client_info) >= 1 and client_info[0] is client_socket:
                    clients.pop(i)
                    break
        
        try: 
            client_socket.close()
        except: 
            pass
        print(f"[TCP 종료] {addr} 연결 종료 (emp_no: {authed_emp})")


def start_tcp_server():
    """TCP 채팅 서버 시작"""
    print(f"[SRV] TCP 채팅 서버 시작 준비: {TCP_HOST}:{TCP_PORT}")
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((TCP_HOST, TCP_PORT))
    srv.listen()
    print(f"[SRV] TCP 서버가 {TCP_HOST}:{TCP_PORT} 에서 실행 중입니다.")
    
    while True:
        csock, addr = srv.accept()
        threading.Thread(target=handle_client, args=(csock, addr), daemon=True).start()


def get_connected_clients_count():
    """연결된 클라이언트 수 반환"""
    with clients_lock:
        return len(clients)