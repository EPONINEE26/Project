"""검토 경계와 원본 인구를 연결해 세미 프로젝트 미리보기 자료를 생성합니다."""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from openpyxl import load_workbook

BASE = Path(__file__).resolve().parents[1]
REVIEW = BASE / 'data/review/seoul_analysis_partial_20261103'
OUT = BASE / 'data/analysis'
VERSION = 'project-preview-20261103'


def read_rows(path):
    book = load_workbook(path, read_only=True, data_only=True)
    rows = book.active.values
    headers = next(rows)
    result = [dict(zip(headers, row)) for row in rows]
    book.close()
    return result


def norm(value):
    return re.sub(r'\s+', '', str(value or ''))


def main():
    geometry_path = BASE.parent / 'fdata/seoul_commercial_areas.xlsx'
    population_path = next((BASE / 'data').glob('*길단위*.xlsx'))
    # 검토 당시 도형 검사와 동일한 원본인지 확인합니다.
    expected = {
        geometry_path: 'be6adaa9feaeca2957ebce2cdc71d9da47aa0eb40186a53dca3ae1ef6ecb0253',
        population_path: '53fd72f418357330f7b34b80a28b3a7665f6324981060a7d7af7dbd8e7b6d1a2',
    }
    for path, digest in expected.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f'검토 원본과 다릅니다: {path}')
    areas = json.loads((REVIEW / 'review_only_DO_NOT_IMPORT/02_areas.json').read_text(encoding='utf-8'))
    index = defaultdict(list)
    for row in areas:
        fields = row['fields']
        fields.update(version=VERSION, effective_on=None, verified=False)
        index[(norm(fields['name']), norm(fields['area_type']))].append(fields)
    original = {str(r['TRDAR_CD']): r for r in read_rows(geometry_path)}
    populations, audit = [], []
    seen = set()
    counts = Counter()
    for number, row in enumerate(read_rows(population_path), 2):
        matches = index.get((norm(row['상권_코드_명']), norm(row['상권구분'])), [])
        status = 'matched' if len(matches) == 1 else 'unmatched' if not matches else 'ambiguous'
        fields = matches[0] if len(matches) == 1 else None
        audit.append({
            'source_row': number, 'name': row['상권_코드_명'],
            'source_district': row['자치구'], 'source_dong': row['행정동'],
            'area_code': fields['code'] if fields else '',
            'boundary_district': original[fields['code']]['SIGNGU_CD_'] if fields else '',
            'boundary_dong': original[fields['code']]['ADSTRD_CD_'] if fields else '',
            'result': status,
        })
        counts[status] += 1
        if not fields:
            continue
        raw_period = str(row['분기'])
        if not re.fullmatch(r'20\d{2}[1-4]', raw_period):
            raise ValueError(f'분기 형식 오류: {number}')
        period = raw_period[:4] + 'Q' + raw_period[-1]
        key = (fields['id'], period)
        if key in seen:
            raise ValueError(f'인구 중복: {key}')
        seen.add(key)

        def number_value(value):
            if value is None:
                return None
            text = str(value).replace(',', '').strip()
            if not re.fullmatch(r'\d+', text):
                raise ValueError(f'비음수 정수 아님: 행 {number}, {value}')
            return int(text)

        populations.append({'model': 'PopulationStat', 'fields': {
            'area_id': fields['id'], 'source_id': 2, 'period': period,
            'unit': '원자료 수치', 'kind': 'floating', 'total': number_value(row['전체']),
            'households': None, 'single_households': None,
            'by_age': {k: number_value(row[k]) for k in ['10대', '20대', '30대', '40대', '50대', '60대']},
            'by_time': {k: number_value(row[k]) for k in ['0~6시', '6~11시', '11~14시', '14~17시', '17~21시', '21~24시']},
            'by_day': {k: number_value(row[k]) for k in ['월', '화', '수', '목', '금', '토', '일']},
        }})
    populations.sort(key=lambda r: (r['fields']['area_id'], r['fields']['period']))
    for pk, row in enumerate(populations, 1):
        row['fields']['id'] = pk
    sources = json.loads((REVIEW / '01_sources.json').read_text(encoding='utf-8'))
    sources[0]['fields']['note'] += '; 세미 프로젝트 미리보기: 경위도 형태 좌표를 변환 없이 사용. 공식 CRS 미확정. version은 로컬 자료 버전이며 effective_on은 미확인(null). verified=false 유지.'
    sources[1]['fields']['note'] += '; 세미 프로젝트 미리보기: 단위·평균/누계 미확인으로 원자료 수치 표시. 상권명+공식 상권유형의 유일 일치로 연결. 원본 자치구·행정동은 불일치 가능해 매칭 조건에서 제외하고 대응표에 보존.'
    for name, data in [('01_sources.json', sources), ('02_areas.json', areas), ('04_population.json', populations)]:
        (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    reports = BASE / 'data/reports'
    reports.mkdir(exist_ok=True)
    with (reports / 'seoul_population_mapping.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audit[0]))
        writer.writeheader()
        writer.writerows(audit)
    summary = {'areas': len(areas), 'population': len(populations), 'matching': dict(counts), 'covered_areas': len({r['fields']['area_id'] for r in populations})}
    (reports / 'seoul_preview_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == '__main__':
    main()
