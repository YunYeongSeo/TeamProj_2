#include "pch.h"
#include "LoginDlg.h"

#include <string>
#include <vector>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <atlconv.h>   // CT2A, CW2A

#pragma comment(lib, "ws2_32.lib")
#define IP "192.168.0.87"

// ===== 접속 대상 =====
static constexpr const char* kServerIpA = IP; // 같은 PC에서 서버면 127.0.0.1
static constexpr unsigned short kServerPort = 5000;

// 서버 성공 토큰 (기본 문자열)
static constexpr const char* kOkTokenAscii = "SERVER: LOGIN_OK";
static constexpr const char* kOkTokenUtf8 =
"SERVER: \xEB\xA1\x9C\xEA\xB7\xB8\xEC\x9D\xB8 \xEC\x84\xB1\xEA\xB3\xBC"; // "SERVER: 로그인 성공" UTF-8

// ===== 내부 유틸 =====
static bool SendAll(SOCKET s, const char* data, int len)
{
    int sent = 0;
    while (sent < len) {
        int n = send(s, data + sent, len - sent, 0);
        if (n <= 0) return false;
        sent += n;
    }
    return true;
}

// 비차단 connect + select 로 타임아웃 내 연결 확인
static bool PingServer(const char* ip, unsigned short port, int timeout_ms = 800)
{
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) return false;

    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) { WSACleanup(); return false; }

    // 비차단 전환
    u_long nb = 1;
    ioctlsocket(s, FIONBIO, &nb);

    sockaddr_in sa{};
    sa.sin_family = AF_INET;
    sa.sin_port = htons(port);
    if (inet_pton(AF_INET, ip, &sa.sin_addr) != 1) {
        closesocket(s); WSACleanup(); return false;
    }

    // 즉시 반환됨(비차단)
    connect(s, (SOCKADDR*)&sa, sizeof(sa));

    fd_set wfds; FD_ZERO(&wfds); FD_SET(s, &wfds);
    timeval tv{ timeout_ms / 1000, (timeout_ms % 1000) * 1000 };

    int r = select(0, nullptr, &wfds, nullptr, &tv);

    bool ok = false;
    if (r > 0 && FD_ISSET(s, &wfds)) {
        int err = 0; int len = sizeof(err);
        getsockopt(s, SOL_SOCKET, SO_ERROR, (char*)&err, &len);
        ok = (err == 0);
    }

    closesocket(s);
    WSACleanup();
    return ok;
}

// 서버가 배너를 먼저 보낼 수도 있으므로, 잠깐 대기 후 읽을 수 있으면 한 번 비워줌
static void DrainWelcomeBannerIfAny(SOCKET s, int wait_ms = 200)
{
    fd_set rfds; FD_ZERO(&rfds); FD_SET(s, &rfds);
    timeval tv{ wait_ms / 1000, (wait_ms % 1000) * 1000 };

    if (select(0, &rfds, nullptr, nullptr, &tv) > 0) {
        char tmp[1024];
        recv(s, tmp, sizeof(tmp), 0); // 배너만 비움(실패해도 무시)
    }
}

// ===== MFC 메시지 맵 =====
BEGIN_MESSAGE_MAP(CLoginDlg, CDialogEx)
    ON_BN_CLICKED(IDC_OK_BUTTON, &CLoginDlg::OnClickedOkButton)
    ON_BN_CLICKED(IDC_CANCEL_BUTTON, &CLoginDlg::OnClickedCancleButton)
END_MESSAGE_MAP()

BOOL CLoginDlg::OnInitDialog()
{
    BOOL b = CDialogEx::OnInitDialog();

    // 앱 실행하자마자 서버가 꺼져 있으면 알림
    if (!PingServer(kServerIpA, kServerPort, 800)) {
        AfxMessageBox(L"서버와 연결되어 있지 않습니다.\n서버를 먼저 실행해 주세요.");
    }
    return b;
}

void CLoginDlg::OnClickedOkButton()
{
    OnOK();
}

void CLoginDlg::OnClickedCancleButton()
{
    OnCancel();
}

