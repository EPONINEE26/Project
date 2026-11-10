# FCHA TANTAN | API 명세서 (현행 v1 + 확장안)

**Base URL:** `/api/v1`  · **현재** 공개 GET/JSON API, 인증 필요 없음

## 1. GET `/brands/` — 브랜드 전체 목록

- 응답 200 `application/json; charset=utf-8`
- 최상위: `schema_version`, `is_demo`, `source_label`, `updated_at`, `years`, `regions`, `brands`.
- `brands[]`: `id`(slug), `name`, `category`, `tagline`, `english_name`, `description`, `image`, `color`, `initial_cost_krw`, `costs`, `area_sqm`, `stats[]`.
- `stats[]`: `year`, `stores`, `opened`, `closed`, `annual_sales_krw`, `source_label`, `source_url`, `regions`(지역명:매장수).
- 현재는 전체 응답 후 브라우저에서 검색/필터/정렬을 처리.
- 실제 데이터가 하나라도 있으면 목록에서 데모 데이터 자동 제외.

```json
{
  "schema_version":"1.0",
  "is_demo":true,
  "source_label":"예시 데이터",
  "updated_at":"2026-10-13",
  "years":[2025,2024],
  "regions":["서울","경기","인천","부산","대구","광주","대전","울산","세종","강원","충북","충남","전북","전남","경북","경남","제주"],
  "brands":[{
    "id":"example-cafe","name":"예시 카페","category":"카페", "tagline":"", "english_name":"", "description":"", "image":"coffee.jpg", "color":"#F4EF76",
    "initial_cost_krw":null,"costs":{},"area_sqm":33,
    "stats":[{"year":2025,"stores":null,"opened":null,"closed":null,"annual_sales_krw":null,"source_label":"예시 데이터","source_url":"","regions":{"서울":null}}]
  }]
}
```

> 위 JSON은 구조 설명용이며 실제 DB 응답값을 보증하는 예제가 아님.

## 2. GET `/brands/{slug}/` — 브랜드 상세

| 구분 | 내용 |
|---|---|
| URL 매개변수 | slug: 문자열, 브랜드의 고유 ID |
| 성공 | 200 + 브랜드 객체(목록의 `brands[]` 요소와 같은 형식) |
| 미존재 | 404, Django 표준 오류 응답(프런트와 JSON 오류 포맷은 통일 필요) |

## 응답 규칙 / 정확성

- `annual_sales_krw`: 가맹점 평균 **연** 매출(원). 표시 월매출(만원) ≈ 연매출 / 12 / 10000.
- `stores`: 기준연도 연말 가맹점 수. `opened`, `closed`: 해당 연도 발생 건수.
- `regions`: 지역별 **매장 수**뿐이며, 지역별 매출·개폐업 수는 제공하지 않음.
- 모든 수치 필드는 `null`을 허용. `null`을 0으로 자동 치환하지 않음.
- `initial_cost_krw`와 `costs`는 참고 금액이며 임대료·권리금 등을 포함한다고 가정하지 않음.

## 향후 API v2 후보(미구현)

| 메서드 | URL | 목적 |
|---|---|---|
| GET | `/api/v2/brands/?q=&category=&region=&year=&ordering=&page=` | 검색/페이지네이션 |
| GET | `/api/v2/brands/{slug}/stats/?year=2025` | 연간 KPI 단위 조회 |
| GET | `/api/v2/regions/?year=2025` | 지역 집계 |
| POST | `/api/v2/auth/login/` | 계정 로그인(인증 설계 필요) |
| GET/POST | `/api/v2/bookmarks/` | 계정별 관심 브랜드 |
| DELETE | `/api/v2/bookmarks/{id}/` | 관심 해제 |

확장 API는 제품 기획안일 뿐 구현·동작을 보장하지 않습니다.


## 필드별 사양 (요청·응답 계약)

| 필드 | 자료형 | 필수/결측 | 추가 설명 |
|---|---|---|---|
| schema_version | string | 필수 | 현재 `1.0` |
| is_demo | boolean | 필수 | 전체 목록 기준 가상 여부 |
| updated_at | string | 빈문자열 가능 | 목록의 최근 갱신일 |
| years | integer[] | 빈 배열 가능 | 가능한 연도, 내림차순 |
| regions | string[] | 필수 | 17개 시·도 |
| brands | object[] | 빈 배열 가능 | 전체 목록 배열 |
| brands[].id | string | 필수 | ORM의 slug |
| brands[].initial_cost_krw | integer/null | 결측 가능 | 창업비용 추정치(원) |
| brands[].stats[].stores | integer/null | 결측 가능 | 연말 점포 수 |
| brands[].stats[].opened | integer/null | 결측 가능 | 신규 개업 수(연도 발생) |
| brands[].stats[].closed | integer/null | 결측 가능 | 폐업 수(연도 발생) |
| brands[].stats[].annual_sales_krw | integer/null | 결측 가능 | 평균 연매출(원) |
| brands[].stats[].regions | object | 결측값 포함 | 지역명→매장 수 |

## 오류 응답과 클라이언트 대응

| 상황 | 현재 확인된 동작 | 프런트 요구사항 |
|---|---|---|
| 목록 조회 성공 | HTTP 200 JSON | 가상/실제 표시, 연도 선택 |
| 상세 slug 미존재 | Django 404 | 돌아가기 링크, 빈 값 처리 |
| 네트워크 문제 | fetch 실패 | 재시도 버튼과 오류 문구 |
| 데이터 필드 null | null 허용 | ‘미제공’ 표시, 0으로 변조 금지 |
| 목록 0개 | `brands: []` 가능 | 결과 없음 문구 |
| GET 이외 요청 | @require_GET | 405 대응; 수정 API는 현재 없음 |

## cURL 테스트 예시

```bash
curl -i http://127.0.0.1:8000/api/v1/brands/
curl -i http://127.0.0.1:8000/api/v1/brands/example-cafe/
```

> 두 번째 slug는 예시다. 실제 slug는 브랜드 목록 응답에서 확인한다.

## 프런트엔드 연동 순서

1. 로컬 Django가 켜졌는지 확인한다.
2. 브라우저에서 `/api/v1/brands/`를 직접 열어 JSON인지 확인한다.
3. `/` 접속 시 `/app-config.js`가 `mode:'api'`로 설정되는지 확인한다.
4. 목록 카드 연도·업종·지역 필터, 상세, 비교, 관심 저장을 확인한다.
5. 네트워크 탭에서 JSON 다운로드 실패나 CORS 문제가 없는지 확인한다.

## 확장 전 합의가 필요한 부분

- 페이지네이션과 검색, 지역 요약 API, 계정별 관심 브랜드는 구현된 기능이 아니라 향후 설계안이다.
- 데이터 수집 원문에서 `opened`/`closed` 정의가 일치하지 않으면 해당 필드를 null로 유지한다.
- 관리자 수정 API(POST/PUT/DELETE)는 외부에 공개하지 않고 권한·감사로그 설계 후 개발한다.
