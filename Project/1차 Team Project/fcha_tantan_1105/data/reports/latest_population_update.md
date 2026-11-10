# 최신 유동인구 교체 (2026-11-04)

- 현재 상태는 과거의 seoul_preview_notes.md 적재 결과보다 이 문서와 latest_population_update.json을 우선합니다.
- 원본: fdata/서울시 상권분석서비스(길단위인구-상권).csv (CP949), 2026Q2 1,648건.
- 공식 상권 코드와 유형을 검증해 1,641건 저장. 이전 floating 자료는 모두 삭제했고 2026Q2만 유지합니다.
- 기존 경계 오류로 제외된 7건은 적재하지 않았습니다. validation_report.md에 기록된 자기교차 6건과 잘린 도형 1건입니다. 상세 코드 및 명칭은 latest_population_update.json 참고.
- 이름 표기가 다른 3건은 코드와 유형으로 연결했습니다. 기존 상권 경계 명칭은 유지합니다.
- 교체 직전 만든 DB 백업은 2026-11-04 사용자 요청으로 삭제했습니다. JSON의 backup은 삭제한 파일의 과거 경로이며 backup_status에 삭제 상태를 기록합니다.
- data/analysis의 출처 및 인구 JSON도 현재 DB에 맞게 갱신했습니다. 과거 원본과 검토 기록은 보존합니다.
- 기존 prepare_seoul_analysis.py는 과거 XLSX 미리보기 생성용입니다. 최신 CSV 재적재에는 사용하지 않습니다.
- 갱신 명령: python manage.py replace_latest_population "../fdata/서울시 상권분석서비스(길단위인구-상권).csv" --commit
- --commit을 생략하면 DB 변경 없이 검증합니다. 향후 여러 분기 파일도 가장 최신 분기만 선택합니다.
- 화면은 실제 저장된 period를 한국어로 변환해 '최신유동인구', '2026년 2분기'를 표시합니다. 원자료 단위·산출기준 미확인 안내는 유지합니다.
- Django 시스템 검사, 관련 테스트 6개, 실제 페이지 및 경계 API HTTP 200 확인. DB 분기 집계 결과 floating / 2026Q2 / 1,641건.
