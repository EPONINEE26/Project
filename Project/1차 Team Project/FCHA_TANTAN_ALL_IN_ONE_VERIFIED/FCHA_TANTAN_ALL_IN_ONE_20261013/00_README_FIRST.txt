FCHA TANTAN | 전체 통합 설계·로컬 실행 패키지
작성 기준: 2026-10-13 / 원본 fcha_tantan.zip

1. ZIP을 먼저 모두 압축 해제하세요.
2. OPEN_FIRST.html 더블클릭 → 설계 문서 PDF 6종/와이어프레임 열기.
3. 편집할 때는 01_DOCUMENTS/*.docx 사용; 같은 이름의 PDF는 확인용.
4. Django 실행: 03_WEBSITE_SOURCE/RUN_SITE_WINDOWS.bat 더블클릭. Python 3.12~3.13 권장, 첫 패키지 설치에는 인터넷 필요.
5. 정적 데모: 03_WEBSITE_SOURCE/RUN_FRONTEND_WINDOWS.bat 더블클릭.
6. 개발환경 서버 주소: http://127.0.0.1:8000 (Django), http://127.0.0.1:8080 (정적).
7. 원본 소스는 03_WEBSITE_SOURCE에 있으며 UI 자체는 설계 문서에 맞춰 자동 수정되지 않았습니다.
8. 주의: 브랜드 8개 및 2024/2025 통계는 전부 가상. 실제 데이터 수집/배포 완료 버전이 아닙니다.
9. 관심 브랜드 localStorage; 로그인/계정 동기화 없음. SCR-05 빈 화면 유형 구분은 QA 개선 항목.
10. 작업 범위는 로컬 개발용으로, 프로덕션 HTTPS/SECRET_KEY/DB 백업 등 운영 준비는 별도입니다.

폴더:
  01_DOCUMENTS   : 6개 영역의 DOCX+PDF, 관련 MD, ERD 및 아키텍처 이미지, OpenAPI YAML
  02_UI_PREVIEW  : 인터랙티브 와이어프레임 HTML과 확인용 화면 PNG
  03_WEBSITE_SOURCE : 오리지널 HTML/CSS/JS/Django 프로젝트 및 로컬 실행 BAT
  04_VERIFICATION: 파일 검사 및 소스 테스트 결과
