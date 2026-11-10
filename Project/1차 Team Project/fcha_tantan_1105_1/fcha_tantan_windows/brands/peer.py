"""동종업계(같은 업종·같은 공시연도) 평균과 추천 점수.

추천 점수(0~100) = (폐업률 점수 + 월매출 점수 + 창업비용 점수) ÷ 3
  · 각 항목은 업계 평균과 같으면 50점, 업계보다 2배 이상 유리하면 100점(상한), 불리할수록 0점에 가깝습니다.
  · 폐업률 점수   = 50 × 업계 폐업률 ÷ 브랜드 폐업률   (폐업률 = 연간 폐업 ÷ 연말 전체 매장)
  · 월매출 점수   = 50 × 브랜드 월매출 ÷ 업계 평균 월매출
  · 창업비용 점수 = 50 × 업계 평균 창업비용 ÷ 브랜드 창업비용
  · 공시 값이 없는 항목은 0점입니다(추정값으로 채우지 않음).
  · 연말 매장이 MIN_STORES_FOR_CLOSURE개 미만이면 폐업 1~2건으로 비율이 크게 흔들리므로 폐업률 점수는 0점입니다.
업계 평균은 값이 있는 브랜드만의 단순 평균, 업계 폐업률은 매장·폐업이 모두 있는 브랜드의 합계 기준입니다.
"""
from collections import defaultdict
from .models import AnnualStat

MIN_STORES_FOR_CLOSURE = 30
SCORE_NOTE = ('추천 점수 = (폐업률 점수 + 월매출 점수 + 창업비용 점수) ÷ 3 · 각 항목은 같은 업종 평균과 같으면 50점, '
              '2배 이상 유리하면 100점 · 폐업률 = 연간 폐업 ÷ 연말 매장 · 공시 값이 없는 항목은 0점 · '
              f'연말 매장 {MIN_STORES_FOR_CLOSURE}개 미만은 폐업률 점수 0점')


def bar(mine, average, count):
    """Template data for one brand-vs-industry bar pair (same shape as the brand detail cards)."""
    if mine is None or average is None:
        return None
    top = max(mine, average) or 1
    return {'mine': mine, 'average': round(average), 'count': count,
            'mine_width': round(mine / top * 100, 1), 'average_width': round(average / top * 100, 1)}


def category_benchmarks(year, brands):
    """One query: industry averages per category for the given year and visible brands."""
    groups = defaultdict(list)
    rows = AnnualStat.objects.filter(year=year, brand__in=brands).values(
        'brand__category', 'stores', 'opened', 'closed', 'annual_sales_krw', 'startup_cost_krw')
    for row in rows:
        groups[row['brand__category']].append(row)
    result = {}
    for category, stats in groups.items():
        def average(field, scale=1):
            found = [s[field] for s in stats if s[field] is not None]
            return (sum(found) / len(found) / scale, len(found)) if found else (None, 0)
        pairs = [(s['closed'], s['stores']) for s in stats if s['closed'] is not None and s['stores']]
        result[category] = {
            'opened': average('opened'), 'closed': average('closed'),
            'monthly': average('annual_sales_krw', 12 * 10000), 'cost': average('startup_cost_krw', 10000),
            'closure': (sum(c for c, _ in pairs) / sum(n for _, n in pairs) * 100, len(pairs)) if pairs else (None, 0),
        }
    return result


def ratio_score(better, worse):
    """50 × better ÷ worse, capped to 0~100. Both are 'how good' oriented values."""
    if better is None or worse is None:
        return None
    if worse == 0:
        return 100.0 if better > 0 else 50.0
    return round(min(100.0, 50 * better / worse), 1)


def brand_comparison(stat, cost_krw, benchmark):
    """Bars and scores for one brand. stat may be None (no disclosure for the year)."""
    benchmark = benchmark or {}
    stores = stat.stores if stat else None
    closed = stat.closed if stat else None
    monthly = round(stat.annual_sales_krw / 12 / 10000) if stat and stat.annual_sales_krw is not None else None
    cost = round(cost_krw / 10000) if cost_krw is not None else None
    closure = round(closed / stores * 100, 1) if closed is not None and stores else None
    peer_closure, closure_count = benchmark.get('closure', (None, 0))
    bars = {
        'cost': bar(cost, *benchmark.get('cost', (None, 0))),
        'opened': bar(stat.opened if stat else None, *benchmark.get('opened', (None, 0))),
        'closed': bar(closed, *benchmark.get('closed', (None, 0))),
        'monthly': bar(monthly, *benchmark.get('monthly', (None, 0))),
        'closure': {'mine': closure, 'average': round(peer_closure, 1), 'count': closure_count}
                   if closure is not None and peer_closure is not None else None,
    }
    # 폐업률·창업비용은 낮을수록, 월매출은 높을수록 유리합니다.
    few_stores = stores is not None and stores < MIN_STORES_FOR_CLOSURE
    scores = {
        'closure': None if few_stores else ratio_score(peer_closure, closure) if closure is not None and peer_closure is not None else None,
        'sales': ratio_score(monthly, benchmark.get('monthly', (None, 0))[0]),
        'cost': ratio_score(benchmark.get('cost', (None, 0))[0], cost) if cost else None,
    }
    scores['total'] = round(sum(v or 0 for v in scores.values()) / 3, 1)
    scores['few_stores'] = few_stores
    scores['min_stores'] = MIN_STORES_FOR_CLOSURE
    return bars, scores
