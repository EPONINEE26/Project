"""Work 분할 산출물을 해시·참조·필드 검증 후 원자적으로 최초 적재합니다."""
import hashlib
import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from market.analysis_models import DataSource, IndustryCode, PublicStore


class Command(BaseCommand):
    help = '공공 매장 분할 자료 최초 적재. 기본 검증 전용, --commit으로 저장.'

    def add_arguments(self, parser):
        parser.add_argument('directory')
        parser.add_argument('--original', required=True)
        parser.add_argument('--commit', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            self.load(options)
        except (ValueError, KeyError, TypeError, OSError, ValidationError) as error:
            raise CommandError(str(error)) from error

    def load(self, options):
        directory = Path(options['directory']).resolve()
        manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf-8-sig'))
        if PublicStore.objects.exists() or IndustryCode.objects.exists():
            raise ValueError('최초 적재 전용: 업종 또는 공공 매장 데이터가 이미 있습니다.')
        if DataSource.objects.filter(pk=manifest['source_id']).exists():
            raise ValueError('출처 ID가 기존 DB와 충돌합니다.')
        original = Path(options['original'])
        def digest(path):
            result = hashlib.sha256()
            with path.open('rb') as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b''):
                    result.update(block)
            return result.hexdigest()
        if digest(original) != manifest['original_sha256']:
            raise ValueError('가공에 사용한 원본과 로컬 CSV의 해시가 다릅니다.')
        files = {row['filename']: row for row in manifest['files']}
        order = manifest['process_order']
        if len(order) != len(set(order)) or len(order) < 3:
            raise ValueError('분할 파일 순서가 올바르지 않습니다.')
        paths = []
        for name in order:
            path = (directory / name).resolve()
            if path.parent != directory or not path.is_file():
                raise ValueError('잘못된 파일 경로: ' + name)
            if digest(path) != files[name]['sha256']:
                raise ValueError('파일 해시 불일치: ' + name)
            paths.append(path)
        self.stdout.write(f'원본 및 {len(paths)}개 적재 파일 해시 확인 완료', ending='\n')

        def records(path, model):
            rows = json.loads(path.read_text(encoding='utf-8-sig'))
            if not isinstance(rows, list) or len(rows) != files[path.name]['records']:
                raise ValueError('건수 또는 배열 형식 오류: ' + path.name)
            allowed = {field.attname for field in model._meta.fields}
            for row in rows:
                if set(row) != {'model', 'fields'} or row['model'] != model.__name__:
                    raise ValueError('모델 형식 오류: ' + path.name)
                if set(row['fields']) - allowed:
                    raise ValueError('허용되지 않은 필드: ' + path.name)
            return rows

        sources = records(paths[0], DataSource)
        if len(sources) != 1 or sources[0]['fields']['id'] != manifest['source_id']:
            raise ValueError('출처 참조 불일치')
        source = DataSource(**sources[0]['fields'])
        source.full_clean()
        source.save(force_insert=True)
        industries = []
        keys = set()
        for row in records(paths[1], IndustryCode):
            obj = IndustryCode(**row['fields'])
            obj.full_clean()
            key = (obj.system, obj.code)
            if key in keys:
                raise ValueError('업종 코드 중복')
            keys.add(key)
            industries.append(obj)
        if len({obj.pk for obj in industries}) != len(industries):
            raise ValueError('업종 ID 중복')
        if len(industries) != manifest['industry_count']:
            raise ValueError('업종 건수 불일치')
        IndustryCode.objects.bulk_create(industries)
        industry_ids = {obj.pk for obj in industries}
        external_ids = set()
        total = 0
        for path in paths[2:]:
            objects = []
            for row in records(path, PublicStore):
                obj = PublicStore(**row['fields'])
                if obj.pk != total + 1:
                    raise ValueError('매장 ID 순서 또는 중복 오류')
                if obj.source_id != source.pk or obj.industry_id not in industry_ids | {None}:
                    raise ValueError('출처 또는 업종 참조 오류')
                if obj.brand_id is not None or obj.area_id is not None:
                    raise ValueError('이번 자료는 브랜드·상권 미연결 상태여야 합니다.')
                # FK는 위에서 집합으로 검증해 매장별 관계 조회를 생략합니다.
                obj.clean_fields(exclude=['source', 'industry', 'brand', 'area'])
                obj.clean()
                if obj.external_id in external_ids:
                    raise ValueError('매장 식별자 중복: ' + obj.external_id)
                external_ids.add(obj.external_id)
                if not isinstance(obj.raw, dict):
                    raise ValueError('원본 raw 형식 오류')
                if str(obj.latitude) != obj.raw['위도'] or str(obj.longitude) != obj.raw['경도']:
                    # Decimal 문자열의 지수 표기는 수치 동등성으로 확인합니다.
                    from decimal import Decimal
                    if obj.latitude != Decimal(obj.raw['위도']) or obj.longitude != Decimal(obj.raw['경도']):
                        raise ValueError('원본 좌표 불일치')
                if obj.external_id != obj.raw['상가업소번호']:
                    raise ValueError('원본 식별자 불일치')
                objects.append(obj)
                total += 1
            PublicStore.objects.bulk_create(objects, batch_size=500)
            self.stdout.write(f'{path.name}: 누적 {total:,}건 검증·적재', ending='\n')
            self.stdout.flush()
        if total != manifest['output_stores']:
            raise ValueError('최종 매장 건수 불일치')
        if not options['commit']:
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(f'{total:,}건 ' + ('저장 완료' if options['commit'] else '검증 완료 (저장하지 않음)')))
