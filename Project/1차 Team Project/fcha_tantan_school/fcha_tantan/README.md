# 프차 탄탄 — 학원 패턴 Django 버전

주소 → urls.py → views.py → models.py에서 조회 → render(HTML, context) 구조입니다.
화면은 Django 템플릿의 {{ 변수 }}, {% for %}, {% if %}로 만듭니다.
JavaScript로 본문 HTML을 생성하지 않습니다.
네이비·옐로우 디자인과 검색, 업종/지역/연도 필터, 상세 통계, 비교, CSV, 관심 브랜드를 유지했습니다.
현재 8개 브랜드와 2024·2025년 통계는 가상 데이터입니다. 실제 자료 수집은 포함하지 않습니다.

## Windows PowerShell 실행

이 압축은 기존 폴더 위에 덮어쓰기보다 별도 폴더에 풀어 먼저 확인하세요.
아래 경로는 압축 안의 fcha_tantan 폴더를 C:\workspace\franchise_lens\fcha_tantan_school 안에 놓았다고 가정합니다.
기존 DB와 기존 작업 파일은 자동 이전되지 않습니다.

```powershell
cd "C:\workspace\franchise_lens\fcha_tantan_school\fcha_tantan"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
.\.venv\Scripts\python.exe backend\manage.py runserver
```

접속: http://127.0.0.1:8000/ · 서버 종료: Ctrl+C.
이 버전은 Django가 HTML을 처리하므로 python -m http.server로 실행할 수 없습니다.
가상환경 활성화나 PowerShell 실행 정책 변경은 필요 없습니다.

## 학원 방식으로 읽는 순서

1. backend/config/urls.py: 프로젝트 주소 연결
2. backend/brands/urls.py: 앱 내부 주소 연결
3. backend/brands/views.py: request.GET, request.POST, DB 조회, render와 redirect
4. backend/brands/models.py: Brand, AnnualStat, RegionalStat 데이터 구조
5. backend/templates/brands/blist.html: 목록 페이지
6. backend/templates/includes/list_section.html 및 brand_card.html: 목록과 카드 HTML
7. backend/templates/brands/bview.html: 상세 페이지
8. backend/templates/base.html: 공통 메뉴·푸터와 {% block %}

## HTML 파일과 주소

| 주소 | 뷰 함수 | HTML |
| --- | --- | --- |
| / | home.views.index | home/index.html |
| /brands/blist/ | blist | brands/blist.html |
| /brands/bview/tantan/ | bview | brands/bview.html |
| /brands/bcompare/ | bcompare | brands/bcompare.html |
| /brands/bregion/ | bregion | brands/bregion.html |
| /brands/bsaved/ | bsaved | brands/bsaved.html |
| /brands/guide/ | guide | brands/guide.html |

학생 목록 slist → 브랜드 목록 blist, 학생 상세 sview → 브랜드 상세 bview와 같은 패턴입니다.
브랜드 상세는 숫자 no 대신 브랜드 고유 문자열 slug를 사용합니다.
브랜드 입력·수정·삭제는 /admin/에서 처리합니다. 별도 작성·수정 폼이나 회원 로그인은 포함하지 않습니다.

관리자 생성:
```powershell
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
```

## 폴더 역할

- backend/home/: 메인 앱의 urls.py와 views.py
- backend/brands/: 모델, 화면 뷰, 앱 URL, 관리자, CSV 입력, 테스트
- backend/brands/api_views.py: 기존 JSON API (일반 화면은 이 API 없이 DB를 조회)
- backend/brands/data/brands.json: seed_demo용 가상 데이터
- backend/templates/: 화면별 HTML과 공통 템플릿
- backend/static/brands/css/: 디자인
- backend/static/brands/js/common.js: 필터 선택 시 폼 제출
- backend/static/brands/assets/: 이미지
- docs/: 데이터 형식, 구조 설명, 이미지 출처, 검증 결과

검색은 GET 폼으로 서버에 전달합니다. 조회 버튼이나 Enter로 검색합니다.
필터를 바꾸면 작은 JavaScript가 폼을 제출하여 페이지를 다시 불러옵니다.
JavaScript가 없어도 조회 버튼으로 동작합니다.
비교·관심 버튼은 POST + {% csrf_token %} + redirect 방식입니다.
비교는 최대 3개이며 세션에 저장합니다. 관심 브랜드도 같은 브라우저의 Django 세션에 저장합니다.
기존 정적 사이트의 localStorage 저장 목록은 자동 이전하지 않습니다.
로그인·기기 간 동기화는 없습니다. 세션 쿠키나 서버 DB를 삭제하면 저장 목록은 사라집니다.

## 실제 데이터 입력

Pandas로 검수한 CSV를 docs/sample_stats.csv 형식으로 정리한 다음:
```powershell
.\.venv\Scripts\python.exe backend\manage.py import_stats "C:\data\verified_stats.csv"
```
사진·소개·비용은 관리자에서 입력합니다. 실데이터가 있으면 목록에서 데모 브랜드를 제외합니다.

## 검증

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py test brands
```

로컬 개발용 설정입니다. 배포 시 Django 환경변수, 운영 정적 파일 제공, HTTPS, DB 백업을 설정하세요.
