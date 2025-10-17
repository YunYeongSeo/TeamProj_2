"""
내부용 페이지 라우트 (대시보드 iframe용)
"""
from web.flask_app import app

@app.route("/_internal/barcode_dashboard")
def internal_barcode_dashboard():
    """🔒 내부용: Balance 바코드 검출 대시보드"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Balance Barcode Detection</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="3">
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stats { display: flex; justify-content: space-around; flex-wrap: wrap; }
            .stat-item { text-align: center; padding: 15px; }
            .stat-number { font-size: 2em; font-weight: bold; color: #28a745; }
            .stat-label { color: #666; margin-top: 5px; font-size: 14px; }
            .product-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
            .product-item { padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #28a745; }
            .unregistered-item { border-left-color: #ffc107; background: #fff3cd; }
            .barcode-icon { font-size: 2em; margin-bottom: 10px; }
            .balance-header { background: linear-gradient(45deg, #28a745, #20c997); color: white; text-align: center; padding: 15px; border-radius: 8px; }
            .test-button { background: #28a745; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; margin: 10px 0; }
            .test-button:hover { background: #218838; }
            .test-result { background: #d4edda; padding: 10px; border-radius: 5px; margin: 10px 0; display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="balance-header">
                <div class="barcode-icon">⚖️</div>
                <h1>Balance Barcode Detection</h1>
                <p>실용적인 Balance 바코드 검출 시스템 (Bamgohsi 제품)</p>
            </div>
            
            <div class="card">
                <h3>🔥 Balance 테스트</h3>
                <button class="test-button" onclick="forceTest()">Balance 바코드 검출 실행</button>
                <div id="testResult" class="test-result"></div>
            </div>
            
            <div class="card">
                <h3>Balance 실시간 통계</h3>
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-number" id="recent10min">-</div>
                        <div class="stat-label">최근 10분 (Balance 검출)</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="recentRejected">-</div>
                        <div class="stat-label">최근 10분 (Balance 차단)</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-number" id="totalEvents">-</div>
                        <div class="stat-label">Balance 이벤트</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Balance 제품별 분포 (최근 10분)</h3>
                <div class="product-list" id="productDistribution"></div>
            </div>
        </div>
        
        <script>
            function forceTest() {
                document.getElementById('testResult').style.display = 'block';
                document.getElementById('testResult').innerHTML = '🔄 Balance 바코드 검출 실행 중...';
                
                fetch('/test_barcode_now', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('testResult').innerHTML = 
                                `✅ Balance 검출 성공: ${data.detections_count}개 바코드 검출`;
                        } else {
                            document.getElementById('testResult').innerHTML = 
                                `❌ Balance 검출 실패: ${data.error}`;
                        }
                    })
                    .catch(err => {
                        document.getElementById('testResult').innerHTML = 
                            `❌ 네트워크 오류: ${err}`;
                    });
            }
            
            function updateStats() {
                fetch('/barcode_stats')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('recent10min').textContent = data.recent_10min.total;
                        document.getElementById('recentRejected').textContent = data.recent_10min.rejected || 0;
                        document.getElementById('totalEvents').textContent = data.recent_10min.events;
                        
                        const productDiv = document.getElementById('productDistribution');
                        productDiv.innerHTML = '';
                        
                        if (Object.keys(data.recent_10min.product_distribution).length === 0) {
                            productDiv.innerHTML = '<div class="product-item"><strong>Balance 대기 중</strong><br>Bamgohsi 제품이나 다른 바코드를 보여주세요</div>';
                        } else {
                            Object.entries(data.recent_10min.product_distribution).forEach(([product, count]) => {
                                const item = document.createElement('div');
                                const isUnregistered = product.includes('미등록');
                                item.className = isUnregistered ? 'product-item unregistered-item' : 'product-item';
                                
                                let icon = '⚖️';
                                if (product.includes('스트로베리')) icon = '🍓';
                                else if (product.includes('피치')) icon = '🍑';
                                else if (product.includes('스피어민트')) icon = '🌿';
                                else if (product.includes('페퍼민트')) icon = '🍃';
                                else if (product.includes('꿀,레몬')) icon = '🍯';
                                else if (product.includes('배,비파')) icon = '🍐';
                                else if (isUnregistered) icon = '❓';
                                
                                item.innerHTML = `<div class="barcode-icon">${icon}</div><strong>${product}</strong><br>${count}개 검출`;
                                productDiv.appendChild(item);
                            });
                        }
                    })
                    .catch(err => {
                        console.error('Balance stats update error:', err);
                    });
            }
            
            updateStats();
            setInterval(updateStats, 3000);
        </script>
    </body>
    </html>
    """


