BAMGOHSI_BARCODE_MAP = {
    "8804973304842": "스트로베리향",
    "8804973304835": "피치향",
    "8804973304828": "스피어민트향",
    "8804973304811": "페퍼민트향",
    "8804973308789": "꿀,레몬향",
    "8804973308802": "배,비파향"
}

def get_product_name(barcode):
    return BAMGOHSI_BARCODE_MAP.get(barcode, f"미등록제품({barcode})")