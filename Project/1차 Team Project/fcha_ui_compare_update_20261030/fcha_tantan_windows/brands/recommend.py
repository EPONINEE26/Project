"""회원가입 때 입력한 창업 조건(목적·예산·목표 매출·희망 지역·업종)으로 브랜드를 추천합니다.

점수(100점 만점)는 공개 통계만으로 계산하는 참고값이며 수익을 보장하지 않습니다.
- 예산 적합: 정보공개서 창업 부담금이 예산 이내인 브랜드만 추천(미공개는 감점 후 포함)
- 목표 매출: 가맹점 평균 월매출(범위 자료면 하한)이 목표 이상인지
- 희망 지역: 희망 시·도의 가맹점 수
- 안정성: 계약종료·해지 ÷ 가맹점 수 (낮을수록 높음)
"""
from django.contrib.auth.decorators import login_required
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Coalesce
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .models import AnnualStat, RegionalStat

# 창업 목적별 가중치(예산, 매출, 지역, 안정성)
WEIGHTS = {
    'living': (30, 20, 20, 30),      # 생계형: 안정성 중시
    'invest': (25, 35, 15, 25),      # 투자형: 매출 중시
    'convert': (30, 25, 20, 25),     # 업종 전환
    'side': (40, 20, 20, 20),        # 부업·소자본: 예산 중시
    'other': (30, 25, 20, 25),
}


def recommend(profile, brands, year, limit=10):
    stat = AnnualStat.objects.filter(brand=OuterRef('pk'), year=year).order_by()
    qs = brands.annotate(
        r_cost=Subquery(stat.values('startup_cost_krw')[:1]),
        r_sales=Coalesce(Subquery(stat.values('annual_sales_krw')[:1]), Subquery(stat.values('sales_min_krw')[:1])),
        r_stores=Subquery(stat.values('stores')[:1]), r_closed=Subquery(stat.values('closed')[:1]))
    if profile.desired_region:
        regional = RegionalStat.objects.filter(annual_stat__brand=OuterRef('pk'), annual_stat__year=year,
                                               region=profile.desired_region).order_by()
        qs = qs.annotate(r_region=Subquery(regional.values('stores')[:1]))
    if profile.desired_category and profile.desired_category != '전체':
        qs = qs.filter(category=profile.desired_category)
    budget = (profile.budget_manwon or 0) * 10000
    target = (profile.target_monthly_sales_manwon or 0) * 10000
    w_budget, w_sales, w_region, w_stable = WEIGHTS.get(profile.startup_purpose, WEIGHTS['other'])
    results = []
    for brand in qs.filter(r_stores__isnull=False):
        reasons, score = [], 0.0
        cost = brand.r_cost
        if cost is not None and budget and cost > budget:
            continue  # 예산 초과는 추천하지 않습니다.
        if cost is None:
            score += w_budget * 0.3
            reasons.append('창업 부담금 미공개(예산 적합 여부 확인 필요)')
        else:
            score += w_budget
            reasons.append(f'창업 부담금 {round(cost / 10000):,}만원 · 예산 이내')
        monthly = brand.r_sales / 12 if brand.r_sales is not None else None
        if monthly is None:
            reasons.append('평균 매출 미공개')
        elif target:
            ratio = min(monthly / target, 1)
            score += w_sales * ratio
            reasons.append(f'평균 월매출 {round(monthly / 10000):,}만원 · 목표 대비 {round(monthly / target * 100)}%')
        else:
            score += w_sales * 0.5
        if profile.desired_region:
            count = getattr(brand, 'r_region', None) or 0
            score += w_region * min(count / 30, 1)
            reasons.append(f'{profile.desired_region} 가맹점 {count:,}개')
        if brand.r_stores and brand.r_closed is not None:
            rate = brand.r_closed / brand.r_stores
            small = brand.r_stores < 10  # 가맹점이 적으면 해지율 0%도 우연일 수 있어 절반만 반영
            score += w_stable * (1 - min(rate / 0.2, 1)) * (0.5 if small else 1)
            reasons.append(f'계약종료·해지율 {rate * 100:.1f}%' + (f' (전국 {brand.r_stores}개 · 표본 적음)' if small else ''))
        else:
            score += w_stable * 0.3
        results.append({'brand': brand, 'score': round(score), 'reasons': reasons})
    results.sort(key=lambda r: (-r['score'], r['brand'].id))
    return results[:limit]


@login_required
@require_GET
def recommend_view(request):
    from .views import context_for
    context = context_for(request)
    profile = getattr(request.user, 'member_profile', None)
    if profile is not None and profile.wants_startup is False:
        profile = None  # 창업 목적이 아니면 조건 입력 안내만 보여줍니다.
    results = recommend(profile, context['all_brands'], context['year']) if profile else []
    context.update(page='recommend', profile=profile, results=results)
    return render(request, 'recommend.html', context)
