# aix_web_1007과 같은 프로젝트 배치

바깥 폴더 이름과 안쪽 설정 폴더 이름이 같은 것은 startproject의 기본 구조입니다.
이번에는 실제 django-admin startproject fcha_tantan으로 기본 프로젝트를 생성했습니다.

| 학습 파일: p1015/project04 | 이번 정리본 |
| --- | --- |
| project04/manage.py | fcha_tantan/manage.py |
| project04/project04/settings.py | fcha_tantan/fcha_tantan/settings.py |
| project04/project04/urls.py | fcha_tantan/fcha_tantan/urls.py |
| project04/home/ | fcha_tantan/home/ |
| project04/member/ 같은 기능 앱 | fcha_tantan/brands/ |
| 앱 안 templates | home/templates, brands/templates |
| project04/static/ | fcha_tantan/static/ |
| project04/db.sqlite3 | fcha_tantan/db.sqlite3 |

구성 방식을 맞춘 것이며 회원 로그인 앱은 추가하지 않았습니다. 직접 만든 앱은 home·brands 두 개입니다.
settings.py는 fcha_tantan/fcha_tantan/settings.py 하나입니다.
이 문서의 다음 경로는 manage.py가 있는 바깥쪽 fcha_tantan 기준입니다.

| 파일·폴더 | 역할 |
| --- | --- |
| manage.py | Django 명령 실행 |
| fcha_tantan/settings.py | 앱·DB·템플릿·static 설정 |
| fcha_tantan/urls.py | 앱·관리자·JSON API 주소 연결 |
| fcha_tantan/asgi.py, wsgi.py | 서버 진입점 |
| home/urls.py, views.py | 메인 주소와 데이터 전달 |
| home/templates/index.html | 메인 본문 |
| brands/urls.py | 목록·상세·비교·관심·지역 주소 |
| brands/views.py | DB 조회·필터·통계·세션·화면 출력 |
| brands/models.py | 브랜드·연도 통계·지역 통계 모델 |
| brands/admin.py | 관리자 모델 등록 |
| home/apps.py, brands/apps.py | 앱 기본 설정 |
| brands/api_views.py | JSON API 응답 |
| brands/constants.py | 지역 목록 |
| brands/templates/base.html | 모든 화면의 메뉴·푸터 |
| brands/templates/*.html | 목록·상세·비교·지역·관심·안내 |
| brands/templates/includes/ | 반복 사용하는 HTML 조각 |
| brands/templatetags/brand_format.py | 숫자·금액 표시 필터 |
| brands/data/brands.json | 원본 예시 데이터 |
| brands/management/commands/ | 예시 입력·CSV 가져오기 명령 |
| home/migrations/, brands/migrations/ | DB 구조 변경 기록 |
| brands/tests.py | 기존 기능 테스트 |
| static/images/ | 원본 이미지 9개 |
| static/css/style.css, django.css | 원본 디자인·폼 스타일 |
| static/js/common.js | 필터 선택 시 폼 자동 제출 |
| db.sqlite3 | 마이그레이션과 예시 데이터 준비 완료 |
| requirements.txt | 원본 패키지 목록 |
| docs/ | 문법·이동 경로·API·검수·출처 문서 |

APP_DIRS=True, DIRS=[]로 앱 안 templates를 찾습니다.
STATICFILES_DIRS=[os.path.join(BASE_DIR, 'static')]를 사용합니다.
render(request, 'index.html', context), render(request, 'blist.html', context)처럼 학원 방식으로 파일명을 전달합니다.
원본의 관계형 통계 모델, CSV 입력, JSON API, 공통 HTML·필터 폴더는 기능 보존을 위해 유지했습니다.
__pycache__는 Python이 자동으로 만들며 압축에서는 제외했습니다.
