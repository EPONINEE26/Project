"""읽기 전용 비교 보고서에서 승인 목록을 생성. 기존 승인 목록은 덮어쓰지 않음."""
import json
from pathlib import Path
BASE = Path(__file__).resolve().parent
src = BASE/'output'/'DB_변경검토.json'
out = BASE/'output'/'DB_승인목록.json'
report = json.loads(src.read_text(encoding='utf-8-sig'))
if out.exists():
    raise SystemExit(f'기존 승인 목록 보호: {out} (덮어쓰지 않음)')
if report.get('mode') != 'READ_ONLY' or report.get('target_brands') != 19:
    raise SystemExit('예상하지 못한 비교 보고서입니다.')
items = []
for n, d in enumerate(report['differences'], 1):
    items.append({'번호':n, '결정':'보류', '검증근거':'', **d})
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps({'설명':'결정: 보류 / 승인 / DB 유지. 승인 전 검증근거 기입. JSON과 DB 수치 검증 필수.',
                           'source_json':report['json_file'], 'source_db':report['db_file'],
                           'items':items}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'승인 목록 생성: {out} / {len(items)}건 / 전체 보류')
print('DB는 수정하지 않았습니다.')
