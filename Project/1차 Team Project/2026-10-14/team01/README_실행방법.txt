01의 기능과 화면을 유지한 정리본

[실행 방법 - PowerShell]
1. 압축을 풀고 team01 폴더를 엽니다. manage.py가 있는 폴더입니다.
2. 터미널에서 아래 명령을 순서대로 실행합니다.

python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

접속 주소: http://127.0.0.1:8000/
관리자 계정이 필요하면: python manage.py createsuperuser

[폴더 구성]
team01/ : settings.py, urls.py, wsgi.py, asgi.py - 프로젝트 설정
home/ : 메인 화면 앱, templates/index.html
brands/ : 브랜드 기능 앱, templates/에 브랜드 화면들
brands/templates/base.html : 여러 앱에서 사용하는 공통 화면 틀
brands/templates/includes/ : 공통 HTML 조각. 앱이 아니므로 INSTALLED_APPS 등록 불필요
static/ : images, css, js
docs/ : 01의 설계 문서와 CSV 예시(원본 보존, 옛 경로는 아래 새 경로 참고)
db.sqlite3 : 01의 기존 데이터베이스 유지

[수정 내용]
- 01의 backend 안 코드를 manage.py와 같은 단계로 이동
- config 프로젝트 설정 폴더를 team01로 변경
- 템플릿을 home/templates, brands/templates로 이동하고 render 경로 수정
- 공통 HTML도 brands/templates에 배치, APP_DIRS=True로 검색
- static/images, static/css, static/js로 경로 수정
- 02의 설정 파일처럼 항목별로 줄을 나누어 정리
- 01의 URL, 모델, 마이그레이션, 데이터, API, 검색/필터, 비교, 관심 저장, CSV 기능 유지
- 02의 빈 DB로 교체하지 않음

[데이터 명령]
업로드한 01의 DB에는 브랜드 데이터가 없어 최초 실행 시 필요: python manage.py seed_demo
CSV 예시 가져오기: python manage.py import_stats docs/sample_stats.csv --demo
검사: python manage.py check
테스트: python manage.py test

02의 메인 URL에서 path('/')는 path('')로 고쳤고,
01의 전체 브랜드 URL/API 연결을 유지했습니다.
