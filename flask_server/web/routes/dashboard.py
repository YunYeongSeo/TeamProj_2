"""
대시보드 메인 페이지 라우트 (로그인 없이, 환경 데이터 포함)
"""
from flask import redirect
from web.flask_app import app

@app.route("/")
def index():
    """메인 페이지 → 대시보드로 바로 이동"""
    return redirect("/dashboard")


@app.route("/dashboard")
def unified_dashboard():
    """🎯 통합 대시보드 (환경 데이터 포함)"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bamgohsi 통합 대시보드</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', 'Malgun Gothic', Arial, sans-serif; background: #f5f5f5; overflow: hidden; }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 18px 30px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
                display: flex;
                justify-content: space-between;
                align-items: center;
                position: sticky;
                top: 0;
                z-index: 1000;
            }
            .header h1 { font-size: 22px; font-weight: 600; }
            .header-info { display: flex; gap: 15px; align-items: center; }
            .header-badge { background: rgba(255,255,255,0.2); padding: 6px 14px; border-radius: 20px; font-size: 13px; }
            
            .container { display: flex; height: calc(100vh - 70px); }
            
            .sidebar {
                width: 240px;
                background: #2c3e50;
                color: white;
                padding: 15px 0;
                overflow-y: auto;
                box-shadow: 2px 0 10px rgba(0,0,0,0.1);
            }
            .sidebar::-webkit-scrollbar { width: 6px; }
            .sidebar::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.3); border-radius: 3px; }
            
            .menu-section { margin: 15px 0; }
            .menu-section-title { padding: 10px 20px; font-size: 11px; color: #95a5a6; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }
            
            .menu-item {
                padding: 12px 20px;
                cursor: pointer;
                transition: all 0.2s;
                display: flex;
                align-items: center;
                gap: 12px;
                font-size: 14px;
                border-left: 3px solid transparent;
                user-select: none;
            }
            .menu-item:hover {
                background: rgba(255,255,255,0.08);
                border-left-color: #3498db;
            }
            .menu-item.active {
                background: rgba(52, 152, 219, 0.25);
                border-left-color: #3498db;
                font-weight: 600;
            }
            .menu-icon { font-size: 18px; width: 22px; text-align: center; }
            
            .content {
                flex: 1;
                overflow-y: auto;
                background: #ecf0f1;
            }
            .content::-webkit-scrollbar { width: 8px; }
            .content::-webkit-scrollbar-thumb { background: #bdc3c7; border-radius: 4px; }
            
            .content-page {
                display: none;
                height: 100%;
            }
            .content-page.active {
                display: block;
                animation: fadeIn 0.3s;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            .iframe-container {
                width: 100%;
                height: 100%;
                background: white;
            }
            .iframe-container iframe {
                width: 100%;
                height: 100%;
                border: none;
            }
            
            .welcome {
                text-align: center;
                padding: 80px 20px;
                max-width: 1100px;
                margin: 0 auto;
            }
            .welcome h2 { font-size: 42px; margin-bottom: 15px; color: #2c3e50; }
            .welcome p { font-size: 18px; color: #7f8c8d; margin-bottom: 50px; }
            .welcome-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 25px;
            }
            .welcome-card {
                background: white;
                padding: 35px 20px;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                cursor: pointer;
                transition: all 0.3s;
            }
            .welcome-card:hover {
                transform: translateY(-8px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.15);
            }
            .welcome-card-icon { font-size: 48px; margin-bottom: 15px; }
            .welcome-card-title { font-size: 16px; font-weight: 600; color: #2c3e50; }
            .welcome-card-desc { font-size: 13px; color: #95a5a6; margin-top: 8px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 Bamgohsi 통합 대시보드</h1>
            <div class="header-info">
                <div class="header-badge">⚖️ Balance 모드</div>
                <div class="header-badge" id="currentTime">--:--:--</div>
            </div>
        </div>
        
        <div class="container">
            <div class="sidebar">
                <div class="menu-section">
                    <div class="menu-section-title">메인</div>
                    <div class="menu-item active" onclick="showPage('welcome')">
                        <span class="menu-icon">🏠</span>
                        <span>홈</span>
                    </div>
                </div>
                
                <div class="menu-section">
                    <div class="menu-section-title">바코드 시스템</div>
                    <div class="menu-item" onclick="showPage('barcode')">
                        <span class="menu-icon">⚖️</span>
                        <span>바코드 검출</span>
                    </div>
                    <div class="menu-item" onclick="showPage('gallery')">
                        <span class="menu-icon">📸</span>
                        <span>검출 갤러리</span>
                    </div>
                    <div class="menu-item" onclick="showPage('analytics')">
                        <span class="menu-icon">📊</span>
                        <span>검출 분석</span>
                    </div>
                </div>
                
                <div class="menu-section">
                    <div class="menu-section-title">모니터링</div>
                    <div class="menu-item" onclick="showPage('video')">
                        <span class="menu-icon">📹</span>
                        <span>실시간 영상</span>
                    </div>
                    <div class="menu-item" onclick="showPage('environment')">
                        <span class="menu-icon">🌡️</span>
                        <span>온도 습도</span>
                    </div>
                    <div class="menu-item" onclick="showPage('stats')">
                        <span class="menu-icon">📈</span>
                        <span>시스템 통계</span>
                    </div>
                </div>
                
                <div class="menu-section">
                    <div class="menu-section-title">관리</div>
                    <div class="menu-item" onclick="showPage('login')">
                        <span class="menu-icon">👤</span>
                        <span>로그인 이력</span>
                    </div>
                </div>
            </div>
            
            <div class="content">
                <div id="page-welcome" class="content-page active">
                    <div class="welcome">
                        <h2>🎉 환영합니다!</h2>
                        <p>Bamgohsi Balance 바코드 검출 시스템 통합 대시보드</p>
                        <div class="welcome-grid">
                            <div class="welcome-card" onclick="showPage('barcode')">
                                <div class="welcome-card-icon">⚖️</div>
                                <div class="welcome-card-title">바코드 검출</div>
                                <div class="welcome-card-desc">실시간 바코드 검출 현황</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('gallery')">
                                <div class="welcome-card-icon">📸</div>
                                <div class="welcome-card-title">검출 갤러리</div>
                                <div class="welcome-card-desc">검출된 이미지 보기</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('analytics')">
                                <div class="welcome-card-icon">📊</div>
                                <div class="welcome-card-title">검출 분석</div>
                                <div class="welcome-card-desc">통계 및 그래프</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('video')">
                                <div class="welcome-card-icon">📹</div>
                                <div class="welcome-card-title">실시간 영상</div>
                                <div class="welcome-card-desc">라이브 비디오 스트리밍</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('environment')">
                                <div class="welcome-card-icon">🌡️</div>
                                <div class="welcome-card-title">온도 습도</div>
                                <div class="welcome-card-desc">DHT11 센서 데이터</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('stats')">
                                <div class="welcome-card-icon">📈</div>
                                <div class="welcome-card-title">시스템 통계</div>
                                <div class="welcome-card-desc">서버 및 세션 정보</div>
                            </div>
                            <div class="welcome-card" onclick="showPage('login')">
                                <div class="welcome-card-icon">👤</div>
                                <div class="welcome-card-title">로그인 이력</div>
                                <div class="welcome-card-desc">사용자 접속 기록</div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div id="page-barcode" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-barcode" data-src="/_internal/barcode_dashboard"></iframe>
                    </div>
                </div>
                
                <div id="page-gallery" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-gallery" data-src="/_internal/barcode_gallery"></iframe>
                    </div>
                </div>
                
                <div id="page-analytics" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-analytics" data-src="/_internal/barcode_analytics"></iframe>
                    </div>
                </div>
                
                <div id="page-login" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-login" data-src="/_internal/login_history"></iframe>
                    </div>
                </div>
                
                <div id="page-video" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-video" data-src="/_internal/video_feed_page"></iframe>
                    </div>
                </div>
                
                <div id="page-environment" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-environment" data-src="/_internal/environment"></iframe>
                    </div>
                </div>
                
                <div id="page-stats" class="content-page">
                    <div class="iframe-container">
                        <iframe id="iframe-stats" data-src="/_internal/stats_page"></iframe>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            function updateTime() {
                const now = new Date();
                document.getElementById('currentTime').textContent = now.toLocaleTimeString('ko-KR');
            }
            updateTime();
            setInterval(updateTime, 1000);
            
            function showPage(pageName) {
                document.querySelectorAll('.menu-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                event.currentTarget.classList.add('active');
                
                document.querySelectorAll('.content-page').forEach(page => {
                    page.classList.remove('active');
                });
                
                const targetPage = document.getElementById('page-' + pageName);
                targetPage.classList.add('active');
                
                const iframe = targetPage.querySelector('iframe');
                if (iframe && !iframe.src && iframe.dataset.src) {
                    iframe.src = iframe.dataset.src;
                }
            }
        </script>
    </body>
    </html>
    """