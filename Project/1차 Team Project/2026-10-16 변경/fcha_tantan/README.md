# 프차 탄탄 — 학원 실습 구조 정리본

이번 프로젝트는 django-admin startproject fcha_tantan으로 새로 만든 기본 구조를 사용합니다.
aix_web_1007/p1015/project04 실습처럼 manage.py와 앱, static이 같은 위치에 있습니다.
settings.py는 안쪽 fcha_tantan/settings.py 하나뿐입니다. backend·config 폴더는 없습니다.

## CMD에서 바로 실행

압축을 풀고 manage.py가 보이는 바깥쪽 fcha_tantan 폴더로 이동합니다.

```cmd
cd /d "압축을 푼 경로\fcha_tantan"
python manage.py runserver
```

접속: http://127.0.0.1:8000/
종료: Ctrl+C

예시 브랜드 8개와 2024·2025년 통계가 들어 있는 db.sqlite3를 포함했습니다.
처음 확인할 때 migrate·seed_demo를 다시 실행할 필요가 없습니다.
Django 등 필요한 패키지가 설치되어 있으면 pip 설치 명령도 생략합니다.
설치되지 않은 패키지 오류가 날 때만 python -m pip install -r requirements.txt를 실행하세요.
원본 requirements의 Django 5.2 계열 조건을 유지했으며 이전 단계에서 6.1.2도 검수했습니다.
설치 명령은 기존 전역 패키지 버전을 바꿀 수 있으므로 현재 환경에서 실행된다면 생략하세요.

## DB를 새로 만들 때만

```cmd
python manage.py migrate
python manage.py seed_demo
```

seed_demo는 원본에 있던 예시 데이터 입력 명령이며 매번 실행하는 명령이 아닙니다.
관리자 계정은 포함하지 않았습니다. 필요하면 python manage.py createsuperuser로 만듭니다.
HTML 더블클릭이나 Live Server 대신 Django 서버 주소로 확인합니다.

## 폴더와 문서

- fcha_tantan/: settings.py·프로젝트 urls.py·asgi.py·wsgi.py
- home/templates/index.html: 메인 HTML
- brands/templates/: 나머지 화면, base.html, includes 조각
- static/images·css·js/: 원본 이미지·스타일·JavaScript
- docs/PROJECT_STRUCTURE.md: 실습 구조 비교와 전체 파일 역할
- docs/HTML_SYNTAX.md: HTML별 Django·HTML·CSS·JavaScript 문법
- docs/PAGE_NAVIGATION.md: HTML별 버튼과 이동 경로
- docs/LEARNING_GUIDE.md, SCHOOL_PATTERN.md: 배운 문법과 연결
- docs/VERIFICATION.md: 이번 정리본의 검수 결과와 제한
- 나머지 docs: 원본 API·이미지 출처·디자인·CSV 자료

직접 만든 앱은 home와 brands 두 개입니다. 안쪽 fcha_tantan은 설정 패키지, includes·templatetags는 앱 내부 폴더입니다.
통계·브랜드는 원본의 가상 데이터입니다. 기존 화면 문구·폼·메뉴·차트와 CSS·JS·이미지를 유지했습니다.
