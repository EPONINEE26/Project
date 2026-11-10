# HTML별 버튼과 이동 경로

HTML을 더블클릭하지 말고 Django 서버를 실행한 뒤 http://127.0.0.1:8000/ 에 접속합니다.
아래 HTML 경로는 바깥쪽 fcha_tantan 폴더 기준입니다. <slug>는 tantan 같은 브랜드 식별자입니다.

## 페이지 주소

| HTML 파일 | 화면 | 주소 | 뷰 함수 |
| --- | --- | --- | --- |
| home/templates/index.html | 메인 | / | home.views.index |
| brands/templates/blist.html | 브랜드 목록 | /brands/blist/ | blist |
| brands/templates/bview.html | 브랜드 상세 | /brands/bview/<slug>/ | bview |
| brands/templates/bcompare.html | 비교 | /brands/bcompare/ | bcompare |
| brands/templates/bregion.html | 지역 | /brands/bregion/ | bregion |
| brands/templates/bsaved.html | 관심 브랜드 | /brands/bsaved/ | bsaved |
| brands/templates/guide.html | 데이터 안내 | /brands/guide/ | guide |

## 모든 페이지 공통: brands/templates/base.html

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 상단·하단 프차 탄탄 로고 | 메인 / |
| 브랜드 탐색 | /brands/blist/?year=선택연도 |
| 지역 살펴보기 | /brands/bregion/?year=선택연도 |
| 브랜드 비교 | /brands/bcompare/?year=선택연도 |
| 데이터 안내 | /brands/guide/ |
| ♡ 관심 브랜드 | /brands/bsaved/?year=선택연도 |
| 하단 데이터 기준 및 이용 안내 | /brands/guide/ |
| 본문으로 건너뛰기 | 현재 페이지 #main |
| 하단 비교함 × | 해당 브랜드 비교 해제 후 현재 페이지로 복귀 |
| 하단 비교함 비우기 | 비교 선택 전체 해제 후 현재 페이지로 복귀 |
| 하단 비교하기 | /brands/bcompare/?year=선택연도 |

비교함은 1개 이상 선택했고 현재 화면이 비교 페이지가 아닐 때 나타납니다.

## index.html: 메인

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 브랜드 둘러보기 | 같은 페이지 #brands 목록 위치 |
| 지역에서 기회를 찾다 | /brands/bregion/ |
| 숫자의 기준을 읽다 | /brands/guide/ |
| 검색·필터·브랜드 카드 | 아래 공통 목록 설명과 동일 |

## blist.html / bsaved.html / 메인 공통 목록

목록 본문은 brands/templates/includes/list_section.html, 카드는 brand_card.html입니다.

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 검색창 입력 후 Enter 또는 ↵ | 현재 주소로 query를 GET 전송해 검색 |
| 업종: 전체·카페·치킨·편의점·미용실 | category를 바꾸고 현재 목록 재조회 |
| 지역 선택 | region을 바꾸고 현재 목록 재조회 |
| 연도 선택 | year를 바꾸고 현재 목록 재조회 |
| 조회 | 선택한 검색·필터 조건을 GET 전송 |
| 정렬 선택 | sort를 바꾸고 현재 목록 재조회 |
| ↻ 초기화 | 현재 경로에서 검색 조건 제거 |
| 카드 사진 / 브랜드 이름 / 자세히 보기 | /brands/bview/<slug>/?year=선택연도 |
| ♡ 또는 ♥ | POST /brands/saved/toggle/<slug>/ 후 현재 페이지 복귀 |
| 비교 담기 / 비교함에서 빼기 | POST /brands/compare/toggle/<slug>/ 후 현재 페이지 복귀 |
| 빈 목록의 모든 브랜드 둘러보기 | /brands/blist/ |

관심 화면은 저장한 브랜드만 표시합니다. 비교는 최대 3개, 관심·비교 선택은 브라우저 세션에 저장합니다.
필터 자동 제출은 static/js/common.js가 담당합니다. JavaScript가 없으면 조회 버튼을 사용합니다.

## bview.html: 상세

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 브랜드 탐색 / ← 브랜드 목록으로 | 브랜드 목록 (뒤로 링크는 선택 연도 유지) |
| 연도 / 조회 | 현재 브랜드의 선택 연도 통계 재조회 |
| 비교 / 하트 | 위 목록과 같은 POST 처리 |
| 브랜드 한눈에 | #overview |
| 개·폐업 현황 | #trend |
| 지역별 매장 | #distribution |
| 창업비용 | #cost |
| 전체 지역 브랜드 비교하기 | /brands/bregion/?year=선택연도 |
| 전체 17개 지역 매장 수 확인 | details 태그 열기·닫기, 페이지 이동 없음 |
| 지표 정의 자세히 보기 | /brands/guide/ |

## bcompare.html: 비교

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 연도 / 조회 | 선택 브랜드를 선택 연도로 재비교 |
| CSV 내려받기 | /brands/compare/csv/?year=선택연도 파일 다운로드 |
| 브랜드 추가 + | /brands/blist/?year=선택연도 |
| 비교표 브랜드 이름 ↗ | 브랜드 상세 (연도 유지) |
| 비교함에서 빼기 | 해당 브랜드 비교 해제 후 비교 화면 복귀 |
| 브랜드 선택하러 가기 | 비교함이 비었을 때 /brands/blist/ |

## bregion.html: 지역

| 누르는 항목 | 이동 또는 처리 |
| --- | --- |
| 연도 / 조회 | 선택한 지역 유지, 연도 변경 |
| 지역 타일 | /brands/bregion/?region=지역명&year=선택연도 |
| 표의 브랜드 이름 | 브랜드 상세 (연도 유지) |
| 표의 비교 담기 / 빼기 | 해당 브랜드 비교 선택 변경 |

## guide.html: 데이터 안내

본문은 지표 설명입니다. 본문 전용 이동 버튼은 없고 공통 메뉴를 사용합니다.

## includes 안 HTML은 독립 페이지가 아닙니다

| 파일 | 역할 |
| --- | --- |
| badge.html | 예시 데이터 또는 출처 배지 |
| bars.html | 지역 매장 막대 |
| brand_card.html | 사진·브랜드명·하트·비교·상세 카드 |
| compare_button.html | 비교 POST 폼 |
| list_section.html | 검색·필터·목록 |
| save_button.html | 관심 POST 폼 |
| year_select.html | 연도 선택 |

includes는 앱 이름이 아니라 HTML 조각을 담은 폴더입니다. base.html도 별도 주소 없이 각 페이지가 extends로 공유합니다.
