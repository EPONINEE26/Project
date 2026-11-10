"""준비된 서울 JSON을 전체 검증하고 하나의 트랜잭션으로 최초 적재합니다."""
import json
import os
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()

from django.core.management import call_command
from market.analysis_models import DataSource, CommercialArea, PopulationStat


def main():
    if any(model.objects.exists() for model in (DataSource, CommercialArea, PopulationStat)):
        raise SystemExit('최초 적재 전용입니다. 기존 분석 데이터가 있어 중단합니다.')
    records = []
    for name in ['01_sources.json', '02_areas.json', '04_population.json']:
        records.extend(json.loads((BASE / 'data/analysis' / name).read_text(encoding='utf-8')))
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'seoul_combined.json'
        path.write_text(json.dumps(records, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        call_command('import_analysis', str(path), commit=True)


if __name__ == '__main__':
    main()
