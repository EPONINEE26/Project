"""상권 업종 경쟁 밀도(1단계): 공공 상가 매장 수로 계산한 입지계수(LQ).

입지계수 = (이 상권에서 해당 업종이 차지하는 매장 비중) ÷ (서울 전체 상권에서 해당 업종 비중)
  · 경쟁 과밀 업종: 입지계수 CROWDED_LQ배 이상 · 상권 내 매장 MIN_CROWDED_STORES곳 이상
  · 공급이 적은 업종: 서울 평균 비중 COMMON_SHARE% 이상인 흔한 업종인데 입지계수 SCARCE_LQ배 이하
    (상권 전체 비교 대상 매장이 MIN_AREA_STORES곳 미만이면 표본이 작아 판단하지 않음)
비교 대상은 소비자 대상 업종(소매·음식·교육·여가·개인서비스)이며 숙박·전문직·병원·부동산 등은 제외합니다.
매출·폐업 자료가 아니므로 '유불리'가 아니라 경쟁 정도를 보여주는 지표입니다.
"""
from functools import lru_cache
from django.db.models import Count, Max, Q
from .analysis_models import PublicStore

CONSUMER_PREFIXES = ('G2', 'I2', 'P1', 'R1', 'S2')
CROWDED_LQ = 1.5
SCARCE_LQ = 0.5
MIN_CROWDED_STORES = 5
MIN_AREA_STORES = 50
COMMON_SHARE = 1.0
TOP = 5


def consumer_stores(reference_on):
    consumer = Q()
    for prefix in CONSUMER_PREFIXES:
        consumer |= Q(industry__code__startswith=prefix)
    return PublicStore.objects.filter(consumer, reference_on=reference_on, industry__isnull=False)


@lru_cache(maxsize=2)
def seoul_shares(reference_on):
    """{industry_id: (name, share%)} over every store linked to a commercial area. Cached per snapshot."""
    rows = list(consumer_stores(reference_on).filter(area__isnull=False)
                .values('industry_id', 'industry__name').annotate(n=Count('id')))
    total = sum(r['n'] for r in rows) or 1
    return {r['industry_id']: (r['industry__name'], r['n'] / total * 100) for r in rows}


def industry_competition(area):
    if not area:
        return None
    reference_on = PublicStore.objects.aggregate(latest=Max('reference_on'))['latest']
    if reference_on is None:
        return None
    shares = seoul_shares(reference_on)
    local = {r['industry_id']: r['n'] for r in consumer_stores(reference_on).filter(area=area)
             .values('industry_id').annotate(n=Count('id'))}
    total = sum(local.values())
    result = {'reference_on': reference_on, 'total': total, 'crowded': [], 'scarce': [],
              'enough': total >= MIN_AREA_STORES, 'min_area_stores': MIN_AREA_STORES,
              'crowded_lq': CROWDED_LQ, 'scarce_lq': SCARCE_LQ, 'common_share': COMMON_SHARE}
    if not total:
        return result
    for industry_id, (name, seoul_share) in shares.items():
        count = local.get(industry_id, 0)
        local_share = count / total * 100
        row = {'name': name, 'count': count, 'local_share': round(local_share, 1),
               'seoul_share': round(seoul_share, 1), 'lq': round(local_share / seoul_share, 1) if seoul_share else None}
        if count >= MIN_CROWDED_STORES and row['lq'] is not None and local_share / seoul_share >= CROWDED_LQ:
            result['crowded'].append(row)
        elif result['enough'] and seoul_share >= COMMON_SHARE and local_share / seoul_share <= SCARCE_LQ:
            result['scarce'].append(row)
    result['crowded'] = sorted(result['crowded'], key=lambda r: (-r['lq'], -r['count'], r['name']))[:TOP]
    result['scarce'] = sorted(result['scarce'], key=lambda r: (-r['seoul_share'], r['count'], r['name']))[:TOP]
    return result
