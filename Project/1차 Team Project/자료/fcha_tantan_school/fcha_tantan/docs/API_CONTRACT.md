# API 계약 v1

`GET /api/v1/brands/` 는 backend/brands/data/brands.json과 동일한 모양을 반환합니다.
`GET /api/v1/brands/{slug}/` 는 하나의 브랜드 객체를 반환합니다. 없는 브랜드는 404.
조회 전용 GET입니다. JSON API는 모든 레코드를 제공합니다. Django HTML 화면은 서버에서 검색·필터·정렬합니다. 수천 브랜드 규모가 되면 서버 검색·페이지네이션으로 전환하세요.

## 최상위

| 필드 | 형식 | 의미 |
| --- | --- | --- |
| schema_version | 문자열 | 1.0 |
| is_demo | 불리언 | 가상 여부 |
| source_label | 문자열 | 원자료 출처 |
| updated_at | YYYY-MM-DD | 갱신일 |
| years | 정수 배열 | 최신순 기준연도 |
| regions | 문자열 배열 | 17개 지역 |
| brands | 객체 배열 | 브랜드 |

## 브랜드

id: 고유 slug. name, category, tagline, english_name, description: 문자열.
image: backend/static/brands/assets 안의 파일 이름. color: #RRGGBB.
initial_cost_krw: 정수 원 또는 null. costs: 항목명→원 금액. area_sqm: 제곱미터.
stats: 연도별 통계 배열.

## 연도별 통계

| 필드 | 단위/형식 | 정의 |
| --- | --- | --- |
| year | 정수 | 기준연도 |
| stores | 정수/결측 null | 전국 연말 가맹점 수 |
| opened | 정수/null | 해당 연도 실제 신규 개업 수 |
| closed | 정수/null | 해당 연도 실제 폐업 수 |
| annual_sales_krw | 정수 원/null | 가맹점 평균 연매출 |
| regions | 지역명→정수/null | 지역별 연말 매장 수 |
| source_label/source_url | 문자열 | 실제 API의 원자료 출처 |

월매출 표시 = round(annual_sales_krw / 12 / 10000), 화면은 만원 단위.
null은 미제공입니다. 0은 검증된 0건입니다. 서로 바꾸지 않습니다.
개업·폐업은 누적이 아닌 선택 연도 합계. 계약종료/해지는 실제 폐업과 다릅니다.
지역이 바뀌어도 전국 매출/개업/폐업은 변하지 않습니다. 지역 자료가 없기 때문입니다.

## CSV 입력

docs/sample_stats.csv 참조. 한 행은 브랜드 1개 × 연도 1개 × 지역 1개.
전국 지표는 17개 지역 행에 똑같이 반복합니다. 합산하지 않고 동일값인지 검증 후 한 번만 저장합니다.
지역은 서울, 경기, 인천, 부산, 대구, 광주, 대전, 울산, 세종, 강원, 충북, 충남, 전북, 전남, 경북, 경남, 제주.
세종특별자치시 → 세종처럼 원자료의 이름을 정규화한 후 입력하세요.
미제공 수치는 빈칸. 숫자에 쉼표/음수/소수 금지. 17개 지역 모두 있어야 합니다.
CSV importer는 브랜드 이름/업종 및 통계만 가져옵니다. 사진·소개·비용은 관리자에서 별도로 입력하세요.
잘못된 값·중복·합계 불일치는 전체 트랜잭션을 취소합니다.
동일 브랜드/연도는 갱신하고 CSV에 없는 연도는 유지합니다.

가상 CSV 테스트:
```powershell
.\.venv\Scripts\python.exe backend\manage.py import_stats docs\sample_stats.csv --demo
```
실데이터 CSV:
```powershell
.\.venv\Scripts\python.exe backend\manage.py import_stats C:\data\verified_stats.csv
```
실데이터가 1개라도 들어오면 목록 API에서 데모 브랜드를 제외합니다. 가상/실제 식별자 충돌은 거부합니다.
현재 API는 브랜드 목록 전체 조회 방식입니다. 관심/비교 목록은 Django 세션으로 저장하며, 인증·계정별 동기화·크롤링은 다음 단계입니다.
