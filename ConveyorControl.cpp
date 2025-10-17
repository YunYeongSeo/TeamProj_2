#include "pch.h"
#include "ConveyorControl.h"

#include <windows.h>
#include <winhttp.h>
#include <vector>
#include <string>
#include <cstdio>
#pragma comment(lib, "winhttp.lib")

// ---------- message box helper (no MFC dependency) ----------
static void MsgBoxA(const char* s, UINT type = MB_OK | MB_ICONINFORMATION) {
#ifdef _UNICODE
    wchar_t w[1024];
    if (!s) s = "";
    MultiByteToWideChar(CP_ACP, 0, s, -1, w, 1024);
    ::MessageBoxW(NULL, w, L"Conveyor", type);
#else
    ::MessageBoxA(NULL, s ? s : "", "Conveyor", type);
#endif
}

// ---------- runtime target ----------
static std::string g_host = CONVEYOR_SERVER_HOST;
static unsigned short g_port = (unsigned short)CONVEYOR_SERVER_PORT;

void Conveyor_SetServerA(const char* host, unsigned short port) {
    g_host = (host ? host : "");
    g_port = port;
}
void Conveyor_GetServerA(std::string& hostOut, unsigned short& portOut) {
    hostOut = g_host;
    portOut = g_port;
}

void Conveyor_DebugShowConfigA() {
    char buf[128];
    _snprintf_s(buf, _TRUNCATE, "Server: %s:%u", g_host.c_str(), (unsigned)g_port);
    MsgBoxA(buf);
}

// ---------- helpers ----------
static std::wstring WidenFromACP(const char* s) {
    if (!s) return std::wstring();
    int wlen = MultiByteToWideChar(CP_ACP, 0, s, -1, NULL, 0);
    std::wstring w;
    if (wlen > 1) {
        w.resize((size_t)wlen - 1);
        MultiByteToWideChar(CP_ACP, 0, s, -1, &w[0], wlen);
    }
    return w;
}

// NO_PROXY GET request. Body is optional.
static BOOL HttpGetNoProxyA(const char* host, INTERNET_PORT port, const char* path,
    DWORD timeoutMs, std::string* bodyOut /*=nullptr*/)
{
    std::wstring wAgent = WidenFromACP("MFC-Conveyor/1.0");
    std::wstring wHost = WidenFromACP(host);
    std::wstring wPath = WidenFromACP(path);

    HINTERNET hSession = WinHttpOpen(wAgent.c_str(),
        WINHTTP_ACCESS_TYPE_NO_PROXY,
        WINHTTP_NO_PROXY_NAME,
        WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) { MsgBoxA("WinHttpOpen failed"); return FALSE; }

    WinHttpSetTimeouts(hSession, timeoutMs, timeoutMs, timeoutMs, timeoutMs);

    HINTERNET hConnect = WinHttpConnect(hSession, wHost.c_str(), port, 0);
    if (!hConnect) {
        MsgBoxA("WinHttpConnect failed");
        WinHttpCloseHandle(hSession);
        return FALSE;
    }

    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"GET", wPath.c_str(),
        NULL, WINHTTP_NO_REFERER,
        WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
    if (!hRequest) {
        MsgBoxA("WinHttpOpenRequest failed");
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return FALSE;
    }

    BOOL ok = WinHttpSendRequest(hRequest,
        WINHTTP_NO_ADDITIONAL_HEADERS, 0,
        NULL, 0, 0, 0);
    if (!ok) {
        DWORD e = GetLastError();
        LPSTR msg = NULL;
        FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL, e, 0, (LPSTR)&msg, 0, NULL);
        MsgBoxA(msg ? msg : "SendRequest failed", MB_OK | MB_ICONERROR);
        if (msg) LocalFree(msg);
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return FALSE;
    }

    ok = WinHttpReceiveResponse(hRequest, NULL);
    if (!ok) {
        DWORD e = GetLastError();
        LPSTR msg = NULL;
        FormatMessageA(FORMAT_MESSAGE_ALLOCATE_BUFFER | FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS,
            NULL, e, 0, (LPSTR)&msg, 0, NULL);
        MsgBoxA(msg ? msg : "ReceiveResponse failed", MB_OK | MB_ICONERROR);
        if (msg) LocalFree(msg);
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return FALSE;
    }

    DWORD status = 0, len = sizeof(status);
    WinHttpQueryHeaders(hRequest,
        WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
        WINHTTP_HEADER_NAME_BY_INDEX, &status, &len, WINHTTP_NO_HEADER_INDEX);

    std::string body;
    for (;;) {
        DWORD avail = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &avail) || avail == 0) break;
        std::vector<char> buf; buf.resize(avail);
        DWORD rd = 0;
        if (!WinHttpReadData(hRequest, buf.data(), avail, &rd) || rd == 0) break;
        body.append(buf.data(), rd);
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);

    if (bodyOut) *bodyOut = body;

    if (status != 200) {
        char tmp[64]; _snprintf_s(tmp, _TRUNCATE, "HTTP %lu", status);
        std::string msg = std::string(tmp) + "\n";
        msg += (body.size() > 512 ? body.substr(0, 512) : body);
        MsgBoxA(msg.c_str(), MB_OK | MB_ICONERROR);
        return FALSE;
    }
    return TRUE;
}

