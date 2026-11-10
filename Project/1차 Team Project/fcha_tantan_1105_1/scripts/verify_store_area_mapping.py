"""Validate Work artifacts against original files and live DB before atomic linking.

Run with --commit to apply; default is read-only. Requires Shapely 2.x.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / '.validation_deps'))
import numpy as np
import shapely
from shapely.geometry import shape
from shapely.strtree import STRtree


def check(value, message):
    if not value:
        raise ValueError(message)


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', action='store_true')
    args = parser.parse_args()
    bundle = BASE / 'data/review/seoul_store_area_mapping_20261103'
    original = BASE / 'data/review/seoul_public_stores_20261103'
    manifest = read_json(bundle / 'manifest.json')
    summary = read_json(bundle / 'store_area_summary.json')
    for group in ('inputs', 'outputs'):
        for entry in manifest[group]:
            name = entry['filename']
            check(Path(name).name == name, 'Unsafe manifest filename')
            path = (bundle / name if group == 'outputs' else
                    BASE / 'data/analysis/02_areas.json' if name == '02_areas.json' else original / name)
            check(hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], f'Hash mismatch: {path}')
            if name.endswith('.json') and entry['records'] is not None:
                obj = read_json(path)
                count = obj['areas'] if name == 'geometry_validation.json' else len(obj) if isinstance(obj, list) else 1
                check(count == entry['records'], f'Count: {name}')
    print('Input/output hashes verified', flush=True)
    conn = sqlite3.connect(BASE / 'db.sqlite3', timeout=60)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('BEGIN IMMEDIATE' if args.commit else 'BEGIN')
        areas = read_json(BASE / 'data/analysis/02_areas.json')
        db_areas = {r['id']: dict(r) for r in conn.execute('SELECT * FROM market_commercialarea')}
        geometries, area_ids = [], []
        for record in areas:
            fields = record['fields']
            db = db_areas[fields['id']]
            for key, value in fields.items():
                if key in db:
                    actual = json.loads(db[key]) if key == 'boundary' else db[key]
                    check(actual == value, f'Area differs: {fields["id"]}/{key}')
            check(fields['version'] == 'project-preview-20261103' and not fields['verified'] and fields['effective_on'] is None, 'Boundary metadata')
            geometry = shape(fields['boundary'])
            check(geometry.is_valid and not geometry.is_empty, 'Invalid geometry')
            geometries.append(geometry)
            area_ids.append(fields['id'])
        check(len(areas) == 1643 and len(set(area_ids)) == 1643, 'Area count/duplicates')
        tree = STRtree(geometries)
        stores = {str(r['id']): dict(r) for r in conn.execute('SELECT id,source_id,external_id,latitude,longitude,reference_on,area_id FROM market_publicstore WHERE source_id=3')}
        check(len(stores) == 554092, 'DB store count')
        seen_original = set()
        for entry in manifest['inputs']:
            if not entry['filename'].startswith('07_public_stores_'):
                continue
            for record in read_json(original / entry['filename']):
                f = record['fields']
                sid = str(f['id'])
                check(sid not in seen_original, 'Original duplicate')
                seen_original.add(sid)
                db = stores[sid]
                for key in ('source_id', 'external_id', 'latitude', 'longitude', 'reference_on'):
                    check(str(db[key]) == str(f[key]), f'Store differs: {sid}/{key}')
        check(seen_original == set(stores), 'Original/DB coverage')
        with (bundle / 'store_area_mapping.csv').open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        mapping = {r['public_store_id']: r for r in rows}
        check(len(mapping) == len(rows) == len(stores) and set(mapping) == set(stores), 'CSV coverage/duplicates')
        counts, per_area, expected_reviews, updates = Counter(), Counter(), {}, []
        for offset in range(0, len(rows), 10000):
            batch = rows[offset:offset + 10000]
            points = shapely.points([[float(stores[r['public_store_id']]['longitude']), float(stores[r['public_store_id']]['latitude'])] for r in batch])
            check(bool(np.all(shapely.is_valid(points))), 'Invalid point')
            interiors, touches = {}, {}
            for predicate, target in [('within', interiors), ('touches', touches)]:
                pairs = tree.query(points, predicate=predicate)
                for point_index, area_index in pairs.T:
                    target.setdefault(int(point_index), []).append(area_ids[int(area_index)])
            for index, row in enumerate(batch):
                sid = row['public_store_id']
                db = stores[sid]
                inside, boundary = sorted(interiors.get(index, [])), sorted(touches.get(index, []))
                status = 'boundary' if boundary else 'overlap' if len(inside) > 1 else 'matched' if inside else 'outside'
                aid = inside[0] if status == 'matched' else None
                check(row['source_id'] == str(db['source_id']) and row['external_id'] == db['external_id'], f'Identity: {sid}')
                check(row['status'] == status and row['area_id'] == (str(aid) if aid else ''), f'Spatial mismatch: {sid}')
                check(db['area_id'] is None or db['area_id'] == aid, f'Existing mapping conflict: {sid}')
                counts[status] += 1
                if aid:
                    per_area[str(aid)] += 1
                    updates.append((int(sid), aid))
                else:
                    expected_reviews[sid] = (status, inside, boundary)
            if offset % 100000 == 0:
                print(f'Spatial verified: {offset + len(batch):,}', flush=True)
        with (bundle / 'store_area_review.csv').open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                status, inside, boundary = expected_reviews.pop(row['public_store_id'])
                reason = json.loads(row['reason'])
                check(row['status'] == status and sorted(json.loads(row['candidate_area_ids'])) == sorted(set(inside + boundary)), 'Review candidates')
                check(sorted(reason['interior_area_ids']) == inside and sorted(reason['boundary_area_ids']) == boundary, 'Review reason')
        check(not expected_reviews, 'Missing reviews')
        check(all(counts[k] == v for k, v in summary['status_counts'].items()), 'Status totals')
        check(all(per_area[k] == v for k, v in summary['matched_by_area_id'].items()), 'Area totals')
        check(sum(counts.values()) == summary['total_input'] == summary['total_processed'] == 554092, 'Total')
        if args.commit:
            conn.execute('CREATE TEMP TABLE verified_area_links (id INTEGER PRIMARY KEY, area_id INTEGER NOT NULL)')
            conn.executemany('INSERT INTO verified_area_links VALUES (?,?)', updates)
            conn.execute('UPDATE market_publicstore SET area_id=(SELECT area_id FROM verified_area_links WHERE id=market_publicstore.id) WHERE id IN (SELECT id FROM verified_area_links) AND area_id IS NULL')
            actual = Counter({str(r[0]): r[1] for r in conn.execute('SELECT area_id, count(*) FROM market_publicstore WHERE source_id=3 AND area_id IS NOT NULL GROUP BY area_id')})
            check(actual == per_area, 'Post-update grouped totals')
            conn.commit()
        else:
            conn.rollback()
        report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'committed': args.commit,
                  'stores_verified': len(stores), 'areas_verified': len(areas), 'status_counts': dict(counts),
                  'linked': sum(per_area.values()) if args.commit else None,
                  'mapping_sha256': hashlib.sha256((bundle / 'store_area_mapping.csv').read_bytes()).hexdigest(),
                  'shapely': shapely.__version__, 'geos': shapely.geos_version_string,
                  'scope': 'Project preview; CRS equivalence assumed, no buffer or coordinate correction'}
        path = BASE / 'data/reports/store_area_local_verification.json'
        path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report), flush=True)
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
