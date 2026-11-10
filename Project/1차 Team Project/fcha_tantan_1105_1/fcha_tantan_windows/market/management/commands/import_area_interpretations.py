"""지정한 경계 버전의 CommercialArea에 엑셀 원문 5개 항목을 저장합니다."""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from openpyxl import load_workbook

from market.analysis_models import CommercialArea


FIELDS = {
    'recommended_target': '추천 타깃층',
    'characteristics': '상권의 특성',
    'favorable_industries': '🟢 유리한 예시 업종',
    'unfavorable_industries': '🔴 불리한 예시 업종',
    'location_strategy': '전략적 입지 전제조건',
}


class Command(BaseCommand):
    help = '엑셀 원문을 상권 코드로 연결합니다. 기본은 미리보기이며 --commit으로 저장합니다.'

    def add_arguments(self, parser):
        parser.add_argument('path', help='위치에 제한 없는 원본 xlsx 경로')
        parser.add_argument('--area-version', required=True, help='적재 대상 CommercialArea 경계 버전')
        parser.add_argument('--commit', action='store_true')

    def handle(self, *args, **options):
        path = Path(options['path'])
        try:
            book = load_workbook(path, read_only=True, data_only=True)
            try:
                rows = book.active.iter_rows(values_only=True)
                headers = next(rows)
                code_index = headers.index('상권 코드')
                indices = {field: headers.index(label) for field, label in FIELDS.items()}
                records = {}
                for row in rows:
                    # 인구표 등 공식 상권 코드가 없는 별도 행은 제외합니다.
                    if row[code_index] is None:
                        continue
                    code = str(row[code_index]).removesuffix('.0')
                    if code in records:
                        raise ValueError(f'상권 코드 중복: {code}')
                    values = {field: row[index] if row[index] is not None else '' for field, index in indices.items()}
                    if any(not isinstance(value, str) for value in values.values()):
                        raise ValueError(f'원문이 문자열이 아닙니다: {code}')
                    records[code] = values
            finally:
                book.close()
        except (OSError, ValueError, StopIteration) as exc:
            raise CommandError(f'엑셀 확인 실패: {exc}') from exc

        with transaction.atomic():
            areas = list(CommercialArea.objects.select_for_update().filter(version=options['area_version']))
            if not areas:
                raise CommandError('해당 경계 버전의 상권이 없습니다.')
            matched = [area for area in areas if area.code in records]
            for area in matched:
                for field, value in records[area.code].items():
                    # 요약·재분류 없이 원문 그대로 저장. 빈 셀은 빈 문자열입니다.
                    setattr(area, field, value)
            self.stdout.write(f'엑셀 {len(records)}개 / DB 매칭 {len(matched)}개 / DB에 없는 코드 {len(set(records) - {a.code for a in areas})}개')
            if options['commit']:
                CommercialArea.objects.bulk_update(matched, list(FIELDS), batch_size=100)
                self.stdout.write(self.style.SUCCESS('CommercialArea 원문 저장 완료'))
            else:
                self.stdout.write('미리보기 완료. --commit을 추가하면 저장합니다.')
