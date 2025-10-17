#pragma once

#include <afx.h>
#include <winhttp.h>

class dbConnect {
public:
    dbConnect();
    ~dbConnect();

    // 서버가 살아있는지 확인 (플라스크 /health 호출)
    BOOL ok();

    // 로그인: id/pw로 서버에 POST하고 반환 사용자명을 outUsername에 채움.
    // 반환값은 서버 호출 성공 여부(네트워크/서버 오류면 FALSE).
    BOOL Login(const CString& id, const CString& pw, CString& outUsername);

private:
    CString m_host;
    INTERNET_PORT m_port;
    CString m_basePath;
};