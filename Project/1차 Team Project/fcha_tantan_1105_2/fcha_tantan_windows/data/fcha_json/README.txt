프차탄탄 JSON 데이터 / 2026-10-19T21:24:41+09:00

1. 파일
brands.json: 전체 업종, 공식 브랜드ID 12,498개. 최상위는 브랜드 배열입니다.
priority_brands.json: 카페·치킨·편의점·미용실 우선 업종 1,821개. 최상위 배열입니다.
metadata.json: 필드 설명·단위·출처·페이지 사용법.
data_quality.json: 수집 건수·중복·브랜드 연결 불일치·미연결 원본·검증 결과.
example_mega.json: 실제 메가엠지씨커피 1개 브랜드의 전체 구조를 보기 좋게 정리한 예시.

2. 사용
메인/비교: priority_brands.json에서 category, name, history의 2024/2025 항목을 선택.
상세: brands.json에서 id가 같은 객체를 찾습니다.
브라우저: const brands = await (await fetch('/static/data/priority_brands.json')).json();
Django/Python: brands = json.load(open('brands.json', encoding='utf-8'))
전체 파일은 크므로 서버에서 읽어 페이지·필터별로 필요한 브랜드만 전달하는 것을 권장합니다.

3. 요청 반영
id는 coffee_20160628처럼 업종 접두어와 공식 브랜드관리번호를 조합했습니다.
year는 요청대로 2024년 공시=2024, 2025년 공시=2025로 입력했습니다.
원본 acntgYr는 source_accounting_year에 별도 보관했습니다.
전국 17개 시도 실제 데이터이며 더미를 만들지 않았습니다.
이미지·소개문구는 수집되지 않아 null. 임의의 로고나 파일명을 넣지 않았습니다.

4. 숫자 해석
stores는 가맹점 수, total_stores는 가맹점+직영점입니다.
opened는 신규등록, closed는 계약종료+해지입니다. 지역별 개폐업 수는 제공되지 않습니다.
전국 annual_sales_krw는 가맹점당 연간 평균매출입니다.
지역 매출은 범위값이므로 annual_sales_min_krw/annual_sales_max_krw를 표시하세요.
null은 0이 아닙니다. 미공개·미연결 데이터를 0원으로 표시하지 마세요.
금액은 정보공개서 표준 천원 단위에서 원으로 1000배 변환했습니다.
회사의 전체 매출/순이익, 홀·배달 매출, 점주 수익률, 로고는 이 자료에서 얻을 수 없습니다.

5. 매칭
공식 브랜드ID가 있는 자료는 ID로 연결했습니다.
ID 없는 전국 현황·창업비용은 같은 연도의 회사명+브랜드명+업종을 완전일치시켰습니다.
중복이거나 이름이 달라 연결을 확정할 수 없는 값은 null로 두고 data_quality.json에 보존했습니다.
본부ID가 연도별로 달라질 수 있으므로 브랜드ID를 주키로 사용하세요.

검증: {'region_rows_checked': 367489, 'history_rows_checked': 22173, 'national_stats_rows_checked': 20045, 'unique_brand_ids_checked': 12498, 'json_files_parsed': 5}
