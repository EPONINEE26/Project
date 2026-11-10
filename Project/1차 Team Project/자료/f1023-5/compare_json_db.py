"""프차탄탄: 19개 브랜드 JSON ↔ Django SQLite 읽기 전용 비교.
실행: python compare_json_db.py
DB와 원본 JSON은 절대 수정하지 않습니다.
"""
from pathlib import Path
import json
import sqlite3
from collections import Counter

BASE = Path(__file__).resolve().parent
JSON_PATH = BASE / 'output' / 'priority_brands_updated.json'
DB_PATH = BASE / 'db.sqlite3'
TARGET_PATH = BASE / 'target_ids.json'
REPORT_PATH = BASE / 'output' / 'DB_변경검토.json'

ANNUAL = ('stores', 'direct_stores', 'total_stores', 'opened', 'closed', 'annual_sales_krw')
BRAND = ('name', 'category')
COST = ('franchise_fee_krw', 'education_fee_krw', 'guarantee_deposit_krw', 'other_cost_krw')


def main():
    for path in (JSON_PATH, DB_PATH, TARGET_PATH):
        if not path.is_file():
            raise SystemExit(f'파일 없음: {path}')
    source = json.loads(JSON_PATH.read_text(encoding='utf-8-sig'))
    target_ids = set(json.loads(TARGET_PATH.read_text(encoding='utf-8-sig')))
    if len(target_ids) != 19 or len(source) != 1821:
        raise SystemExit(f'예상 데이터 개수 불일치: 대상 {len(target_ids)}, 전체 {len(source)} (비교 중단)')
    indexed = {b['id']: b for b in source if b['id'] in target_ids}
    if set(indexed) != target_ids:
        raise SystemExit(f'JSON 대상 브랜드 누락: {sorted(target_ids-set(indexed))}')
    con = sqlite3.connect(f'file:{DB_PATH.as_posix()}?mode=ro', uri=True)
    con.row_factory = sqlite3.Row
    differences = []
    checks = 0
    def compare(slug, year, section, field, jvalue, dvalue, region=None):
        nonlocal checks
        checks += 1
        if jvalue != dvalue:
            differences.append({'status': 'DB에 없음' if dvalue is None and jvalue is not None else 'JSON에 없음' if jvalue is None and dvalue is not None else '변경 필요',
                                'brand_id': slug, 'year': year, 'section': section, 'region': region,
                                'field': field, 'json_value': jvalue, 'db_value': dvalue})
    try:
        brands = {r['slug']: dict(r) for r in con.execute('SELECT id, slug, name, category, is_demo FROM brands_brand')}
        for slug in sorted(target_ids):
            b = indexed[slug]
            db = brands.get(slug)
            if not db:
                differences.append({'status':'DB에 없음', 'brand_id':slug, 'section':'brand', 'note':'브랜드 레코드 없음'})
                continue
            if db['is_demo']:
                differences.append({'status':'검증 오류', 'brand_id':slug, 'section':'brand', 'note':'대상 브랜드가 DB에서 데모로 표시됨'})
                continue
            for field in BRAND:
                compare(slug, None, 'brand', field, b.get(field), db[field])
            for hist in b.get('history', []):
                year = hist.get('year')
                if year not in (2024, 2025):
                    continue
                stat = con.execute('SELECT * FROM brands_annualstat WHERE brand_id=? AND year=?', (db['id'], year)).fetchone()
                if not stat:
                    differences.append({'status':'DB에 없음', 'brand_id':slug, 'year':year, 'section':'annual', 'note':'연도별 통계 레코드 없음'})
                    continue
                for field in ANNUAL:
                    compare(slug, year, 'annual', field, hist.get(field), stat[field])
                for region, values in hist.get('regions', {}).items():
                    row = con.execute('SELECT stores FROM brands_regionalstat WHERE annual_stat_id=? AND region=?', (stat['id'], region)).fetchone()
                    if row is None:
                        differences.append({'status':'DB에 없음', 'brand_id':slug, 'year':year, 'section':'regional', 'region':region, 'note':'지역 레코드 없음'})
                    else:
                        compare(slug, year, 'regional', 'stores', values.get('stores'), row['stores'], region)
                area = con.execute('SELECT annual_sales_per_pyeong_krw FROM brands_areasales WHERE annual_stat_id=?', (stat['id'],)).fetchone()
                # JSON 원본의 3.3㎡당 연매출과 DB의 평당 연매출은 단위가 같은 경우만 비교
                area_value = hist.get('annual_sales_per_3_3sqm_krw')
                if area is not None:
                    compare(slug, year, 'area_sales', 'annual_sales_per_pyeong_krw', area_value, area['annual_sales_per_pyeong_krw'])
                breakdown = hist.get('startup_cost_breakdown') or {}
                for code in COST:
                    cost = con.execute('''SELECT sc.amount_krw FROM brands_startupcost sc
                        JOIN brands_costitem ci ON ci.id=sc.item_id
                        WHERE sc.brand_id=? AND sc.year=? AND ci.category=? AND ci.code=?''',
                        (db['id'], year, b['category'], code)).fetchone()
                    if cost is None:
                        differences.append({'status':'DB에 없음', 'brand_id':slug, 'year':year, 'section':'startup_cost', 'field':code, 'note':'비용 레코드 없음'})
                    else:
                        compare(slug, year, 'startup_cost', code, breakdown.get(code), cost['amount_krw'])
    finally:
        con.close()
    counts = Counter(d['status'] for d in differences)
    report = {'mode':'READ_ONLY', 'json_file':str(JSON_PATH), 'db_file':str(DB_PATH),
              'target_brands':len(target_ids), 'checked_fields':checks,
              'differences_count':len(differences), 'status_counts':dict(counts), 'differences':differences,
              'notes':['비교 전용: DB 변경 없음', 'DB에 없는 JSON 필드는 비교 대상에서 제외',
                       '연도별 통계는 2024/2025년만 비교', '출처·검증 상태는 별도 검증 필요']}
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'읽기 전용 비교 완료: 브랜드 {len(target_ids)}개 / 필드 비교 {checks}건 / 차이 {len(differences)}건')
    print('상태별:', dict(counts))
    print('결과:', REPORT_PATH)
    print('DB는 수정하지 않았습니다.')

if __name__ == '__main__':
    main()
