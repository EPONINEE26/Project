from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from .analysis_models import PopulationStat


class ResidentPopulationImportTests(TestCase):
    def setUp(self):
        from .test_worker_population import WorkerPopulationImportTests
        WorkerPopulationImportTests.setUp(self)
        self.row = {key.replace('직장_인구', '상주인구'): value for key, value in self.row.items()}
        self.row['총_가구_수'] = '25'

    def test_latest_dry_run_upsert_and_card(self):
        from .analysis import population_card
        self.run_import([self.row])
        self.assertFalse(PopulationStat.objects.exists())
        self.run_import([self.row], commit=True)
        self.run_import([self.row], commit=True)
        stat = PopulationStat.objects.get()
        self.assertEqual((stat.kind, stat.period, stat.total, stat.households), ('resident', '2026Q2', 60, 25))
        self.assertIsNone(stat.single_households)
        self.assertEqual(stat.by_gender, {'남성': 30, '여성': 30})
        self.assertEqual(len(population_card({'stat': stat})['breakdowns'][0]['items']), 6)

    def test_invalid_or_duplicate_rows_do_not_write(self):
        from django.core.management.base import CommandError
        for rows in [[self.row, self.row], [dict(self.row, 총_상주인구_수='-1')]]:
            with self.assertRaises(CommandError):
                self.run_import(rows, commit=True)
        self.assertFalse(PopulationStat.objects.exists())

    def run_import(self, rows, commit=False):
        import csv
        import tempfile
        from pathlib import Path
        from django.test import override_settings
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/analysis').mkdir(parents=True)
            path = base / 'resident.csv'
            with path.open('w', encoding='cp949', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=self.row)
                writer.writeheader()
                writer.writerows(rows)
            with override_settings(BASE_DIR=base):
                call_command('import_resident_population', str(path), commit=commit, stdout=StringIO())
