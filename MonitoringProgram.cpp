// MonitoringProgram.cpp : 애플리케이션 클래스 동작 정의

#include "pch.h"
#include "framework.h"
#include "afxwinappex.h"
#include "afxdialogex.h"

#include "MonitoringProgram.h"
#include "MainFrm.h"
#include "MonitoringProgramDoc.h"
#include "MonitoringProgramView.h"
#include "LoginDlg.h"
#include "resource.h"

#ifdef _DEBUG
#define new DEBUG_NEW
#endif

// CMonitoringProgramApp

BEGIN_MESSAGE_MAP(CMonitoringProgramApp, CWinApp)
    ON_COMMAND(ID_APP_ABOUT, &CMonitoringProgramApp::OnAppAbout)
    ON_COMMAND(ID_FILE_NEW, &CWinApp::OnFileNew)
    ON_COMMAND(ID_FILE_OPEN, &CWinApp::OnFileOpen)
END_MESSAGE_MAP()

// CMonitoringProgramApp 생성

CMonitoringProgramApp::CMonitoringProgramApp() noexcept
{
    // 애플리케이션 ID 문자열
    SetAppID(_T("MonitoringProgram.AppID.NoVersion"));
}

// 유일한 CMonitoringProgramApp 객체
CMonitoringProgramApp theApp;

// CMonitoringProgramApp 초기화

BOOL CMonitoringProgramApp::InitInstance()
{
    CWinApp::InitInstance();

    // ── 1) 로그인 다이얼로그 ──────────────────────────────────────────────
    CLoginDlg login;
    INT_PTR lr = login.DoModal();
    if (lr != IDOK) {
        // 로그인 취소/실패 시 앱 종료
        return FALSE;
    }

    // OK로 닫혔으면 입력값 보관 (View에서 사용)
    m_empNo = login.m_id;   // ex) "EMP001"
    m_password = login.m_pw;   // ex) "Passw0rd!"
    
    // ── 2) 소켓 초기화 (TCP 클라이언트 사용) ─────────────────────────────
    if (!AfxSocketInit()) {
        AfxMessageBox(IDP_SOCKETS_INIT_FAILED);
        return FALSE;
    }

    EnableTaskbarInteraction(FALSE);
    SetRegistryKey(_T("로컬 애플리케이션 마법사에서 생성된 애플리케이션"));
    LoadStdProfileSettings(4);  // MRU 포함 표준 INI 옵션

    // ── 3) SDI 문서/뷰/프레임 템플릿 등록 ────────────────────────────────
    CSingleDocTemplate* pDocTemplate = new CSingleDocTemplate(
        IDR_MAINFRAME,
        RUNTIME_CLASS(CMonitoringProgramDoc),
        RUNTIME_CLASS(CMainFrame),                 // 주 SDI 프레임
        RUNTIME_CLASS(CMonitoringProgramView));
    if (!pDocTemplate) return FALSE;
    AddDocTemplate(pDocTemplate);

    // ── 4) 명령줄 파싱 및 실행 ───────────────────────────────────────────
    CCommandLineInfo cmdInfo;
    ParseCommandLine(cmdInfo);
    if (!ProcessShellCommand(cmdInfo)) return FALSE;

    // ── 5) 메인 윈도우 표시 ──────────────────────────────────────────────
    m_pMainWnd->ShowWindow(SW_SHOW);
    m_pMainWnd->UpdateWindow();
    return TRUE;
}

// 응용 프로그램 정보에 사용되는 CAboutDlg

class CAboutDlg : public CDialogEx
{
public:
    CAboutDlg() noexcept;

#ifdef AFX_DESIGN_TIME
    enum { IDD = IDD_ABOUTBOX };
#endif

protected:
    virtual void DoDataExchange(CDataExchange* pDX); // DDX/DDV

protected:
    DECLARE_MESSAGE_MAP()
};

CAboutDlg::CAboutDlg() noexcept : CDialogEx(IDD_ABOUTBOX) {}
void CAboutDlg::DoDataExchange(CDataExchange* pDX) { CDialogEx::DoDataExchange(pDX); }

BEGIN_MESSAGE_MAP(CAboutDlg, CDialogEx)
END_MESSAGE_MAP()

void CMonitoringProgramApp::OnAppAbout()
{
    CAboutDlg aboutDlg;
    aboutDlg.DoModal();
}
