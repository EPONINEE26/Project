# 학원 패턴과 연결

## 기본 흐름

1. /brands/blist/?year=2024 주소로 접속합니다.
2. config/urls.py가 brands/urls.py를 연결합니다.
3. brands/urls.py가 views.blist를 호출합니다.
4. views.py가 request.GET에서 연도를 받고 models.py의 DB 데이터를 조회합니다.
5. render(request, 'brands/blist.html', context)로 데이터를 전달합니다.
6. HTML에서 {% for row in rows %}로 카드를 반복합니다.
7. 상세 링크 {% url 'brands:bview' row.brand.slug %}로 이동합니다.

## 학생 프로젝트와 비교

| 학원 학생 프로젝트 | 프차 탄탄 |
| --- | --- |
| students 앱 | brands 앱 |
| Stu 모델 | Brand 모델 |
| slist(request) | blist(request) |
| sview(request, no) | bview(request, slug) |
| students/urls.py | brands/urls.py |
| slist.html | blist.html |
| {{ stu.name }} | {{ row.brand.name }} |
| 학생 입력/수정/삭제 폼 | 현재는 Django 관리자에서 관리 |

## 왜 HTML에 include가 있는가

base.html에는 모든 화면이 공유하는 메뉴와 푸터가 있습니다.
각 페이지는 extends로 base.html을 사용하고 block content에 본문을 작성합니다.
목록 화면·메인·관심 브랜드가 공유하는 검색/카드 HTML은 includes/list_section.html에 있습니다.
카드 모양을 바꾸려면 includes/brand_card.html, 상세 내용을 바꾸려면 brands/bview.html을 수정합니다.
블록이나 include도 Django 템플릿 문법이며 JavaScript로 화면을 생성하는 방식이 아닙니다.

## 데이터 요청과 버튼

검색·필터: GET → DB 조회 → render.
비교·관심: POST → csrf 검증 → session 변경 → redirect → GET 화면.
비교 CSV: GET → 선택 브랜드 DB 조회 → CSV 응답.
JSON API는 api_views.py에 남아 있으며 화면 뷰와 분리되어 있습니다.

## 생성되는 파일

backend/db.sqlite3: migrate 이후 생성되는 실제 DB 파일입니다.
.venv/: pip 패키지를 프로젝트별로 설치하는 가상환경입니다.
__pycache__/: Python 자동 생성 캐시입니다.
이 파일들은 배포 압축에 포함하지 않습니다.
