프차탄탄 업종별 엑셀 → JSON 관리도구 (실제 브랜드 19개)

구성
- excel/카페.xlsx, 치킨.xlsx, 편의점.xlsx, 미용실.xlsx
- priority_brands.json : 전체 1,821개 브랜드의 변경하지 않은 원본
- excel_to_json.py : 엑셀을 검사하고 수정된 필드만 JSON에 반영하는 변환 도구
- schema.json, target_ids.json : 변환 규칙 및 허용된 브랜드 ID
- output/변경검토.json : 변경 및 오류 검토 보고서

사용 순서 (Windows PowerShell)
1. 이 압축파일을 압축 해제하고 폴더로 이동
2. python -m pip install openpyxl
3. 업종별 엑셀의 기존 행에 누락된 수치를 채우거나 기존 수치를 수정하고 저장
4. python excel_to_json.py
   → 변경검토.json에서 변경된 값과 오류 확인 (JSON 미생성)
5. python excel_to_json.py --apply-json
   → output/priority_brands_updated.json 생성
6. 새 JSON을 검토한 뒤 별도 Django DB 반영 절차 진행
   ※ 이 도구는 Django DB를 읽거나 쓰지 않습니다.
   ※ 사이트는 DB를 읽으므로 JSON 생성만으로 사이트 화면이 변경되지 않습니다.

편집 규칙
- 빈칸: 기존 원본 값이 있으면 유지, 원본 NULL이면 NULL 유지
- 빈칸에 새 수치를 채우면 새 값으로 반영
- 기존 값을 NULL로 바꾸려면 __NULL__ 이라고 입력
- 0은 실제 숫자 0으로 반영
- brand_id, id, year, region 등 키 필드와 헤더 및 행 수 변경 금지
- 원본 JSON의 19개 대상 이외 브랜드 1,802개와 엑셀에 노출되지 않은 필드는 유지
- 원본 파일은 덮어쓰지 않으며 결과는 output 폴더에 별도 생성
- 월세, 인건비, 운영비는 브랜드 공통 수집 대상에서 제외 (회원 직접 입력)

주의
- 출처 및 값 검증은 팀원이 수행해야 합니다.
- Excel 수식은 저장된 계산 결과를 읽으므로 입력 셀은 값으로 작성하는 것이 안전합니다.
- 연도별통계의 원본에 있는 quality_flags, source_ids 등 복합 필드는 그대로 보존됩니다.
