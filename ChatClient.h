#pragma once

#include <afxwin.h>
#include <WinSock2.h>
#include <WS2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

// ChatClient가 View에게 보낼 사용자 메시지 정의
#define WM_USER_CHAT_MESSAGE    (WM_USER + 101) // 채팅 메시지 도착 (WPARAM: CString*)
#define WM_USER_CONNECTION_STATUS (WM_USER + 102) // 연결 상태 변경 (WPARAM: BOOL bConnected)

class ChatClient
{
public:
    ChatClient();
    ~ChatClient();

    // --- Public API ---
    BOOL Connect(HWND hNotifyWnd, const CString& ip, UINT port, const CString& empNo, const CString& password);
    void Disconnect();
    BOOL SendMessage(const CString& message);
    BOOL IsConnected() const { return m_bIsConnected; }

private:
    // --- Worker Thread ---
    static UINT ReceiveThread(LPVOID pParam);
    void SendLoginInfo();
    BOOL SendLineUtf8(const CString& line);

    // --- Member Variables ---
    HWND    m_hNotifyWnd;     // 알림을 받을 윈도우 핸들 (View의 m_hWnd)
    SOCKET  m_socket;
    BOOL    m_bIsConnected;
    BOOL    m_bLoginSuccess;

    CString m_ip;
    UINT    m_port;
    CString m_empNo;
    CString m_password;

    CWinThread* m_pReceiveThread;
};