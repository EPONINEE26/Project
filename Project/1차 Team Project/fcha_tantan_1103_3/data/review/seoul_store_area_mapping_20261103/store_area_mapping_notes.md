# 서울 매장 ↔ 상권 미리보기 대응표

전체 554,092건, 상권 1,643개. 원본 변경 없음. DB 적재/서비스 수정 없음.

## 입력 구조와 ID
ZIP manifest.process_order의 PublicStore 분할 JSON 56개를 사용. 배열의 model/fields 구조이며 public_store_id=fields.id, source_id=fields.source_id, external_id=fields.external_id. area_id=CommercialArea.fields.id (code가 아님). 원본 ID를 새로 발급하지 않음. JSON 숫자 ID는 CSV 십진 문자열로 출력하고 문자열 ID와 external_id는 그대로 보존. CSV는 UTF-8 BOM. Excel에서 열 때 ID 열을 텍스트로 가져와야 함.
매장 longitude/latitude 원본 문자열은 수정하지 않고 계산 때만 Python float(IEEE 754 binary64)로 변환. 경계는 GeoJSON [longitude, latitude].

## 좌표계 근거와 가정
DataSource.note는 원본 경도·위도 사용 및 좌표계 변환 이력 미확인이라고 명시. 경계에는 authoritative CRS/EPSG 선언 없음. 경위도 필드명/GeoJSON 구조는 축 순서 근거이나 동일 datum을 증명하지 못함. 두 자료가 동일 경위도 좌표계라고 가정하여 평면 XY 위상 판정 수행. EPSG:4326 공식 확인이나 CRS 변환은 하지 않음. 범위만으로 좌표계 확정하지 않음.
경계 version=project-preview-20261103, effective_on=null, verified=false. 공식 기준일/변환 이력 미확정. 매장 reference_on=2026-11-03은 프로젝트 스냅샷 날짜.

## 알고리즘
모든 Polygon/MultiPolygon, 내부 구멍 및 구멍 경계 반영. 폐합·좌표·유효성 검증 후 STRtree의 축 정렬 bounding box 후보 전체에 g.touches(point)와 g.contains(point)를 적용. bbox 밖 도형은 점과 만날 수 없어 생략 가능. 하나라도 touches면 boundary, 그렇지 않고 contains 두 개 이상이면 overlap, 하나면 matched, 없으면 outside. 잘못된 좌표는 invalid_coordinate. geometry 오류 시 진단 저장 후 assert로 중단하며 임의 복구/제외하지 않음.
review.reason은 interior_area_ids와 boundary_area_ids를 별도 보관. candidate_area_ids는 두 배열의 합집합 JSON. matched만 area_id 기입.

## 경계선 및 수치
정확한 사용 함수: shapely geometry.touches(Point), geometry.contains(Point), STRtree.query(Point). 임의 epsilon/거리 허용오차 없음(0), 버퍼/반올림/보정/최근접 없음. GEOS 부동소수점 위상 판정이며 임의정밀 산술 또는 측량 정확도 보장은 아님. 경계에 매우 가까워도 touches가 False면 boundary로 확대하지 않음.

## 실행과 검증
Python 3.12.14, Shapely 2.2.0, GEOS 3.14.1. requirements.txt 참조. 원본 ZIP을 풀어 편집하지 않고 ZipFile에서 읽음. 점으로 시작하는 경로 구성요소는 manifest에 있더라도 제외. 입력 manifest의 비숨김 파일 해시 및 JSON 건수 모두 검증. ZIP 컨테이너/상권 JSON SHA도 산출 manifest에 기록.

```bash
python -m pip install -r requirements.txt
python process_store_area.py --stores-zip seoul_public_stores_20261103.zip --areas 02_areas.json --output result
```
출력은 새 디렉터리로 지정. 실패 시 기존 출력물은 최종 결과로 사용하지 말 것.
필수 검증: 입력/CSV 건수, ID 중복/누락, ID·source_id·external_id 순서 포함 전체 SHA 대조, 상태 합계, matched 실제 ID 존재, 비matched 빈 area_id, 상권별 합계, review 건수 및 유일성 통과. 검증 상세는 summary.validation.

## 한계
공식 검증이 아닌 프로젝트 미리보기. 1,643개 입력 경계 전체에 대한 계산 완전성만 확인하며, 실제 누락 상권·원본 정확도·최신성은 증명하지 않음. outside는 영업 여부나 주소 오류를 의미하지 않음. 서로 다른 상권 유형도 모두 비교하여 중첩은 그대로 overlap 처리. 브랜드/상호명/주소 추정 연결 없음.
공식 함수 설명: https://shapely.readthedocs.io/en/stable/strtree.html 및 https://shapely.readthedocs.io/en/stable/manual.html
