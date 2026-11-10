import csv
import tempfile
from io import StringIO
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from .analysis import population_card
from .analysis_models import CommercialArea, DataSource, PopulationStat


class WorkerPopulationImportTests(TestCase):
    def setUp(self):
        source = DataSource.objects.create(name='경계', collected_on='2026-11-04')
        self.area = CommercialArea.objects.create(code='123', version='test', name='상권', area_type='골목상권', admin_code='11', source=source)
        self.row = {'기준_년분기_코드': '20262', '상권_코드': '123', '상권_코드_명': '상권', '상권_구분_코드_명': '골목상권', '총_직장_인구_수': '60', '남성_직장_인구_수': '30', '여성_직장_인구_수': '30'}
        for age in [10, 20, 30, 40, 50, 60]:
            self.row[f'연령대_{age}{"_이상" if age == 60 else ""}_직장_인구_수'] = '10'

    def run_import(self, rows, commit=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'worker.csv'
            with path.open('w', encoding='cp949', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=self.row)
                writer.writeheader()
                writer.writerows(rows)
            call_command('import_worker_population', str(path), commit=commit, stdout=StringIO())

    def test_latest_dry_run_upsert_and_card(self):
        older = dict(self.row, 기준_년분기_코드='20261')
        self.run_import([older, self.row])
        self.assertFalse(PopulationStat.objects.exists())
        self.run_import([older, self.row], commit=True)
        self.run_import([older, self.row], commit=True)
        stat = PopulationStat.objects.get()
        self.assertEqual((stat.period, stat.kind, stat.total, stat.unit), ('2026Q2', 'worker', 60, '명'))
        self.assertEqual(stat.by_age['60대 이상'], 10)
        card = population_card({'label': '직장인구', 'stat': stat})
        self.assertEqual(card['period_label'], '2026년 2분기')
        self.assertEqual(len(card['breakdowns'][0]['items']), 6)

    def test_invalid_or_duplicate_rows_do_not_write(self):
        for rows in [[self.row, self.row], [dict(self.row, 총_직장_인구_수='-1')]]:
            with self.assertRaises(CommandError):
                self.run_import(rows, commit=True)
        self.assertFalse(PopulationStat.objects.exists())

    def test_area_import_preserves_gender_difference_and_exports(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/analysis').mkdir(parents=True)
            for name in ['01_sources.json', '04_population.json']:
                (base / 'data/analysis' / name).write_text('[]', encoding='utf-8')
            floating = {key.replace('직장_인구_수', '유동인구_수'): value for key, value in self.row.items()}
            floating['여성_유동인구_수'] = '31'
            for day in '월화수목금토일':
                floating[f'{day}요일_유동인구_수'] = '10'
            for start, end in [('00','06'),('06','11'),('11','14'),('14','17'),('17','21'),('21','24')]:
                floating[f'시간대_{start}_{end}_유동인구_수'] = '10'
            for name, row in [('worker',self.row), ('floating',floating)]:
                with (base / f'{name}.csv').open('w', encoding='cp949', newline='') as handle:
                    writer = csv.DictWriter(handle, fieldnames=row)
                    writer.writeheader()
                    writer.writerow(row)
            with override_settings(BASE_DIR=base):
                arguments = dict(worker=base/'worker.csv', floating=base/'floating.csv', stdout=StringIO())
                call_command('import_area_population', '123', **arguments)
                self.assertFalse(PopulationStat.objects.exists())
                for _ in range(2):
                    call_command('import_area_population', '123', commit=True, **arguments)
            self.assertEqual(PopulationStat.objects.count(), 2)
            stat = PopulationStat.objects.get(kind='floating')
            self.assertEqual(stat.total, 60)
            self.assertEqual(stat.by_gender, {'남성':30, '여성':31})
            self.assertEqual(len(stat.by_time), 6)
            card = population_card({'label':'유동인구','stat':stat})
            self.assertEqual(card['breakdowns'][1]['items'][1]['value'],31)
            exported = json.loads((base/'data/analysis/04_population.json').read_text(encoding='utf-8'))
            self.assertEqual(len(exported),2)
