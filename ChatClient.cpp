#include "pch.h"
#include "ChatClient.h"
#include <atlconv.h> // for CT2A

ChatClient::ChatClient()
    : m_hNotifyWnd(NULL)
    , m_socket(INVALID_SOCKET)
    , m_bIsConnected(FALSE)
    , m_bLoginSuccess(FALSE)
    , m_pReceiveThread(nullptr)
    , m_port(0)
{
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
}

ChatClient::~ChatClient()
{
    Disconnect();
    WSACleanup();
}

BOOL ChatClient::Connect(HWND hNotifyWnd, const CString& ip, UINT port, const CString& empNo, const CString& password)
{
    if (m_socket != INVALID_SOCKET) {
        Disconnect();
    }

    m_hNotifyWnd = hNotifyWnd;
    m_ip = ip;
    m_port = port;
    m_empNo = empNo;
    m_password = password;

    m_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (m_socket == INVALID_SOCKET) return FALSE;

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons((u_short)m_port);
    if (inet_pton(AF_INET, CW2A(m_ip), &serverAddr.sin_addr) != 1) {
        closesocket(m_socket);
        m_socket = INVALID_SOCKET;
        return FALSE;
    }

    if (connect(m_socket, (SOCKADDR*)&serverAddr, sizeof(serverAddr)) == SOCKET_ERROR) {
        closesocket(m_socket);
        m_socket = INVALID_SOCKET;
        return FALSE;
    }

    m_bIsConnected = TRUE;
    m_pReceiveThread = AfxBeginThread(ReceiveThread, this);

    // 연결 성공 알림
    ::PostMessage(m_hNotifyWnd, WM_USER_CONNECTION_STATUS, (WPARAM)TRUE, 0);

    SendLoginInfo();
    return TRUE;
}

void ChatClient::Disconnect()
{
    if (m_socket != INVALID_SOCKET) {
        closesocket(m_socket);
        m_socket = INVALID_SOCKET;
    }
    m_bIsConnected = FALSE;
    // 스레드가 스스로 종료될 때까지 잠시 기다릴 수 있으나, 여기서는 생략
    m_pReceiveThread = nullptr;
}

BOOL ChatClient::SendMessage(const CString& message)
{
    if (!IsConnected()) return FALSE;
    return SendLineUtf8(message);
}

void ChatClient::SendLoginInfo()
{
    CString loginLine;
    loginLine.Format(L"LOGIN %s %s", m_empNo.GetString(), m_password.GetString());
    SendLineUtf8(loginLine);
}

BOOL ChatClient::SendLineUtf8(const CString& line)
{
    CString withNl = line + L"\n";
    CT2A a(withNl, CP_UTF8);
    const char* p = a.m_psz;
    int total = (int)strlen(p);
    int sent = 0;

    while (sent < total) {
        int n = send(m_socket, p + sent, total - sent, 0);
        if (n <= 0) {
            Disconnect(); // 전송 실패 시 연결 끊김 처리
            ::PostMessage(m_hNotifyWnd, WM_USER_CONNECTION_STATUS, (WPARAM)FALSE, 0);
            return FALSE;
        }
        sent += n;
    }
    return TRUE;
}

UINT ChatClient::ReceiveThread(LPVOID pParam)
{
    ChatClient* pThis = (ChatClient*)pParam;
    char buffer[2048];

    while (true)
    {
        int recvLen = recv(pThis->m_socket, buffer, sizeof(buffer), 0);
        if (recvLen <= 0) {
            // 연결 종료
            break;
        }

        // UTF-8 -> CString 변환
        int nLen = MultiByteToWideChar(CP_UTF8, 0, buffer, recvLen, NULL, 0);
        wchar_t* pUnicode = new wchar_t[nLen + 1];
        MultiByteToWideChar(CP_UTF8, 0, buffer, recvLen, pUnicode, nLen);
        pUnicode[nLen] = L'\0';

        // CString 객체로 변환 후 동적 할당하여 PostMessage로 전달
        CString* pStr = new CString(pUnicode);
        delete[] pUnicode;

        // ===== ?? 중복 로그인 감지 처리 =====
        if (pStr->Find(L"DUPLICATE_LOGIN") >= 0) {
            // 중복 로그인 메시지를 UI에 전달
            ::PostMessage(pThis->m_hNotifyWnd, WM_USER_CHAT_MESSAGE, (WPARAM)pStr, 0);

            // 연결 상태를 FALSE로 변경
            pThis->m_bIsConnected = FALSE;
            pThis->m_socket = INVALID_SOCKET;

            // 연결 상태 변경 알림
            ::PostMessage(pThis->m_hNotifyWnd, WM_USER_CONNECTION_STATUS, (WPARAM)FALSE, 0);

            // 스레드 종료
            break;
        }

        // 로그인 성공/실패 상태 업데이트
        if (pStr->Find(L"[ SERVER ] : 로그인 성공") >= 0) {
            pThis->m_bLoginSuccess = TRUE;
        }
        if (pStr->Find(L"[ SERVER ] : 로그인 실패") >= 0) {
            pThis->m_bLoginSuccess = FALSE;
        }

        // View로 UI 업데이트 메시지 전달
        ::PostMessage(pThis->m_hNotifyWnd, WM_USER_CHAT_MESSAGE, (WPARAM)pStr, 0);
    }

    // 연결 종료 = 접속 해제
    pThis->m_bIsConnected = FALSE;
    pThis->m_socket = INVALID_SOCKET;
    ::PostMessage(pThis->m_hNotifyWnd, WM_USER_CONNECTION_STATUS, (WPARAM)FALSE, 0);

    return 0;
}