// ---------- public API (explicit host/port) ----------
BOOL Conveyor_HealthA(const char* host, unsigned short port) {
    std::string body;
    BOOL ok = HttpGetNoProxyA(host, port, "/health", 2000, &body);
    if (ok) {
        std::string msg = "Flask OK: " + body;
        MsgBoxA(msg.c_str());
    }
    return ok;
}

BOOL Conveyor_StartA(const char* host, unsigned short port, const char* dir) {
    (void)dir; // current Flask ignores dir
    return HttpGetNoProxyA(host, port, "/api/conveyor/start", 4000, nullptr);
}

BOOL Conveyor_StopA(const char* host, unsigned short port) {
    return HttpGetNoProxyA(host, port, "/api/conveyor/stop", 4000, nullptr);
}

BOOL Conveyor_PulseMSA(const char* host, unsigned short port, int ms, const char* dir) {
    char path[256];
    _snprintf_s(path, _TRUNCATE, "/api/conveyor/pulse?ms=%d&dir=%s", ms, (dir ? dir : "forward"));
    return HttpGetNoProxyA(host, port, path, 5000, nullptr);
}

// Optional cycle endpoints (only if implemented on server)
BOOL Conveyor_CycleStartA(const char* host, unsigned short port, int run_ms, int stop_ms, const char* dir) {
    char path[256];
    _snprintf_s(path, _TRUNCATE, "/api/conveyor/cycle/start?run_ms=%d&stop_ms=%d&dir=%s",
        run_ms, stop_ms, (dir ? dir : "forward"));
    return HttpGetNoProxyA(host, port, path, 5000, nullptr);
}
BOOL Conveyor_CycleStopA(const char* host, unsigned short port) {
    return HttpGetNoProxyA(host, port, "/api/conveyor/cycle/stop", 4000, nullptr);
}

// ---------- convenience wrappers using global server ----------
BOOL Conveyor_Health() { return Conveyor_HealthA(g_host.c_str(), g_port); }
BOOL Conveyor_Start(const char* dir) { return Conveyor_StartA(g_host.c_str(), g_port, dir); }
BOOL Conveyor_Stop() { return Conveyor_StopA(g_host.c_str(), g_port); }
BOOL Conveyor_PulseMS(int ms, const char* dir) { return Conveyor_PulseMSA(g_host.c_str(), g_port, ms, dir); }
BOOL Conveyor_CycleStart(int run_ms, int stop_ms, const char* dir) {
    return Conveyor_CycleStartA(g_host.c_str(), g_port, run_ms, stop_ms, dir);
}
BOOL Conveyor_CycleStop() { return Conveyor_CycleStopA(g_host.c_str(), g_port); }

// End of ConveyorControl.cpp
