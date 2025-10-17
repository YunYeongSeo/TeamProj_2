#include "pch.h"
#include "dbConnect.h"
#include <vector>
#include <string>
#include <winhttp.h>

#pragma comment(lib, "winhttp.lib")

dbConnect::dbConnect()
    : m_host(L"IP"), m_port(5000), m_basePath(L"/")
{
}

dbConnect::~dbConnect()
{
}

// 아주 단순한 JSON 키 값 추출: "key":"value" 형태를 찾아 value 반환.
// (작은 응답에 한해 사용, 복잡한 JSON이면 json 라이브러리 사용 권장)
static CString ExtractJsonStringValue(const CString& json, const wchar_t* key)
{
    CString pattern;
    pattern.Format(L"\"%s\"", key); // "key"
    int pos = json.Find(pattern);
    if (pos == -1) return CString();

    int colon = json.Find(L':', pos + pattern.GetLength());
    if (colon == -1) return CString();

    int firstQuote = json.Find(L'\"', colon);
    if (firstQuote == -1) return CString();

    int secondQuote = json.Find(L'\"', firstQuote + 1);
    if (secondQuote == -1) return CString();

    return json.Mid(firstQuote + 1, secondQuote - firstQuote - 1);
}

static std::string ToUtf8(const CString& s)
{
    if (s.IsEmpty()) return std::string();
    // WideCharToMultiByte로 필요한 바이트 수(널 포함) 얻기
    int n = ::WideCharToMultiByte(CP_UTF8, 0, (LPCTSTR)s, -1, nullptr, 0, nullptr, nullptr);
    if (n <= 0) return std::string();
    std::string out;
    out.resize(n - 1); // 널문자 제외
    ::WideCharToMultiByte(CP_UTF8, 0, (LPCTSTR)s, -1, &out[0], n, nullptr, nullptr);
    return out;
}

static CString FromUtf8(const std::string& s)
{
    if (s.empty()) return CString();
    // MultiByteToWideChar로 필요한 WCHAR 수(널 포함) 얻기
    int n = ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, nullptr, 0);
    if (n <= 0) return CString();
    CString out;
    out.GetBufferSetLength(n - 1); // 널문자 제외
    ::MultiByteToWideChar(CP_UTF8, 0, s.c_str(), -1, out.GetBuffer(), n);
    out.ReleaseBuffer();
    return out;
}

static bool WinHttpRequest(
    const CString& host, INTERNET_PORT port,
    const CString& verb, const CString& path,
    const std::string* requestBody, // nullptr이면 바디 없음
    std::string& responseBody, DWORD& statusCode)
{
    BOOL  bResults = FALSE;
    HINTERNET hSession = nullptr, hConnect = nullptr, hRequest = nullptr;
    statusCode = 0;
    responseBody.clear();

    hSession = WinHttpOpen(L"MonitoringProgram/1.0",
                          WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                          WINHTTP_NO_PROXY_NAME,
                          WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) goto cleanup;

    hConnect = WinHttpConnect(hSession, host, port, 0);
    if (!hConnect) goto cleanup;

    // WinHttpOpenRequest의 path은 LPCWSTR
    hRequest = WinHttpOpenRequest(hConnect,
                                  (LPCWSTR)verb,
                                  (LPCWSTR)path,
                                  nullptr,
                                  WINHTTP_NO_REFERER,
                                  WINHTTP_DEFAULT_ACCEPT_TYPES,
                                  0);
    if (!hRequest) goto cleanup;

    BOOL hasBody = (requestBody != nullptr && !requestBody->empty());
    LPCWSTR headers = hasBody ? L"Content-Type: application/json" : WINHTTP_NO_ADDITIONAL_HEADERS;
    DWORD headersLen = hasBody ? (DWORD)wcslen(headers) : 0;
    DWORD bodyLen = hasBody ? (DWORD)requestBody->size() : 0;

    bResults = WinHttpSendRequest(hRequest,
                                  headers,
                                  headersLen,
                                  (LPVOID)(hasBody ? requestBody->data() : nullptr),
                                  bodyLen,
                                  bodyLen,
                                  0);
    if (!bResults) goto cleanup;

    bResults = WinHttpReceiveResponse(hRequest, nullptr);
    if (!bResults) goto cleanup;

    // 상태 코드 얻기
    DWORD dwSize = sizeof(DWORD);
    WinHttpQueryHeaders(hRequest, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
                        WINHTTP_HEADER_NAME_BY_INDEX, &statusCode, &dwSize, WINHTTP_NO_HEADER_INDEX);

    // 응답 읽기
    for (;;)
    {
        DWORD dwAvailable = 0;
        if (!WinHttpQueryDataAvailable(hRequest, &dwAvailable)) break;
        if (dwAvailable == 0) break;

        std::vector<char> buffer(dwAvailable + 1);
        DWORD dwRead = 0;
        if (!WinHttpReadData(hRequest, buffer.data(), dwAvailable, &dwRead)) break;
        buffer[dwRead] = 0;
        responseBody.append(buffer.data(), dwRead);
    }

cleanup:
    if (hRequest) WinHttpCloseHandle(hRequest);
    if (hConnect) WinHttpCloseHandle(hConnect);
    if (hSession) WinHttpCloseHandle(hSession);

    return bResults != FALSE;
}

BOOL dbConnect::ok()
{
    // /health 확인
    std::string resp;
    DWORD status = 0;
    CString path = m_basePath;
    if (path.Right(1) != L"/") path += L"/";
    path += L"health";

    BOOL success = WinHttpRequest(m_host, m_port, L"GET", path, nullptr, resp, status);
    if (!success) return FALSE;

    CString cresp = FromUtf8(resp);
    // 플라스크에서 단순 "OK" 반환한다고 가정
    if (status == 200 && cresp.Find(L"OK") != -1) return TRUE;
    return FALSE;
}

BOOL dbConnect::Login(const CString& id, const CString& pw, CString& outUsername)
{
    outUsername.Empty();

    // JSON 바디 생성
    CString body;
    body.Format(L"{\"id\":\"%s\",\"pw\":\"%s\"}", id, pw);
    std::string utf8Body = ToUtf8(body);

    std::string resp;
    DWORD status = 0;
    CString path = m_basePath;
    if (path.Right(1) != L"/") path += L"/";
    path += L"api/login";

    BOOL success = WinHttpRequest(m_host, m_port, L"POST", path, &utf8Body, resp, status);
    if (!success) return FALSE;

    CString cresp = FromUtf8(resp);

    // 단순 JSON 파싱: {"success":true,"username":"..."}
    if (cresp.Find(L"\"success\"") != -1 && cresp.Find(L"true") == -1) {
        // 서버는 요청을 처리했으나 로그인 실패
        return TRUE;
    }

    CString username = ExtractJsonStringValue(cresp, L"username");
    if (!username.IsEmpty()) {
        outUsername = username;
    }
    return TRUE;
}