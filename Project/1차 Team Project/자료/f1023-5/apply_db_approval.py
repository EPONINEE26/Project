"""프차탄탄 승인 목록의 승인 항목만 DB에 반영.
기본 실행은 검증 전용. 실제 반영: python apply_db_approval.py --apply-db
승인 전에 원자료 확인 필수. 반영 시 DB 백업 후 단일 트랜잭션 사용.
"""
import argparse
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parent
DB = BASE/'db.sqlite3'
APPROVAL = BASE/'output'/'DB_승인목록.json'
JSON = BASE/'output'/'priority_brands_updated.json'
TARGET = BASE/'target_ids.json'
ALLOWED = {
    'brand': {'name': 'name', 'category': 'category'},
    'annual': {x:x for x in ('stores','direct_stores','total_stores','opened','closed','annual_sales_krw')},
    'regional': {'stores':'stores'},
    'area_sales': {'annual_sales_per_pyeong_krw':'annual_sales_per_pyeong_krw'},
    'startup_cost': {x:'amount_krw' for x in ('franchise_fee_krw','education_fee_krw','guarantee_deposit_krw','other_cost_krw')},
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply-db', action='store_true', help='승인된 변경만 실제 DB에 적용')
    args = parser.parse_args()
    for path in (DB, APPROVAL, JSON, TARGET):
        if not path.is_file(): raise SystemExit(f'필수 파일 없음: {path}')
    approval = json.loads(APPROVAL.read_text(encoding='utf-8-sig'))
    items = approval['items']
    target_ids = set(json.loads(TARGET.read_text(encoding='utf-8-sig')))
    source = json.loads(JSON.read_text(encoding='utf-8-sig'))
    indexed = {b['id']:b for b in source if b['id'] in target_ids}
    if len(target_ids)!=19 or len(source)!=1821 or set(indexed)!=target_ids:
        raise SystemExit('대상 브랜드 또는 JSON 개수 불일치: 중단')
    if Path(approval.get('source_json','')).name != JSON.name or Path(approval.get('source_db','')).name != DB.name:
        raise SystemExit('승인 목록의 원본 파일 정보 불일치')
    selected = [d for d in items if d['결정']=='승인']
    if any(d['결정'] not in ('보류','승인','DB 유지') for d in items):
        raise SystemExit('허용되지 않는 결정값')
    if not selected:
        print('승인 0건: DB 변경 없음. DB_승인목록.json에서 검증한 항목만 승인하세요.')
        return
    for d in selected:
        if not d.get('검증근거','').strip(): raise SystemExit(f"검증근거 누락: {d['번호']}번")
        if d.get('status')!='변경 필요' or d.get('brand_id') not in target_ids:
            raise SystemExit(f"지원하지 않는 항목: {d['번호']}번")
        if d.get('field') not in ALLOWED.get(d.get('section'),{}):
            raise SystemExit(f"허용되지 않는 필드: {d['번호']}번")
        if d.get('section') not in ('brand','annual','regional','area_sales','startup_cost'):
            raise SystemExit(f"지원하지 않는 섹션: {d['번호']}번")
        if d['section'] != 'brand' and d.get('year') not in (2024,2025):
            raise SystemExit(f"연도 오류: {d['번호']}번")
        if d['section']=='regional' and not d.get('region'):
            raise SystemExit(f"지역 누락: {d['번호']}번")
        b = indexed[d['brand_id']]
        h = next((h for h in b.get('history',[]) if h.get('year')==d.get('year')), None)
        section, field = d['section'], d['field']
        if section=='brand': actual = b.get(field)
        elif h is None: raise SystemExit(f"JSON 연도 누락: {d['번호']}번")
        elif section=='annual': actual=h.get(field)
        elif section=='regional': actual=h.get('regions',{}).get(d['region'],{}).get('stores')
        elif section=='area_sales': actual=h.get('annual_sales_per_3_3sqm_krw')
        else: actual=(h.get('startup_cost_breakdown') or {}).get(field)
        if actual != d['json_value']:
            raise SystemExit(f"JSON이 비교 당시와 다릅니다: {d['번호']}번")
        if section not in ('brand',) and actual is not None and (isinstance(actual,bool) or not isinstance(actual,int) or actual<0):
            raise SystemExit(f"수치 타입 오류: {d['번호']}번")
    conn = sqlite3.connect(f'file:{DB.as_posix()}?mode={"rw" if args.apply_db else "ro"}', uri=True)
    conn.row_factory = sqlite3.Row
    planned=[]
    try:
        for d in selected:
            slug,year,section,field=d['brand_id'],d.get('year'),d['section'],d['field']
            brand=conn.execute('SELECT id,category,is_demo FROM brands_brand WHERE slug=?',(slug,)).fetchone()
            if brand is None or brand['is_demo']:
                raise SystemExit(f"DB 브랜드 없음/데모: {slug}")
            if section=='brand':
                table='brands_brand'; col=field; row_id=brand['id']
            elif section=='startup_cost':
                table='brands_startupcost'; col='amount_krw'
                row=conn.execute('''SELECT sc.id FROM brands_startupcost sc JOIN brands_costitem ci ON ci.id=sc.item_id
                  WHERE sc.brand_id=? AND sc.year=? AND ci.category=? AND ci.code=?''',
                  (brand['id'],year,brand['category'],field)).fetchone()
                row_id=row['id'] if row else None
            else:
                stat=conn.execute('SELECT id FROM brands_annualstat WHERE brand_id=? AND year=?',(brand['id'],year)).fetchone()
                if stat is None: raise SystemExit(f"연도 통계 없음: {slug} {year}")
                if section=='annual': table='brands_annualstat';col=field;row_id=stat['id']
                elif section=='regional':
                    table='brands_regionalstat';col='stores'
                    row=conn.execute('SELECT id FROM brands_regionalstat WHERE annual_stat_id=? AND region=?',(stat['id'],d['region'])).fetchone()
                    row_id=row['id'] if row else None
                else:
                    table='brands_areasales';col='annual_sales_per_pyeong_krw'
                    row=conn.execute('SELECT id FROM brands_areasales WHERE annual_stat_id=?',(stat['id'],)).fetchone()
                    row_id=row['id'] if row else None
            if row_id is None: raise SystemExit(f"DB 레코드 없음: {d['번호']}번")
            old=conn.execute(f'SELECT {col} FROM {table} WHERE id=?',(row_id,)).fetchone()[0]
            if old != d['db_value']:
                raise SystemExit(f"DB 값이 비교 당시와 다릅니다: {d['번호']}번 (현재 {old!r})")
            planned.append((d,table,col,row_id))
        print(f'검증 완료: 승인 {len(planned)}건 / 보류·DB 유지 {len(items)-len(planned)}건')
        if not args.apply_db:
            print('미리보기 모드: DB 변경 없음. 실제 적용은 --apply-db')
            return
        # SQLite 온라인 백업으로 일관된 DB 스냅샷 생성
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=BASE/'output'/f'db_backup_before_approval_{stamp}.sqlite3'
        backup.parent.mkdir(exist_ok=True)
        with sqlite3.connect(backup) as dst: conn.backup(dst)
        print('DB 백업:',backup)
        try:
            conn.execute('BEGIN IMMEDIATE')
            # 잠금 획득 후 재확인 (동시 수정 방지)
            for d,table,col,row_id in planned:
                old=conn.execute(f'SELECT {col} FROM {table} WHERE id=?',(row_id,)).fetchone()[0]
                if old!=d['db_value']: raise RuntimeError(f"DB 값 변경 감지: {d['번호']}번")
                conn.execute(f'UPDATE {table} SET {col}=? WHERE id=?',(d['json_value'],row_id))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        print(f'승인 {len(planned)}건 적용 완료. 재비교: python compare_json_db.py')
    finally:
        conn.close()
if __name__=='__main__':main()