@app.route("/_internal/barcode_gallery")
def internal_barcode_gallery():
    """🔒 내부용: 바코드 검출 이미지 갤러리"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>바코드 검출 갤러리</title>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .gallery { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .gallery-item { background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
            .gallery-item:hover { transform: translateY(-5px); box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
            .gallery-item img { width: 100%; height: 250px; object-fit: cover; cursor: pointer; display: block; }
            .gallery-item-info { padding: 15px; }
            .barcode-number { font-size: 1.2em; font-weight: bold; color: #28a745; }
            .product-name { color: #666; margin: 5px 0; }
            .confidence { color: #007bff; font-weight: bold; }
            .timestamp { color: #999; font-size: 0.9em; }
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.9); }
            .modal-content { margin: auto; display: block; max-width: 90%; max-height: 90%; margin-top: 50px; }
            .close { position: absolute; top: 20px; right: 40px; color: #f1f1f1; font-size: 40px; font-weight: bold; cursor: pointer; }
            .close:hover { color: #bbb; }
            .error-msg { color: red; text-align: center; padding: 20px; }
            .error-placeholder { padding: 15px; text-align: center; color: #999; background: #f8f9fa; height: 250px; display: flex; align-items: center; justify-content: center; flex-direction: column; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📸 바코드 검출 갤러리</h1>
            <p>검출된 바코드 이미지 및 정보</p>
        </div>
        
        <div class="gallery" id="gallery"></div>
        
        <div id="imageModal" class="modal" onclick="closeModal()">
            <span class="close">&times;</span>
            <img class="modal-content" id="modalImage">
        </div>
        
        <script>
            function loadGallery() {
                fetch('/api/barcode_detections_with_images?limit=100')
                    .then(response => response.json())
                    .then(data => {
                        const gallery = document.getElementById('gallery');
                        gallery.innerHTML = '';
                        
                        if (data.detections.length === 0) {
                            gallery.innerHTML = '<p class="error-msg">검출된 바코드가 없습니다</p>';
                            return;
                        }
                        
                        data.detections.forEach(item => {
                            const card = document.createElement('div');
                            card.className = 'gallery-item';
                            
                            const imgUrl = `/barcode_images/${item.image_filename}`;
                            const detectedTime = new Date(item.detected_at).toLocaleString('ko-KR');
                            
                            const img = document.createElement('img');
                            img.src = imgUrl;
                            img.alt = item.barcode;
                            img.style.cursor = 'pointer';
                            
                            img.onload = function() {
                                console.log('✅ 이미지 로드 성공:', item.image_filename);
                            };
                            
                            img.onerror = function() {
                                console.error('❌ 이미지 로드 실패:', item.image_filename);
                                this.style.display = 'none';
                                const errorDiv = document.createElement('div');
                                errorDiv.className = 'error-placeholder';
                                errorDiv.innerHTML = `
                                    <div>🖼️</div>
                                    <div>이미지 로드 실패</div>
                                    <div style="font-size:0.8em;margin-top:10px;">${item.image_filename}</div>
                                `;
                                this.parentElement.insertBefore(errorDiv, this);
                            };
                            
                            img.onclick = function() {
                                openModal(imgUrl);
                            };
                            
                            const info = document.createElement('div');
                            info.className = 'gallery-item-info';
                            info.innerHTML = `
                                <div class="barcode-number">${item.barcode}</div>
                                <div class="product-name">${item.product_name}</div>
                                <div class="confidence">신뢰도: ${item.confidence.toFixed(2)}%</div>
                                <div class="timestamp">${detectedTime}</div>
                            `;
                            
                            card.appendChild(img);
                            card.appendChild(info);
                            gallery.appendChild(card);
                        });
                    })
                    .catch(err => {
                        console.error('갤러리 로드 오류:', err);
                        document.getElementById('gallery').innerHTML = '<p class="error-msg">갤러리 로드 오류: ' + err + '</p>';
                    });
            }
            
            function openModal(imgUrl) {
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImage');
                modal.style.display = 'block';
                modalImg.src = imgUrl;
            }
            
            function closeModal() {
                document.getElementById('imageModal').style.display = 'none';
            }
            
            loadGallery();
            setInterval(loadGallery, 10000);
        </script>
    </body>
    </html>
    """


