"""
바코드 검증 및 신뢰도 계산 유틸리티
"""
import re
from config import BARCODE_PRODUCT_MAP


def validate_barcode_balanced(barcode_data):
    """🔍 Balance 바코드 패턴 검증 (정확하지만 너무 엄격하지 않게)"""
    try:
        # 1. 기본 길이 검증 (10~15자리 허용)
        if len(barcode_data) < 10 or len(barcode_data) > 15:
            return False, "길이_오류"
        
        # 2. 숫자만 포함 검증
        if not barcode_data.isdigit():
            return False, "숫자_오류"
        
        # 3. 등록된 Bamgohsi 제품 우선 허용
        if barcode_data in BARCODE_PRODUCT_MAP:
            return True, "등록_제품"
        
        # 4. 명백한 잘못된 패턴만 차단 (Balance)
        obvious_invalid_patterns = [
            r"^0{8,}",            # 00000000...
            r"^1{8,}",            # 11111111...
            r"^[0-2]{13}$",       # 000~222
            r"^9{8,}",            # 99999999...
        ]
        
        for pattern in obvious_invalid_patterns:
            if re.match(pattern, barcode_data):
                return False, "명백한_잘못된_패턴"
        
        # 5. 일반적인 바코드 패턴 허용 (Balance)
        if len(barcode_data) == 13:
            return True, "표준_13자리_바코드"
        
        if len(barcode_data) == 12:
            return True, "표준_12자리_바코드"
        
        return True, "일반_바코드"
        
    except Exception as e:
        return False, "검증_오류"


def calculate_barcode_confidence_balanced(barcode_obj):
    """🔍 Balance 바코드 신뢰도 계산 (완화된 기준)"""
    try:
        # 바코드 크기 점수
        rect = barcode_obj.rect
        area = rect.width * rect.height
        size_score = min(area / 3000, 1.0)
        
        # 바코드 품질 점수
        data_length = len(barcode_obj.data)
        length_score = 1.0 if data_length >= 10 else data_length / 10.0
        
        # 바코드 위치 점수
        center_x = rect.x + rect.width / 2
        center_y = rect.y + rect.height / 2
        center_score = 1.0 - (abs(center_x - 320) / 320 + abs(center_y - 240) / 240) / 2
        center_score = max(center_score, 0.3)
        
        # Balance 종합 신뢰도 계산
        confidence = (size_score * 0.3 + length_score * 0.4 + center_score * 0.3) * 100
        
        return min(confidence, 100.0)
        
    except Exception as e:
        return 70.0