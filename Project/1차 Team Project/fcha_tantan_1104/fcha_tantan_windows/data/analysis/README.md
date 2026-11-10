# 지역상권분석 데이터 안내

기록 기준: 2026-11-03. 화면은 `../../db.sqlite3`의 Django 모델을 조회합니다.
이 폴더의 JSON을 수정해도 화면이나 DB가 자동으로 바뀌지 않습니다.

## 실제 데이터 위치

| 데이터 | 보존 파일 | DB 모델·상태 |
| --- | --- | --- |
| 상권·인구 출처 | [01_sources.json](01_sources.json) | DataSource ID 1·2 |
| 서울 상권 경계 | [02_areas.json](02_areas.json) | CommercialArea 1,643건 |
| 유동인구 | [04_population.json](04_population.json) | PopulationStat 36,093건, 상권 1,642개·22개 분기 |
| 공공 매장 출처·업종·매장 | [실제 적재 묶음](../review/seoul_public_stores_20261103/) | DataSource ID 3, IndustryCode 247개, PublicStore 554,092건 |
| 매장과 상권의 대응표 | [공간 가공 결과](../review/seoul_store_area_mapping_20261103/) | PublicStore.area_id 422,123건 연결 |
| 희망 업종과 공공 업종 대응 | [industry_mapping.py](../../market/industry_mapping.py) | 지도 필터의 프로젝트 미리보기 대응표 |

`03_industry_codes.json`과 `07_public_stores.json`은 현재 빈 배열(`[]`)입니다.
이번 공공 매장 적재에는 사용하지 않았으며 DB 전체를 내보낸 파일도 아닙니다.
공공 매장은 실제 적재 묶음의 manifest와 분할 JSON으로 관리합니다.
55만 건을 이 폴더의 단일 JSON에도 중복 복사하지 않습니다.

`05_sales.json`, `06_store_trends.json`, `08_attractors.json`,
`09_brand_operations.json`도 현재 빈 배열입니다. 각각 매출·개폐업·집객시설·브랜드
운영 조건의 입력 위치이며, 관련 자료는 아직 연결하지 않았습니다.
빈 파일을 실제 값 0으로 해석하지 않습니다. 상주·직장인구도 미연결 상태입니다.

## 가공·적재 순서와 의미

1. 출처 → 경계 → 유동인구 순으로 적재했습니다. 인구는 공백 정리 후
   상권명과 상권유형이 유일하게 일치할 때만 연결했습니다.
   원본 행정동·일부 자치구 표기 차이로 해당 값은 매칭 조건에서 제외했습니다.
2. 공공 매장 묶음의 manifest에 지정된 파일 해시·건수와 필드를 검증한 뒤
   출처·업종·매장 분할 JSON을 적재했습니다. 점으로 시작하는 임시 파일 4개는
   제외했습니다. 원본 좌표 문자열과 external_id를 보존했습니다.
3. Work가 매장 좌표를 Polygon/MultiPolygon 및 내부 구멍과 비교해 별도 대응표를
   만들었습니다. 로컬에서 입력·출력 해시, 전체 DB ID·좌표·경계 및 모든 공간 판정을
   다시 확인한 뒤 하나의 트랜잭션으로 `area_id`만 반영했습니다.

| 공간 판정 | 건수 | DB 처리 |
| --- | ---: | --- |
| 유일한 경계 내부 | 422,123 | 해당 area_id 연결 |
| 여러 경계 내부 | 17,946 | null 유지 |
| 경계 밖 | 114,023 | null 유지 |
| 경계선 접촉 | 0 | 연결하지 않음 |
| 좌표 오류 | 0 | 연결하지 않음 |

경계선 접촉을 우선 분류하고, 버퍼·좌표 보정·최근접 상권 선택을 하지 않았습니다.
브랜드 식별은 수행하지 않았으며 PublicStore.brand_id는 null입니다.
상호명이 같다는 이유만으로 브랜드를 확정하지 않습니다.

경계는 `project-preview-20261103`, `effective_on=null`, `verified=false`입니다.
공식 경계 기준일·좌표계 변환 이력은 미확정이며 두 자료가 같은 경위도 좌표계라는
가정으로 연결했습니다. 인구는 단위·평균/누계 정의가 미확정이므로 ‘원자료 수치’로
표시합니다. 매장의 `reference_on=2026-11-03`은 프로젝트 스냅샷 날짜이며 현재 영업을
보장하지 않습니다. 상권 경계 안의 매장 수와 선택 위치 반경 안의 매장 수는 다릅니다.

## 확인할 기록

- [경계·인구 작업 기록](../reports/seoul_preview_notes.md)
- [경계·인구 집계](../reports/seoul_preview_summary.json)
- [인구 대응표](../reports/seoul_population_mapping.csv)
- [공공 매장 최초 적재 기록](../reports/public_stores_import_notes.md)
- [희망 업종 지도 대응 정책](../reports/desired_category_map_notes.md)
- [매장 상권 연결 기록](../reports/store_area_linking_notes.md)
- [로컬 검증·DB 반영 결과](../reports/store_area_local_verification.json)
- [공간 대응표](../review/seoul_store_area_mapping_20261103/store_area_mapping.csv)
- [미연결 사유와 후보 상권](../review/seoul_store_area_mapping_20261103/store_area_review.csv)

## 나중에 확인하거나 수정할 때

개별 매장은 `PublicStore.id`와 `(source_id, external_id, reference_on)`으로 확인합니다.
상권 대응표의 `public_store_id`는 DB 기본키이며 `area_id`는 CommercialArea 기본키입니다.
상권 코드(code)와 혼동하지 마세요. CSV의 external_id는 문자열로 읽어 선행 0을 보존합니다.

이미 적재한 원본과 manifest는 보존하고, 수정 자료는 새로운 review 폴더에 따로 두세요.
수정 이유·대상 ID·변경 전후 값·출처·날짜·파일 해시를 기록한 다음 검증과 적용을 진행합니다.
좌표나 경계를 바꾸면 상권 대응도 재계산해야 합니다. 현재 연결 스크립트는 기존 대응과
충돌하면 중단하므로, 변경 적용에는 변경 내용을 검토할 수 있는 별도 처리도 필요합니다.

기존 DB에서 최초 적재 명령을 다시 실행하지 마세요. 일반 `import_analysis`는 기존 ID를
갱신할 수 있고, 공공 매장 묶음의 최초 적재 명령은 충돌 시 중단합니다.
새 DB를 재구성할 때는 모델 마이그레이션과 위 의존 순서에 맞춘 별도 절차를 준비하세요.

프로젝트 루트(`fcha_tantan_windows`)에서 현재 대응표를 검증하는 명령:

```powershell
python scripts/verify_store_area_mapping.py
```

DB는 변경하지 않지만 로컬 검증 보고서는 갱신합니다. `committed=false`는 해당 실행이
검증 전용이었다는 뜻이며 기존 DB 연결을 취소했다는 뜻은 아닙니다.
공간 검증에는 Shapely 2.x가 필요하며 현재 `.validation_deps`에 Shapely 2.2.0을 보관합니다.
권한 문제로 라이브러리를 읽지 못하면 실행 환경을 먼저 확인하세요.

검증 후 DB 연결을 적용하는 옵션은 `--commit`입니다. 실행하면 전체 재검증 후 동일 연결을
유지하고 비어 있는 area_id만 채웁니다. 다른 기존 연결은 덮어쓰지 않습니다.
화면 표시는 [analysis.py](../../market/analysis.py), 지도 조회는
[map_views.py](../../market/map_views.py)에서 확인할 수 있습니다.
