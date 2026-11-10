import json
import tempfile
from pathlib import Path
from io import StringIO
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from .analysis_models import DataSource, PublicStore, CommercialArea, PopulationStat

class ImportAnalysisTests(TestCase):
    def test_numeric_geometry_and_distribution_survive_import(self):
        rows = [
            {'model': 'DataSource', 'fields': {'id': 100, 'name': 'preview', 'collected_on': '2026-11-03'}},
            {'model': 'CommercialArea', 'fields': {
                'id': 100, 'source_id': 100, 'code': 'sample', 'name': 'sample',
                'version': 'project-preview-20261103', 'effective_on': None,
                'area_type': 'test', 'admin_code': 'test', 'verified': False,
                'boundary': {'type': 'Polygon', 'coordinates': [[[127.0, 37.0], [127.1, 37.0], [127.1, 37.1], [127.0, 37.0]]]},
            }},
            {'model': 'PopulationStat', 'fields': {
                'area_id': 100, 'source_id': 100, 'period': '2026Q2',
                'unit': '원자료 수치', 'kind': 'floating', 'total': 100,
                'by_age': {'20대': 12.5},
            }},
        ]
        self.run_import(rows, commit=True)
        area = CommercialArea.objects.get()
        self.assertIsInstance(area.boundary['coordinates'][0][0][0], float)
        self.assertEqual(PopulationStat.objects.get().by_age['20대'], 12.5)
        self.assertIsNone(area.effective_on)
        self.assertFalse(area.verified)

    def run_import(self,rows,commit=False):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'input.json';p.write_text(json.dumps(rows),encoding='utf-8')
            call_command('import_analysis',str(p),commit=commit,stdout=StringIO())
    def test_dry_run_and_atomic_failure(self):
        row={'model':'DataSource','fields':{'id':100,'name':'test','collected_on':'2026-01-01'}}
        self.run_import([row]);self.assertFalse(DataSource.objects.exists())
        with self.assertRaises(CommandError):self.run_import([row,{'model':'Unknown','fields':{}}],commit=True)
        self.assertFalse(DataSource.objects.exists())
    def test_public_store_exact_coordinate_and_string_postcode(self):
        rows=[{'model':'DataSource','fields':{'id':100,'name':'test','collected_on':'2026-01-01'}},{'model':'PublicStore','fields':{'source_id':100,'external_id':'sample','name':'sample','address':'test','postcode':'04778','latitude':'37.123456789012345','longitude':'127.123456789012345','reference_on':'2026-01-01','raw':{'postcode':'04778'}}}]
        self.run_import(rows,commit=True)
        row=PublicStore.objects.get();self.assertEqual(str(row.latitude).rstrip('0'),'37.123456789012345');self.assertEqual(row.postcode,'04778')
    def test_excess_coordinate_precision_is_rejected(self):
        rows=[{'model':'DataSource','fields':{'id':100,'name':'test','collected_on':'2026-01-01'}},{'model':'PublicStore','fields':{'source_id':100,'external_id':'sample','name':'sample','address':'test','latitude':'37.123456789012345678901234567','longitude':'127','reference_on':'2026-01-01'}}]
        with self.assertRaises(CommandError):self.run_import(rows,commit=True)
        self.assertFalse(PublicStore.objects.exists());self.assertFalse(DataSource.objects.exists())
