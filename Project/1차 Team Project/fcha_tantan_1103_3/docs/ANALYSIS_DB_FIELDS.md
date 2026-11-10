# 상권 DB 전체 필드

좌표는 문자열 저장·Decimal 검증으로 정밀도를 보존합니다. 금액·개수의 미확인은 null, 실제 0은 0입니다.

## DataSource

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| name | 출처 | CharField | 아니요 |  |
| url | url | URLField | 예 |  |
| collected_on | 수집일 | DateField | 아니요 |  |
| note | note | TextField | 예 |  |

## CommercialArea

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| code | 공식 상권코드 | CharField | 아니요 |  |
| version | 경계 버전 | CharField | 아니요 |  |
| name | 상권명 | CharField | 아니요 |  |
| area_type | 상권유형 | CharField | 아니요 |  |
| admin_code | 행정구역코드 | CharField | 아니요 |  |
| boundary | GeoJSON Geometry (경도, 위도) | JSONField | 예 |  |
| effective_on | 기준일 | DateField | 아니요 |  |
| verified | 코드·경계 검증 완료 | BooleanField | 아니요 |  |
| source_id | source | ForeignKey | 아니요 | market.DataSource |

## IndustryCode

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| system | 코드 체계·버전 | CharField | 아니요 |  |
| code | code | CharField | 아니요 |  |
| name | name | CharField | 아니요 |  |
| brand_category | 검수된 브랜드 업종 대응 | CharField | 예 |  |
| verified | verified | BooleanField | 아니요 |  |

## PopulationStat

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| area_id | area | ForeignKey | 아니요 | market.CommercialArea |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| period | 기준기간 (예: 2026Q2) | CharField | 아니요 |  |
| unit | 단위 | CharField | 아니요 |  |
| kind | 인구 종류 | CharField | 아니요 |  |
| total | 총 인구 | PositiveBigIntegerField | 예 |  |
| households | 총 가구 | PositiveBigIntegerField | 예 |  |
| single_households | 1인 가구 | PositiveBigIntegerField | 예 |  |
| by_age | 연령별 (미제공 항목은 null) | JSONField | 예 |  |
| by_time | 시간대별 | JSONField | 예 |  |
| by_day | 요일별 | JSONField | 예 |  |

## IndustrySales

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| area_id | area | ForeignKey | 아니요 | market.CommercialArea |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| period | 기준기간 (예: 2026Q2) | CharField | 아니요 |  |
| unit | 단위 | CharField | 아니요 |  |
| industry_id | industry | ForeignKey | 아니요 | market.IndustryCode |
| amount | 매출액 | PositiveBigIntegerField | 예 |  |
| transactions | 매출 건수 | PositiveBigIntegerField | 예 |  |
| by_age | by age | JSONField | 예 |  |
| by_time | by time | JSONField | 예 |  |
| by_day | by day | JSONField | 예 |  |

## StoreTrend

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| area_id | area | ForeignKey | 아니요 | market.CommercialArea |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| period | 기준기간 (예: 2026Q2) | CharField | 아니요 |  |
| unit | 단위 | CharField | 아니요 |  |
| industry_id | industry | ForeignKey | 아니요 | market.IndustryCode |
| operating | operating | PositiveIntegerField | 예 |  |
| opened | opened | PositiveIntegerField | 예 |  |
| closed | closed | PositiveIntegerField | 예 |  |

## PublicStore

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| external_id | 원본 업소 식별자 | CharField | 아니요 |  |
| name | name | CharField | 아니요 |  |
| industry_id | industry | ForeignKey | 예 | market.IndustryCode |
| brand_id | brand | ForeignKey | 예 | brands.Brand |
| area_id | area | ForeignKey | 예 | market.CommercialArea |
| address | address | CharField | 아니요 |  |
| postcode | postcode | CharField | 예 |  |
| latitude | latitude | ExactCoordinateField | 아니요 |  |
| longitude | longitude | ExactCoordinateField | 아니요 |  |
| reference_on | reference on | DateField | 아니요 |  |
| raw | 원본 보존 | JSONField | 예 |  |

## Attractor

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| area_id | area | ForeignKey | 아니요 | market.CommercialArea |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| kind | kind | CharField | 아니요 |  |
| name | name | CharField | 아니요 |  |
| scale | scale | DecimalField | 예 |  |
| unit | unit | CharField | 예 |  |
| reference_on | reference on | DateField | 아니요 |  |

## BrandOperation

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| brand_id | brand | OneToOneField | 아니요 | brands.Brand |
| source_id | source | ForeignKey | 아니요 | market.DataSource |
| checked_on | checked on | DateField | 아니요 |  |
| price_min_krw | price min krw | PositiveIntegerField | 예 |  |
| price_max_krw | price max krw | PositiveIntegerField | 예 |  |
| channels | channels | JSONField | 예 |  |
| minimum_area_sqm | minimum area sqm | DecimalField | 예 |  |
| required_staff | required staff | PositiveSmallIntegerField | 예 |  |
| required_slots | required slots | JSONField | 예 |  |
| staff_operation_allowed | staff operation allowed | BooleanField | 예 |  |
| restrictions | 출점 제한·본사 확인 사항 | TextField | 예 |  |

## StartupCondition

| 필드명 | 설명 | 자료형 | 비워도 됨 | 연결 |
| --- | --- | --- | --- | --- |
| id | ID | BigAutoField | 예 |  |
| user_id | user | OneToOneField | 아니요 | auth.User |
| location | 희망 위치 (주소 또는 동) | CharField | 아니요 |  |
| location_scope | 위치 정밀도 | CharField | 아니요 |  |
| latitude | 위도 | ExactCoordinateField | 예 |  |
| longitude | 경도 | ExactCoordinateField | 예 |  |
| store_status | 점포 확보 여부 | CharField | 아니요 |  |
| total_budget_manwon | 총 투입 가능 예산 (만원) | PositiveBigIntegerField | 아니요 |  |
| operation | 운영 방식 | CharField | 아니요 |  |
| category | 희망 업종 | CharField | 예 |  |
| channels | 판매 방식 | JSONField | 예 |  |
| available_slots | 본인 투입 가능 시간 | JSONField | 예 |  |
| weekend | 주말 운영 가능 | BooleanField | 예 |  |
| staff_count | 투입 가능 인원 | PositiveSmallIntegerField | 예 |  |
| area | 점포 면적 | DecimalField | 예 |  |
| area_unit | 면적 단위 | CharField | 아니요 |  |
| floor | 층수 | CharField | 예 |  |
| rent_manwon | 월세 (만원) | PositiveBigIntegerField | 예 |  |
| management_manwon | 월 관리비 (만원) | PositiveBigIntegerField | 예 |  |
| deposit_manwon | 보증금 (만원) | PositiveBigIntegerField | 예 |  |
| premium_manwon | 권리금 (만원) | PositiveBigIntegerField | 예 |  |
| reserve_manwon | 별도로 확보할 운영자금 (만원) | PositiveBigIntegerField | 예 |  |
| target_profit_manwon | 목표 월 순이익 (만원) | PositiveBigIntegerField | 예 |  |
| experience | 창업·운영 경험 | CharField | 예 |  |
| can_cook | 조리 가능 | BooleanField | 예 |  |
| opening_date | 희망 오픈일 | DateField | 예 |  |
| radius_m | 매장 집계 반경 | PositiveSmallIntegerField | 아니요 |  |
| updated_at | updated at | DateTimeField | 예 |  |
