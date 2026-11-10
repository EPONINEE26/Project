# 지역상권분석 적용 안내

## 실행

이 ZIP은 전체 프로젝트입니다. 기존 작업 폴더를 백업한 뒤 새 폴더에 압축을 풀어 실행하세요. 기존 PC의 DB를 계속 사용할 경우 기존 db.sqlite3를 새 폴더로 복사한 후 migrate를 실행하세요. 새 ZIP의 db.sqlite3에는 첨부 원본 DB를 기준으로 새 빈 테이블과 기존 미적용 마이그레이션을 적용했습니다.

```bat
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

첨부 프로젝트의 requirements.txt 기준 Django 5.2.18에서 검증했습니다. 버전 지정은 임의로 변경하지 않았습니다.

## 변경 기능

- 회원가입: 창업 목적 '예' 선택 시 희망 위치·점포 확보 여부·총예산·운영 방식을 필수 입력합니다. 상세 조건은 선택입니다.
- 두 페이지에서 같은 StartupCondition을 저장·수정·삭제합니다. 선택 항목을 비우고 저장하면 그 값만 삭제됩니다. 전체 삭제는 분석 조건만 삭제하며 계정·다른 회원·개인 매장에는 영향을 주지 않습니다.
- 기본 위치는 동 단위 예비분석입니다. 상세 조건에서 좌표를 입력하거나 카카오 주소 좌표 변환을 사용하면 공식 경계와 연결할 수 있습니다.
- 신규 총예산은 임대보증금·권리금·운영자금을 포함합니다. 기존 MemberProfile의 창업 부담금 예산·목표 매출은 의미가 달라 자동 이관하거나 덮어쓰지 않습니다.
- 예산 후보 비교는 공시 창업 부담금과 입력된 보증금·권리금·운영자금만 확인합니다. 빠진 비용이 있으면 전체 비용 적합성 미확인으로 표시합니다. 월세·관리비·공시 비용의 포함 범위는 본사와 확인해야 합니다.
- 목표 순이익은 희망 목표로 저장하며 매출에서 임의로 순이익을 추정하지 않습니다. 미정인 운영 방식은 제외 조건으로 사용하지 않습니다.
- 브랜드 최소 면적·인원·판매 채널·직원 운영 가능 여부가 실제 등록되어 있으면 확인 가능한 제약을 적용합니다. 본인 투입 시간만으로 매장 영업시간을 충족한다고 판정하지 않습니다.
- 기존 지역 필터·등록 매장 지도·장소검색·브랜드 비교·공시 매장 표는 유지했습니다. 저장한 분석 위치 지도와 기존 탐색 지도는 서로 다른 영역임을 각각 표시합니다.
- 밝은 블루 입력 영역과 선택 위치 지도, 상권 요약 카드, 업종 자료, 브랜드 후보 카드로 구성합니다. 좁은 화면에서는 한 열로 배치합니다.

## DB 공간

모든 새 공공 자료 테이블은 비어 있습니다. 첨부 인구 엑셀은 공식 상권코드·경계 매핑 검증이 끝나지 않았으므로 자동 적재하지 않았습니다. 첨부 table.tsv의 7개 자료 종류와 서울 매장·유동인구용 구조를 포함했습니다.

| 자료 | Django 모델 | 주요 연결 기준 |
| --- | --- | --- |
| 출처·수집 이력 | DataSource | 출처 ID, URL, 수집일 |
| 공식 상권 영역·코드 | CommercialArea | 상권코드 + 경계 버전 (고유), 검증 여부 |
| 업종 코드 대응 | IndustryCode | 코드 체계·버전 + 업종코드 (고유), 검수된 브랜드 업종 |
| 유동·상주·직장인구, 가구 | PopulationStat | 공식 상권 FK + 기간 + 인구 종류 (고유) |
| 상권별 업종 추정매출 | IndustrySales | 공식 상권 FK + 기간 + 업종 FK (고유) |
| 점포·개폐업 변화 | StoreTrend | 공식 상권 FK + 기간 + 업종 FK (고유) |
| 공공 매장 좌표 | PublicStore | 출처 + 원본 업소 ID + 기준일 (고유) |
| 집객시설 | Attractor | 공식 상권 FK, 출처, 기준일 |
| 브랜드 운영 조건 | BrandOperation | 기존 brands.Brand FK (브랜드당 1건), 출처·확인일 |
| 회원별 분석 입력 | StartupCondition | 회원 FK (회원당 1건), 수정일 |

전체 필드명·자료형·필수 여부·연결 모델은 docs/ANALYSIS_DB_FIELDS.md와 data/analysis/schema.json에 정리했습니다. Django 관리자 /admin/에서 새 모델을 등록·수정할 수 있습니다.

## 좌표·경계 구조

개인 StoreLocation은 사용자 후보지이므로 공공 매장을 그 테이블에 넣지 않습니다. 공공 매장은 PublicStore에 저장해 불필요한 소유자·점주 인증 연결 없이 공공 원본 식별자를 유지합니다. 기존 StoreLocation의 좌표나 기존 데이터는 변경하지 않았습니다.

- 새 위도·경도는 SQLite의 소수 변환 손실을 막기 위해 ExactCoordinateField로 문자열 저장하고 Decimal로 검증합니다(최대 소수 25자리). 입력 파일에는 좌표를 문자열로 적어 소수 표기를 보존하세요. 가져오기 명령은 25자리를 넘는 소수를 반올림하지 않고 오류로 거부합니다.
- PublicStore.raw는 원본을 보존하는 공간입니다. 우편번호는 문자열(예: "04778")이며 정수로 변환하지 않습니다.
- 상권 경계는 CommercialArea.boundary에 GeoJSON Geometry(Polygon 또는 MultiPolygon)로 저장합니다. GeoJSON 좌표는 [경도, 위도] 순서입니다. 카카오 지도에 넘길 때만 [위도, 경도]로 변환합니다.
- 다른 경계 버전이 같은 좌표에 겹치면 임의로 하나를 고르지 않습니다. 해당 데이터셋과 사용할 경계 버전을 검수하여 verified 상태를 관리하세요.
- 주소 문자열만으로 공식 상권을 배정하지 않습니다. 위·경도와 검증된 경계가 정확히 한 건 연결될 때 통계를 표시합니다.
- 동일 원본 상권 경계는 좌표 JSON 여러 파일로 복제하기보다 공식 코드·버전 한 곳에 저장하고 모든 통계에서 외래키로 참조하는 구조를 권장합니다.

## JSON 적재

입력 폴더 data/analysis/의 01~09 JSON은 임의 데이터가 없는 빈 배열입니다. 실제 자료로 채운 다음 아래 순서로 검증·적재합니다.

1. 01_sources: DataSource
2. 02_areas: CommercialArea
3. 03_industry_codes: IndustryCode
4. 04_population: PopulationStat
5. 05_sales: IndustrySales
6. 06_store_trends: StoreTrend
7. 07_public_stores: PublicStore
8. 08_attractors: Attractor
9. 09_brand_operations: BrandOperation

각 파일의 최상위는 배열입니다. 각 항목은 model과 fields 두 키로 작성합니다. model 값은 위 모델 이름이며 fields 키는 schema.json의 필드명을 사용합니다. 관계는 source_id, area_id, industry_id, brand_id 형태의 기존 DB PK를 참조합니다. 공식 상권코드와 DB PK는 다른 값입니다. 임의 브랜드명 매칭은 수행하지 않습니다. 기존 브랜드 FK의 brand_id는 brands_brand.id이며 official_brand_id 문자열과 다릅니다.

첫 적재 때 DB PK를 생략하면 자동 생성됩니다. 다른 파일에서 참조할 PK를 /admin/에서 확인하거나 실제 적재용 ID 매핑을 먼저 정리하세요. 기존 기록을 수정할 때에는 확인된 id를 명시합니다. id가 없는 중복 자료는 기존 기록을 자동 합치지 않고 고유 제약 오류로 거부합니다.

```bat
python manage.py import_analysis data/analysis/01_sources.json
python manage.py import_analysis data/analysis/01_sources.json --commit
```

첫 명령은 저장 없이 전체를 검증합니다. --commit이 있을 때만 DB에 기록합니다. 한 파일에서 하나라도 잘못되면 그 파일 전체를 롤백합니다. 각 파일은 별도 트랜잭션이므로 선행 파일이 저장된 후 후행 파일이 실패해도 선행 파일은 남습니다.

통계 period는 YYYYQn(예: 2026Q2) 등 동일한 정렬 규칙으로 통일하세요. 단위와 출처는 필수입니다. 연령·시간·요일별 JSON은 제공된 항목만 넣고 미제공 값은 null로 남기세요. 0은 실제 0일 때만 입력하세요. 서로 별도로 집계된 연령·시간 자료를 곱하지 않습니다. 상권과 상권배후지 자료를 같은 영역으로 섞지 마세요.

## 현재 구현 범위와 미연결 자료

현재 자료로 브랜드 후보·사용자 입력 관리·공식 경계 연결·인구/매출/개폐업 자료 표시는 가능합니다. 모든 공공 통계에 기간·단위·출처·수집일을 표시합니다. 업종 점수·주거/오피스 판정·반경 경쟁률·시간대별 업종 적합도는 데이터와 평가 방식의 검증이 필요하므로 판단 보류입니다. 브랜드 전국 평균매출을 동네 예상매출로 표시하지 않습니다.

지도에는 선택 핀·검증된 공식 경계·반경 표시 토글이 있습니다. 반경 원은 범위를 보여주며 공공 매장의 실제 반경 집계를 뜻하지 않습니다. 이 집계는 향후 원본 좌표 적재·동일 기준일 정리 후 연결해야 합니다. public store 자료를 사용자 등록 매장으로 잘못 표시하지 않습니다.

카카오 지도와 주소 좌표 변환은 .env의 KAKAO_JS_KEY 및 카카오 개발자 사이트의 허용 도메인 설정이 필요합니다. 키가 없어도 주소 직접 입력과 조건 저장은 가능합니다. 외부 지도·주소검색의 실제 연결은 이 환경에서 검증하지 못했습니다. 브라우저 렌더링 검증도 완료하지 못했으며 서버 템플릿 렌더링과 JS 문법을 검사했습니다.

## 주요 수정 파일

- accounts/forms.py, accounts/templates/accounts/member_fields.html: 회원가입·프로필의 공통 창업 조건
- market/analysis_models.py, market/models.py, market/migrations/0003_*.py: 새 DB 모델·마이그레이션
- market/analysis_forms.py, market/analysis.py, market/urls.py: 조건 검증·회원별 저장·경계 연결·후보 비교
- market/admin.py, market/management/commands/import_analysis.py: 관리자·검증 적재
- brands/views.py, brands/recommend.py: 페이지 연결
- brands/templates/bregion.html, recommend.html, includes/analysis_*.html, includes/condition_editor.html: 화면
- static/css/analysis.css, static/js/analysis.js: 반응형 구성·주소 검색·지도
- 기존 화면의 메뉴명 문자열: 지역상권분석으로 변경

공식 기술 참고: https://docs.djangoproject.com/en/5.2/ref/models/fields/ 및 https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/
