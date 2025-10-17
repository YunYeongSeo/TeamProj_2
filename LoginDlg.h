#pragma once
#include "afxwin.h"
#include "resource.h"
#include "dbConnect.h"
#include "pch.h"

#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")

class CLoginDlg : public CDialogEx
{
public:
    CLoginDlg() : CDialogEx(IDD_LOGIN) {}

    // 로그인 성공 시 외부로 내보낼 값
    CString m_id;
    CString m_pw;

protected:
    virtual void DoDataExchange(CDataExchange* pDX) override { CDialogEx::DoDataExchange(pDX); }
    virtual BOOL OnInitDialog() override;
    virtual void OnOK() override;          // <- 여기서 서버 검증 수행
    virtual void OnCancel() override;

    afx_msg void OnClickedOkButton();
    afx_msg void OnClickedCancleButton();

    DECLARE_MESSAGE_MAP()

private:
    // TCP로 서버에 즉시 로그인 검증
    //bool VerifyWithTcp(const CString& emp, const CString& pw);
    bool VerifyWithTcp(const CString& emp, const CString& pw, CString& role);

    // 접속 대상 (필요 시 바꿔도 됨)
    CString m_serverIp = IP;
    int     m_serverPort = 5000;

    dbConnect db_Connect; // (사용 안 해도 무방)
};
