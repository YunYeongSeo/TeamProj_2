# 비밀번호 해쉬화 코드
import bcrypt, unicodedata

# pw = unicodedata.normalize("NFC", "배기현")   # 정규화(권장)
# hash_ = bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt(12)).decode()
# print(hash_)

# pw_2 = unicodedata.normalize("NFC", "윤영서")   # 정규화(권장)
# hash2_ = bcrypt.hashpw(pw_2.encode("utf-8"), bcrypt.gensalt(12)).decode()
# print(hash2_)

# pw_3 = unicodedata.normalize("NFC", "박준혁")   # 정규화(권장)
# hash3_ = bcrypt.hashpw(pw_3.encode("utf-8"), bcrypt.gensalt(12)).decode()
# print(hash3_)

# pw_4 = unicodedata.normalize("NFC", "소현섭")   # 정규화(권장)
# hash4_ = bcrypt.hashpw(pw_4.encode("utf-8"), bcrypt.gensalt(12)).decode()
# print(hash4_)

# pw_5 = unicodedata.normalize("NFC", "가대교")   # 정규화(권장)
# hash5_ = bcrypt.hashpw(pw_5.encode("utf-8"), bcrypt.gensalt(12)).decode()
# print(hash5_)

# 해쉬데이터(비밀번호) 확인
import bcrypt
hash_from_db = r"$2b$12$FKsFY6Ahe54kmU0o2X9OtOJuFCRU4nsqeA5I99wjjfUMOkjNObONa"   # 위 SELECT 결과 그대로 복붙
print(bcrypt.checkpw("배기현".encode("utf-8"),
                     hash_from_db.encode("utf-8")))

import bcrypt
hash_from_db = r"$2b$12$xZILD7GMevBSByYQLEU7.u906fRAUiikLkXw7TS71thgSFJlbbqny"   # 위 SELECT 결과 그대로 복붙
print(bcrypt.checkpw("윤영서".encode("utf-8"),
                     hash_from_db.encode("utf-8")))


import bcrypt
hash_from_db = r"$2b$12$hR8eLXRaBm6e2onb21gTDuMNW5eizL2.oR0xl2svp16/chfa0VrP2"   # 위 SELECT 결과 그대로 복붙
print(bcrypt.checkpw("박준혁".encode("utf-8"),
                     hash_from_db.encode("utf-8")))

import bcrypt
hash_from_db = r"$2b$12$6GkqLpO66AAPukwcpVJ.eOYzm08tqw5PEg9od3s4ElZyLbRW16Z9S"   # 위 SELECT 결과 그대로 복붙
print(bcrypt.checkpw("소현섭".encode("utf-8"),
                     hash_from_db.encode("utf-8")))

import bcrypt
hash_from_db = r"$2b$12$DYUsnP6z68JfQ8Cful1SmeJhSmgNFWYXgAXAEfwxSJrHx2XwSzD/O"   # 위 SELECT 결과 그대로 복붙
print(bcrypt.checkpw("가대교".encode("utf-8"),
                     hash_from_db.encode("utf-8")))