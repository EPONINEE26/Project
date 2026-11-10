"""저장 조건 변경을 롤백하며 실제 DB의 페이지와 경계 API 출력을 확인합니다."""
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fcha_tantan.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db import transaction
from django.test import RequestFactory
from brands.views import bregion
from market.analysis import selected_area, area_geometry
from market.analysis_models import CommercialArea, PopulationStat, StartupCondition


def main():
    factory = RequestFactory()
    # 작은 경계부터 내부 중심점을 찾아 다른 상권과 겹치지 않는 예시를 선택합니다.
    areas = list(CommercialArea.objects.filter(populationstat__period='2026Q2').distinct())
    areas.sort(key=lambda a: len(str(a.boundary)))
    selected = None
    for area in areas[:30]:
        ring = area.boundary['coordinates'][0] if area.boundary['type'] == 'Polygon' else area.boundary['coordinates'][0][0]
        cross = [(a[0]*b[1]-b[0]*a[1]) for a, b in zip(ring, ring[1:])]
        denominator = 3 * sum(cross)
        if not denominator:
            continue
        x = sum((a[0]+b[0])*v for a, b, v in zip(ring, ring[1:], cross))/denominator
        y = sum((a[1]+b[1])*v for a, b, v in zip(ring, ring[1:], cross))/denominator
        condition = SimpleNamespace(longitude=Decimal(str(x)), latitude=Decimal(str(y)))
        found, _ = selected_area(condition)
        if found and found.pk == area.pk:
            selected = (area, condition)
            break
    if not selected:
        raise AssertionError('검증용 단일 상권 좌표를 찾지 못했습니다.')
    area, point = selected
    with transaction.atomic():
        user = get_user_model().objects.first()
        if user is None:
            user = get_user_model().objects.create(username='seoul-preview-verification')
        StartupCondition.objects.update_or_create(user=user, defaults={
            'location': area.name, 'location_scope': 'address', 'store_status': 'none',
            'total_budget_manwon': 10000, 'operation': 'unknown',
            'latitude': point.latitude, 'longitude': point.longitude,
        })
        request = factory.get('/brands/bregion/')
        request.user = user
        request.session = {}
        request._messages = FallbackStorage(request)
        response = bregion(request)
        assert response.status_code == 200
        html = response.content.decode('utf-8')
        for value in [area.name, '2026Q2', '원자료 수치', '세미 프로젝트 미리보기', '10대']:
            assert value in html, value
        geometry = area_geometry(request)
        data = json.loads(geometry.content)
        assert geometry.status_code == 200 and data['geometry'] and not data['verified']
        assert '미리보기' in data['note']
        print(json.dumps({
            'page_status': response.status_code, 'geometry_status': geometry.status_code,
            'example_area': area.name, 'latitude': str(point.latitude),
            'longitude': str(point.longitude),
            'latest_population': PopulationStat.objects.get(area=area, period='2026Q2', kind='floating').total,
            'areas': CommercialArea.objects.count(), 'population': PopulationStat.objects.count(),
        }, ensure_ascii=False))
        transaction.set_rollback(True)


if __name__ == '__main__':
    main()