@app.route("/_internal/barcode_analytics")
def internal_barcode_analytics():
    """🔒 내부용: 바코드 분석 대시보드"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>바코드 분석</title>
        <meta charset="utf-8">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .charts-container { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; }
            .chart-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .chart-card h3 { margin-top: 0; color: #2c3e50; font-size: 18px; margin-bottom: 20px; }
            .stats-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }
            .stat-box { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #28a745; margin-bottom: 5px; }
            .stat-label { color: #666; font-size: 14px; }
            canvas { max-height: 300px; }
            .full-width { grid-column: 1 / -1; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📊 바코드 검출 분석 대시보드</h1>
            <p>실시간 통계 및 그래프</p>
        </div>
        
        <div class="stats-summary">
            <div class="stat-box">
                <div class="stat-number" id="totalDetections">0</div>
                <div class="stat-label">총 검출 (10분)</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="rejectedDetections">0</div>
                <div class="stat-label">거부된 검출</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="successRate">0%</div>
                <div class="stat-label">성공률</div>
            </div>
            <div class="stat-box">
                <div class="stat-number" id="uniqueProducts">0</div>
                <div class="stat-label">검출된 제품 종류</div>
            </div>
        </div>
        
        <div class="charts-container">
            <div class="chart-card">
                <h3>🏆 제품별 검출 순위 (최근 10분)</h3>
                <canvas id="productRankChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3>✅ 검출 성공률</h3>
                <canvas id="successRateChart"></canvas>
            </div>
            
            <div class="chart-card full-width">
                <h3>📈 시간대별 검출량 (최근 1시간)</h3>
                <canvas id="timelineChart"></canvas>
            </div>
        </div>
        
        <script>
            let productRankChart, successRateChart, timelineChart;
            let timelineData = {
                labels: [],
                datasets: [{
                    label: '검출 횟수',
                    data: [],
                    borderColor: 'rgba(40, 167, 69, 1)',
                    backgroundColor: 'rgba(40, 167, 69, 0.2)',
                    tension: 0.4,
                    fill: true
                }]
            };
            
            function initCharts() {
                const ctx1 = document.getElementById('productRankChart').getContext('2d');
                productRankChart = new Chart(ctx1, {
                    type: 'bar',
                    data: {
                        labels: [],
                        datasets: [{
                            label: '검출 횟수',
                            data: [],
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)',
                                'rgba(255, 159, 64, 0.7)'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 1 }
                            }
                        }
                    }
                });
                
                const ctx2 = document.getElementById('successRateChart').getContext('2d');
                successRateChart = new Chart(ctx2, {
                    type: 'doughnut',
                    data: {
                        labels: ['성공', '거부'],
                        datasets: [{
                            data: [0, 0],
                            backgroundColor: [
                                'rgba(40, 167, 69, 0.8)',
                                'rgba(220, 53, 69, 0.8)'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { position: 'bottom' }
                        }
                    }
                });
                
                const ctx3 = document.getElementById('timelineChart').getContext('2d');
                timelineChart = new Chart(ctx3, {
                    type: 'line',
                    data: timelineData,
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: true }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: { stepSize: 1 }
                            }
                        }
                    }
                });
            }
            
            function updateCharts() {
                fetch('/barcode_stats')
                    .then(response => response.json())
                    .then(data => {
                        const recent = data.recent_10min;
                        
                        document.getElementById('totalDetections').textContent = recent.total;
                        document.getElementById('rejectedDetections').textContent = recent.rejected || 0;
                        
                        const successRate = recent.total > 0 
                            ? Math.round((recent.total / (recent.total + (recent.rejected || 0))) * 100)
                            : 0;
                        document.getElementById('successRate').textContent = successRate + '%';
                        document.getElementById('uniqueProducts').textContent = Object.keys(recent.product_distribution).length;
                        
                        const products = Object.entries(recent.product_distribution)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 10);
                        
                        productRankChart.data.labels = products.map(p => p[0]);
                        productRankChart.data.datasets[0].data = products.map(p => p[1]);
                        productRankChart.update();
                        
                        successRateChart.data.datasets[0].data = [recent.total, recent.rejected || 0];
                        successRateChart.update();
                        
                        const now = new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
                        timelineData.labels.push(now);
                        timelineData.datasets[0].data.push(recent.total);
                        
                        if (timelineData.labels.length > 12) {
                            timelineData.labels.shift();
                            timelineData.datasets[0].data.shift();
                        }
                        
                        timelineChart.update();
                    })
                    .catch(err => {
                        console.error('통계 로드 오류:', err);
                    });
            }
            
            initCharts();
            updateCharts();
            setInterval(updateCharts, 5000);
        </script>
    </body>
    </html>
    """


