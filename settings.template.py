# -*- coding: utf-8 -*-

# Flask 세션 만드는데 쓰는 키, 랜덤 스트링으로 충분함
APP_SECRET = "asdfasdfasdfasdf"

# 트위터 API 정보
TWITTER_API_KEY = "KEY"
TWITTER_API_SECRET = "SECRET"

# DB 접속 URL
# http://docs.peewee-orm.com/en/latest/peewee/database.html#connecting-using-a-database-url
DB_URL = "mysql://root:rosebud@localhost/tmdnlcl"

# 트위터 API 콜백 URL, 로그인때밖에 안씀
CALLBACK_URL = "http://tmdnlcl.iamghost.kr"

# 해시태그
HASH_TAG = "#NintendoSwitch"

# 검색모드(timeline, search)
API_MODE = 'timeline'

# 한바퀴 돌고나서 딜레이, 사용자 수가 적은데 너무 빨리 돌면 Limit에 걸릴 수 있음
BATCH_INTERVAL = 5
