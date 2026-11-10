# 커뮤니티 화면 수정본

이 ZIP은 통합 탭 버전입니다. 점주 커뮤니티의 점주 이야기 / 폐점주 커뮤니티 탭에서 이동합니다.
상단과 회원 메뉴에는 점주 커뮤니티 진입점을 제공합니다.

첨부된 화면의 배너, 배너 아래 탭, 카테고리, 검색창, 게시글 카드, 오른쪽 안내 카드 구조를 사용합니다.
폐점주 커뮤니티도 같은 배너·목록·사이드바 구조를 사용합니다.
비로그인 상태에서도 이 구조를 유지하고, 목록 영역에 로그인·회원가입 안내를 표시합니다.
실제 폐업 게시글 제목과 본문은 로그인 회원에게만 제공하며, 글쓰기는 폐업 인증 승인 후 가능합니다.

## 실행

1. ZIP을 새 폴더에 압축 해제하세요.
2. `start.bat`을 실행하세요.
3. 수동 실행 시 `python -m pip install -r requirements.txt`를 실행하세요.
4. `python manage.py migrate`를 실행하세요.
5. `python manage.py runserver`를 실행하세요.
6. 점주 커뮤니티의 폐점주 커뮤니티 탭으로 이동하세요.

## 확인 방법

- `python manage.py check`
- `python manage.py test community`
- `python scripts/verify_community_package.py ZIP경로`

각 ZIP에는 소스, SQLite backup API로 생성한 DB 복사본, 데이터, 정적 파일을 포함합니다.
가상환경, 비공개 증빙, 환경 비밀값, 캐시, 기존 ZIP은 제외합니다.