@app.route("/_internal/login_history")
def internal_login_history():
    """🔒 내부용: 로그인 히스토리 대시보드"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>로그인 이력</title>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .card { background: white; padding: 20px; margin: 15px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #007bff; color: white; }
            tr:hover { background-color: #f5f5f5; }
            .success { color: #28a745; font-weight: bold; }
            .fail { color: #dc3545; font-weight: bold; }
            .stats { display: flex; justify-content: space-around; margin: 20px 0; flex-wrap: wrap; }
            .stat-item { text-align: center; padding: 20px; background: #f8f9fa; border-radius: 8px; }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #007bff; }
            .stat-label { color: #666; margin-top: 10px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>👤 로그인 이력 관리</h1>
            <p>사용자 로그인 기록 및 통계</p>
        </div>
        
        <div class="card">
            <h3>📈 로그인 통계 (최근 7일)</h3>
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-number" id="totalLogins">-</div>
                    <div class="stat-label">총 로그인</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="failedLogins">-</div>
                    <div class="stat-label">실패한 로그인</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="successRate">-</div>
                    <div class="stat-label">성공률 (%)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number" id="avgDuration">-</div>
                    <div class="stat-label">평균 세션 시간 (초)</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📋 로그인 이력 (최근 100건)</h3>
            <table id="historyTable">
                <thead>
                    <tr>
                        <th>사원번호</th>
                        <th>IP 주소</th>
                        <th>로그인 시각</th>
                        <th>로그아웃 시각</th>
                        <th>세션 시간</th>
                        <th>상태</th>
                        <th>실패 사유</th>
                    </tr>
                </thead>
                <tbody id="historyBody">
                    <tr><td colspan="7" style="text-align:center;">로딩 중...</td></tr>
                </tbody>
            </table>
        </div>
        
        <script>
            function formatDuration(seconds) {
                if (!seconds || seconds === 0) return '-';
                const hours = Math.floor(seconds / 3600);
                const minutes = Math.floor((seconds % 3600) / 60);
                const secs = seconds % 60;
                return `${hours}h ${minutes}m ${secs}s`;
            }
            
            function formatDateTime(isoString) {
                if (!isoString) return '-';
                const date = new Date(isoString);
                return date.toLocaleString('ko-KR');
            }
            
            function loadStatistics() {
                fetch('/api/login_statistics?days=7')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('totalLogins').textContent = data.total_logins;
                        document.getElementById('failedLogins').textContent = data.failed_logins;
                        document.getElementById('successRate').textContent = data.success_rate + '%';
                        document.getElementById('avgDuration').textContent = data.avg_session_duration;
                    })
                    .catch(err => console.error('통계 로드 오류:', err));
            }
            
            function loadHistory() {
                fetch('/api/login_history?limit=100')
                    .then(response => response.json())
                    .then(data => {
                        const tbody = document.getElementById('historyBody');
                        tbody.innerHTML = '';
                        
                        if (data.history.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">기록이 없습니다</td></tr>';
                            return;
                        }
                        
                        data.history.forEach(item => {
                            const row = document.createElement('tr');
                            const statusClass = item.login_status === 'SUCCESS' ? 'success' : 'fail';
                            row.innerHTML = `
                                <td>${item.emp_no}</td>
                                <td>${item.client_ip || '-'}</td>
                                <td>${formatDateTime(item.login_time)}</td>
                                <td>${formatDateTime(item.logout_time)}</td>
                                <td>${formatDuration(item.session_duration)}</td>
                                <td class="${statusClass}">${item.login_status}</td>
                                <td>${item.fail_reason || '-'}</td>
                            `;
                            tbody.appendChild(row);
                        });
                    })
                    .catch(err => {
                        console.error('이력 로드 오류:', err);
                        document.getElementById('historyBody').innerHTML = 
                            '<tr><td colspan="7" style="text-align:center;color:red;">로드 실패</td></tr>';
                    });
            }
            
            loadStatistics();
            loadHistory();
            setInterval(() => {
                loadStatistics();
                loadHistory();
            }, 30000);
        </script>
    </body>
    </html>
    """


