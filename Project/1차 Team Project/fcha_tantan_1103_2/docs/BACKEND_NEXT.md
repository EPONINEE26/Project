# 실제 데이터 연결 순서

1. README에 따라 runserver를 실행합니다. DB를 새로 만들 때만 migrate, seed_demo를 실행합니다.
2. brands/urls.py → brands/views.py → brands/templates/blist.html 흐름을 확인합니다.
3. 원본 자료의 연도·단위·지표 정의를 확인하고 별도 raw 폴더에 보관합니다.
4. Pandas로 브랜드 식별자, 업종, 17개 지역명을 정리합니다.
5. 가맹점 평균 연매출을 원 단위로 환산합니다. 본사 매출과 구분합니다.
6. 실제 폐업 자료가 없으면 closed를 빈칸으로 둡니다.
7. docs/sample_stats.csv 형식으로 저장하고 import_stats 명령으로 입력합니다.
8. 관리자에서 실제 이미지·소개·비용을 입력합니다.
9. 데이터 규모가 커지면 서버 페이지네이션과 쿼리 최적화를 추가합니다.
10. 로그인·권한, 운영 DB, 배포는 후속 단계입니다.

일반 페이지는 views.py가 DB를 조회해 HTML로 렌더링합니다.
JSON API는 api_views.py에서 별도로 제공합니다.
