import csv
import tempfile
from pathlib import Path
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from market.analysis_models import DistrictPopulationStat


class DistrictPopulationImportTests(TestCase):
    def test_district_lookup_and_template(self):
        from types import SimpleNamespace
        from django.template.loader import render_to_string
        from market.analysis import district_population_card
        from market.analysis_models import DataSource
        source = DataSource.objects.create(name='district source', collected_on='2026-11-04')
        for period, total in [('2026Q1', 100), ('2026Q2', 200)]:
            DistrictPopulationStat.objects.create(district_code='11140', district_name='중구',
                period=period, total=total, source=source, by_age={'20대': 200},
                by_gender={'남성': 100, '여성': 100}, by_time={'0~6시': 200},
                by_day={day: 1 for day in '월화수목금토일'})
        area = SimpleNamespace(admin_code='11140590', name='장충동주민센터')
        card = district_population_card(area)
        self.assertEqual(card['stat'].total, 200)
        html = render_to_string('includes/district_population.html', {'district_card': card, 'analysis_area': area})
        self.assertIn('중구 유동인구', html)
        self.assertIn('2026년 2분기', html)
        self.assertIn('성별 원자료', html)
        self.assertIsNone(district_population_card(None)['stat'])
        self.assertIsNone(district_population_card(SimpleNamespace(admin_code='11740000'))['stat'])

    def test_import_validation_and_repeat(self):
        row = {'기준_년분기_코드':'20262', '자치구_코드':'11740', '자치구_코드_명':'강동구'}
        columns = ['총 유동','남성 유동','여성 유동']
        columns += [f'{age}대 유동' for age in [10,20,30,40,50,60]]
        columns += ['0~6시','6~11시','11~14시','14~17시','17~21','21~24']
        columns += [day+' 유동' for day in '월화수목금토일']
        row.update({column:'1,234' for column in columns})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'district.csv'
            def write(rows):
                with path.open('w',encoding='cp949',newline='') as handle:
                    writer=csv.DictWriter(handle,fieldnames=row)
                    writer.writeheader()
                    writer.writerows(rows)
            write([row])
            call_command('import_district_population', str(path))
            self.assertEqual(DistrictPopulationStat.objects.count(),0)
            for _ in range(2):
                call_command('import_district_population',str(path),commit=True)
            self.assertEqual(DistrictPopulationStat.objects.count(),1)
            obj=DistrictPopulationStat.objects.get()
            self.assertEqual(obj.total,1234)
            self.assertEqual(obj.raw,row)
            self.assertEqual(obj.by_time['17~21시'],1234)
            write([row,row])
            with self.assertRaises(CommandError):
                call_command('import_district_population',str(path),commit=True)
            self.assertEqual(DistrictPopulationStat.objects.count(),1)