@app.route("/_internal/stats_page")
def internal_stats_page():
    """🔒 내부용: 시스템 통계 페이지"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>시스템 통계</title>
        <meta charset="utf-8">
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h2 { color: #2c3e50; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
            .stat-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
            .stat-label { font-size: 14px; color: #7f8c8d; margin-bottom: 10px; }
            .stat-value { font-size: 32px; font-weight: bold; color: #2c3e50; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📈 시스템 통계</h2>
        </div>
        <div class="stats-grid" id="statsGrid"></div>
        
        <script>
            function loadStats() {
                fetch('/stats')
                    .then(response => response.json())
                    .then(data => {
                        const grid = document.getElementById('statsGrid');
                        grid.innerHTML = `
                            <div class="stat-card">
                                <div class="stat-label">활성 세션</div>
                                <div class="stat-value">${data.active_sessions}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">접속 중인 클라이언트</div>
                                <div class="stat-value">${data.connected_clients}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">최근 10분 바코드 검출</div>
                                <div class="stat-value">${data.recent_barcode_detections}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">거부된 바코드</div>
                                <div class="stat-value">${data.recent_barcode_rejections}</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">검출 간격</div>
                                <div class="stat-value">${data.detection_interval}초</div>
                            </div>
                            <div class="stat-card">
                                <div class="stat-label">신뢰도 임계값</div>
                                <div class="stat-value">${data.confidence_threshold}%</div>
                            </div>
                        `;
                    })
                    .catch(err => console.error('통계 로드 오류:', err));
            }
            
            loadStats();
            setInterval(loadStats, 5000);
        </script>
    </body>
    </html>
    """