// ---- 핵심: TCP로 즉시 로그인 검증 ----
bool CLoginDlg::VerifyWithTcp(const CString& emp, const CString& pw, CString& role)
{
    role.Empty(); // 기본값: 실패

    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
        return false;

    SOCKET s = socket(AF_INET, SOCK_STREAM, 0);
    if (s == INVALID_SOCKET) { WSACleanup(); return false; }

    // 합리적 타임아웃 (전송/수신 5초)
    int to = 5000;
    setsockopt(s, SOL_SOCKET, SO_RCVTIMEO, (const char*)&to, sizeof(to));
    setsockopt(s, SOL_SOCKET, SO_SNDTIMEO, (const char*)&to, sizeof(to));

    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(kServerPort);
    if (inet_pton(AF_INET, kServerIpA, &addr.sin_addr) != 1) {
        closesocket(s); WSACleanup(); return false;
    }

    if (connect(s, (SOCKADDR*)&addr, sizeof(addr)) == SOCKET_ERROR) {
        closesocket(s); WSACleanup(); return false;
    }

    // 서버가 먼저 배너(“로그인해주세요”)를 보낼 수도 있으니 잠깐 비워줌
    DrainWelcomeBannerIfAny(s, 200);

    // LOGIN emp pw\n (UTF-8) 전송
    CString line;
    // 비밀번호는 Trim 하지 않고 그대로 사용 (한글/공백 보존)
    line.Format(L"LOGIN %s %s\n", emp.GetString(), pw.GetString());

    CT2A a(line, CP_UTF8);
    const char* p = a.m_psz;
    const int   total = (int)strlen(p);

    if (!SendAll(s, p, total)) {
        closesocket(s); WSACleanup(); return false;
    }

    // 응답 수신
    std::string resp;
    char buf[1024];
    DWORD start = GetTickCount();
    for (;;)
    {
        fd_set rfds; FD_ZERO(&rfds); FD_SET(s, &rfds);
        timeval tv{ 0, 200 * 1000 }; // 200ms
        int r = select(0, &rfds, nullptr, nullptr, &tv);
        if (r > 0 && FD_ISSET(s, &rfds)) {
            int n = recv(s, buf, sizeof(buf), 0);
            if (n <= 0) break;
            resp.append(buf, buf + n);

            if (resp.find(kOkTokenAscii) != std::string::npos) break;
        }
        else {
            if (GetTickCount() - start > 1000) break; // 1초 제한
        }
        if (resp.size() > 2048) break;
    }

    closesocket(s);
    WSACleanup();

    // "SERVER: LOGIN_OK" 문자열이 있는지 확인
    size_t pos = resp.find(kOkTokenAscii);
    if (pos == std::string::npos) {
        // 한글 메시지도 확인 (백업)
        pos = resp.find(kOkTokenUtf8);
        if (pos == std::string::npos) {
            return false; // 로그인 성공 메시지가 없으면 실패
        }
    }

    // "SERVER: LOGIN_OK" 바로 다음부터 권한 문자열 추출
    size_t roleStart = pos + strlen(kOkTokenAscii);

    // role 문자열 앞 공백 건너뛰기
    while (roleStart < resp.length() && isspace(resp[roleStart])) {
        roleStart++;
    }

    if (roleStart >= resp.length()) {
        return false; // 권한 정보가 없으면 실패
    }

    // 공백 또는 줄바꿈 문자까지만 읽어서 role로 저장
    size_t roleEnd = resp.find_first_of(" \r\n", roleStart);
    if (roleEnd == std::string::npos) {
        roleEnd = resp.length();
    }

    std::string roleStr = resp.substr(roleStart, roleEnd - roleStart);
    role = CString(roleStr.c_str());
    role.Trim();

    return !role.IsEmpty(); // role이 비어있지 않으면 성공
}

void CLoginDlg::OnOK()
{
    CString id, pw;
    GetDlgItemText(IDC_ID_EDIT, id);
    GetDlgItemText(IDC_PW_EDIT, pw);

    id.Trim(); // ID는 공백 제거

    if (id.IsEmpty() || pw.IsEmpty()) {
        AfxMessageBox(L"사번/비밀번호를 입력하세요.");
        return;
    }

    CString role;
    // 서버(DB) 검증
    if (!VerifyWithTcp(id, pw, role)) {
        AfxMessageBox(L"로그인 실패: 사번/비밀번호가 올바르지 않거나 서버 응답이 없습니다.");
        return; // 로그인창 유지
    }

    // 권한 체크: ADMIN만 허용 (관리자 앱)
    if (role.CompareNoCase(L"ADMIN") != 0) {
        AfxMessageBox(L"접근 권한이 없는 아이디입니다.");
        return;
    }

    // 성공 > 값 저장하고 닫기
    m_id = id;
    m_pw = pw;

    EndDialog(IDOK);
}

void CLoginDlg::OnCancel()
{
    EndDialog(IDCANCEL);
}