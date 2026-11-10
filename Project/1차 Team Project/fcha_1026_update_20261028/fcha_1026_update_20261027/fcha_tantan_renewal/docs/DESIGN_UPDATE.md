# Django 템플릿 전환

기존 네이비·옐로우 색상, 서체, 카드, 상세 지표, 지역 통계, 비교 표의 CSS를 유지했습니다.
메인과 각 페이지를 별도 HTML 파일로 분리했습니다.
JavaScript 해시 주소 대신 Django URL을 사용합니다.
검색·정렬은 서버에서 처리하며 화면을 다시 불러옵니다.
동적 compare 버튼은 Django POST 폼으로 바뀌었습니다.
기존 카드·차트·표 스타일은 유지하며 Django form 배치를 django.css로 보완했습니다.