@app.route("/_internal/video_feed_page")
def internal_video_feed_page():
    """🔒 내부용: 실시간 영상 페이지 (카메라 2개)"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>실시간 영상</title>
        <meta charset="utf-8">
        <style>
            body { 
                margin: 0; 
                padding: 20px; 
                background: #2c3e50; 
                font-family: 'Malgun Gothic', Arial, sans-serif;
            }
            .header {
                text-align: center;
                color: white;
                margin-bottom: 30px;
            }
            .header h2 { 
                font-size: 28px; 
                margin-bottom: 10px; 
            }
            .header p {
                color: #95a5a6;
                font-size: 14px;
            }
            .video-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
                gap: 20px;
                max-width: 1400px;
                margin: 0 auto;
            }
            .video-card {
                background: #34495e;
                border-radius: 12px;
                padding: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }
            .video-title {
                color: white;
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .video-icon {
                font-size: 24px;
            }
            .video-container {
                position: relative;
                width: 100%;
                padding-bottom: 75%; /* 4:3 비율 */
                background: #000;
                border-radius: 8px;
                overflow: hidden;
            }
            .video-container img {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                object-fit: contain;
            }
            .video-info {
                margin-top: 15px;
                padding: 10px;
                background: rgba(0,0,0,0.3);
                border-radius: 6px;
                color: #ecf0f1;
                font-size: 13px;
            }
            .info-item {
                display: flex;
                justify-content: space-between;
                padding: 5px 0;
                border-bottom: 1px solid rgba(255,255,255,0.1);
            }
            .info-item:last-child {
                border-bottom: none;
            }
            .info-label {
                color: #95a5a6;
            }
            .info-value {
                color: #2ecc71;
                font-weight: 600;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>📹 실시간 영상 모니터링</h2>
            <p>카메라 1 (바코드 검출) | 카메라 2 (모니터링)</p>
        </div>
        
        <div class="video-grid">
            <!-- 카메라 1 -->
            <div class="video-card">
                <div class="video-title">
                    <span class="video-icon">📹</span>
                    <span>카메라 1 (바코드 검출)</span>
                </div>
                <div class="video-container">
                    <img src="/video_feed_1" alt="카메라 1">
                </div>
                <div class="video-info">
                    <div class="info-item">
                        <span class="info-label">장치</span>
                        <span class="info-value">라즈베리파이 #1</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">IP</span>
                        <span class="info-value">192.168.0.87</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">용도</span>
                        <span class="info-value">바코드 검출 + 센서</span>
                    </div>
                </div>
            </div>
            
            <!-- 카메라 2 -->
            <div class="video-card">
                <div class="video-title">
                    <span class="video-icon">📹</span>
                    <span>카메라 2 (모니터링)</span>
                </div>
                <div class="video-container">
                    <img src="/video_feed_2" alt="카메라 2">
                </div>
                <div class="video-info">
                    <div class="info-item">
                        <span class="info-label">장치</span>
                        <span class="info-value">라즈베리파이 #2</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">IP</span>
                        <span class="info-value">192.168.0.26</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">용도</span>
                        <span class="info-value">라인 모니터링</span>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# internal.py - 환경 데이터 페이지 추가

@app.route("/_internal/environment")
def internal_environment():
    """🔒 내부용: 환경 데이터 대시보드"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>환경 데이터</title>
        <meta charset="utf-8">
        <meta http-equiv="refresh" content="5">
        <style>
            body { font-family: 'Malgun Gothic', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #2c3e50; }
            .env-card { background: white; padding: 40px; margin: 20px auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); max-width: 600px; }
            .env-item { display: flex; justify-content: space-between; align-items: center; padding: 20px; margin: 15px 0; background: #f8f9fa; border-radius: 8px; }
            .env-icon { font-size: 48px; }
            .env-label { font-size: 18px; color: #666; }
            .env-value { font-size: 36px; font-weight: bold; color: #28a745; }
            .env-unit { font-size: 20px; color: #999; margin-left: 5px; }
            .no-data { text-align: center; padding: 40px; color: #999; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🌡️ 환경 데이터</h1>
            <p>라즈베리파이 #2 DHT11 센서</p>
        </div>
        
        <div class="env-card" id="envData">
            <div class="no-data">데이터 로딩 중...</div>
        </div>
        
        <script>
            function loadEnvironment() {
                fetch('/api/environment')
                    .then(response => response.json())
                    .then(data => {
                        const container = document.getElementById('envData');
                        
                        if (data.success && data.data.temperature !== null) {
                            container.innerHTML = `
                                <div class="env-item">
                                    <div>
                                        <div class="env-icon">🌡️</div>
                                        <div class="env-label">온도</div>
                                    </div>
                                    <div>
                                        <span class="env-value">${data.data.temperature}</span>
                                        <span class="env-unit">°C</span>
                                    </div>
                                </div>
                                
                                <div class="env-item">
                                    <div>
                                        <div class="env-icon">💧</div>
                                        <div class="env-label">습도</div>
                                    </div>
                                    <div>
                                        <span class="env-value">${data.data.humidity}</span>
                                        <span class="env-unit">%</span>
                                    </div>
                                </div>
                                
                                <div style="text-align:center;margin-top:30px;color:#999;font-size:14px;">
                                    센서: ${data.data.sensor_id}<br>
                                    위치: ${data.data.location}<br>
                                    시간: ${data.data.timestamp}
                                </div>
                            `;
                        } else {
                            container.innerHTML = '<div class="no-data">환경 데이터가 없습니다</div>';
                        }
                    })
                    .catch(err => {
                        document.getElementById('envData').innerHTML = '<div class="no-data">데이터 로드 오류</div>';
                    });
            }
            
            loadEnvironment();
            setInterval(loadEnvironment, 5000);
        </script>
    </body>
    </html>
    """