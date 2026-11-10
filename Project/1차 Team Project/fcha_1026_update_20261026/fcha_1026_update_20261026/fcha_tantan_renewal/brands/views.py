import csv
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Max, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import SavedBrand
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from .models import AdSlot, AnnualStat, Brand, RegionalStat
from .constants import REGIONS
from .reviews import review_context
from .categories import category_groups


PAGE_SIZE = 10


def visible_brands():
    # 실제 브랜드가 들어오면 예시 브랜드를 목록에서 제외합니다.
    qs = Brand.objects.all()
    if qs.filter(is_demo=False).exists():
        qs = qs.filter(is_demo=False)
    return qs.order_by('id')


def with_stats(qs):
    # 화면에 그릴 브랜드만 연도·지역 통계를 함께 불러옵니다(1,800여 개 전체를 매번 읽지 않음).
    return qs.prefetch_related('annual_stats__regional_stats', 'annual_stats__area_sales')


def context_for(request):
    # 여러 화면에서 함께 사용하는 연도, 비교함, 관심 목록입니다.
    brands = visible_brands()
    stats = AnnualStat.objects.filter(brand__in=brands)
    years = sorted(set(stats.values_list('year', flat=True)), reverse=True)
    sources = sorted(set(stats.values_list('source_label', flat=True)))
    updated_at = stats.aggregate(latest=Max('updated_at'))['latest'] or ''
    is_demo = brands.exists() and not brands.filter(is_demo=False).exists()
    default_year = 2025
    if years:
        default_year = years[0]
    try:
        year = int(request.GET.get('year', default_year))
    except ValueError:
        year = default_year
    if years and year not in years:
        year = default_year

    session_slugs = request.session.get('tantan-compare', [])
    available = set(brands.filter(slug__in=session_slugs).values_list('slug', flat=True))
    compare = []
    for slug in session_slugs:
        if slug in available and slug not in compare and len(compare) < 2:
            compare.append(slug)
    saved = list(SavedBrand.objects.filter(user=request.user).values_list('brand__slug', flat=True)) if request.user.is_authenticated else []
    by_slug = {b.slug: b for b in with_stats(brands.filter(slug__in=compare))}
    compare_brands = [by_slug[slug] for slug in compare]
    request.session['tantan-compare'] = compare
    source_label = ' / '.join(sources)
    if not source_label:
        source_label = '데이터 없음'
    groups = category_groups(brands)
    group_of = {c['name']: g['name'] for g in groups for c in g['categories']}
    context = {
        'all_brands': brands,
        'years': years,
        'year': year,
        'regions': REGIONS,
        'is_demo': is_demo,
        'source_label': source_label,
        'updated_at': updated_at,
        'compare_ids': compare,
        'saved_ids': saved,
        'compare_brands': compare_brands,
        # 업종은 DB 브랜드에서 만듭니다: 업종 묶음(커피·한식·치킨 …) 아이콘 + 세부 업종 선택
        'category_groups': groups,
        'group_names': ['전체'] + [g['name'] for g in groups],
        'group_of': group_of,
        'categories': ['전체'] + list(group_of),
        'sorts': [('stores', '매장 수 많은 순'), ('sales', '평균 월 매출 높은 순'),
                  ('opened', '신규 개업 많은 순'), ('closed', '폐업 수 적은 순'), ('name', '브랜드 이름순')],
    }
    return context


def to_manwon_month(value):
    return round(value / 12 / 10000) if value is not None else None


def brand_row(brand, year, region='전국'):
    # 선택 연도에 해당하는 통계를 찾습니다. 없으면 None입니다.
    stat = None
    for annual in brand.annual_stats.all():
        if annual.year == year:
            stat = annual
            break
    region_counts = {}
    region_stat = None
    monthly = None
    if stat:
        for regional in stat.regional_stats.all():
            region_counts[regional.region] = regional.stores
            if regional.region == region:
                region_stat = regional
        if stat.annual_sales_krw is not None:
            monthly = round(stat.annual_sales_krw / 12 / 10000)
    if stat and region == '전국':
        stores = stat.stores
    else:
        stores = region_counts.get(region)
    try:
        area_record = stat.area_sales if stat else None
    except ObjectDoesNotExist:
        area_record = None
    per_pyeong = area_record.annual_sales_per_pyeong_krw if area_record else None
    area_sqm = brand.area_sqm
    has_range = stat is not None and stat.sales_min_krw is not None and stat.sales_max_krw is not None
    has_region_range = region_stat is not None and region_stat.sales_min_krw is not None and region_stat.sales_max_krw is not None
    return {'brand': brand, 'stat': stat, 'monthly': monthly, 'stores': stores, 'region_counts': region_counts,
            # 공개 자료가 범위값이면 하한~상한(만원/월)만 보여줍니다. 중간값을 만들지 않습니다.
            'monthly_min': to_manwon_month(stat.sales_min_krw) if has_range else None,
            'monthly_max': to_manwon_month(stat.sales_max_krw) if has_range else None,
            'region_monthly_min': to_manwon_month(region_stat.sales_min_krw) if has_region_range else None,
            'region_monthly_max': to_manwon_month(region_stat.sales_max_krw) if has_region_range else None,
            'area_pyeong': round(area_sqm / 3.305785, 1) if area_sqm else None,
            'reference_per_pyeong': round(stat.annual_sales_krw / 12 / 10000 / (area_sqm / 3.305785), 2) if stat and stat.annual_sales_krw is not None and area_sqm else None,
            'per_pyeong_annual': round(per_pyeong / 10000, 2) if per_pyeong is not None else None,
            'per_pyeong_monthly': round(per_pyeong / 12 / 10000, 2) if per_pyeong is not None else None,
            'area_source': area_record.source_label if area_record else ''}


def annotate_year(qs, year, region='전국'):
    # 정렬·필터를 DB에서 처리하기 위해 선택 연도 값을 붙입니다.
    stat = AnnualStat.objects.filter(brand=OuterRef('pk'), year=year).order_by()
    qs = qs.annotate(y_stores=Subquery(stat.values('stores')[:1]), y_opened=Subquery(stat.values('opened')[:1]),
                     y_closed=Subquery(stat.values('closed')[:1]),
                     y_sales=Coalesce(Subquery(stat.values('annual_sales_krw')[:1]), Subquery(stat.values('sales_min_krw')[:1])))
    if region != '전국':
        regional = RegionalStat.objects.filter(annual_stat__brand=OuterRef('pk'), annual_stat__year=year, region=region).order_by()
        qs = qs.annotate(y_region_stores=Subquery(regional.values('stores')[:1]))
    return qs


def paginate(request, qs, year, region='전국'):
    page_obj = Paginator(qs, PAGE_SIZE).get_page(request.GET.get('page'))
    ids = [b.pk for b in page_obj.object_list]
    by_id = {b.pk: b for b in with_stats(Brand.objects.filter(pk__in=ids))}
    rows = [brand_row(by_id[pk], year, region) for pk in ids]
    params = request.GET.copy()
    params.pop('page', None)
    return rows, {'page_obj': page_obj, 'total_count': page_obj.paginator.count,
                  'page_range': list(page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)),
                  'page_query': params.urlencode()}


def ad_rows(year, region):
    # 1·2번 광고 자리. 노출 기간 안의 가장 최근 시작 광고 1개씩, 없으면 빈 자리 안내.
    today = timezone.localdate()
    slots = AdSlot.objects.filter(is_active=True, starts_on__lte=today, ends_on__gte=today,
                                  brand__in=visible_brands()).order_by('position', '-starts_on', '-id')
    chosen = {}
    for slot in slots:
        chosen.setdefault(slot.position, slot)
    brands = {b.pk: b for b in with_stats(Brand.objects.filter(pk__in=[s.brand_id for s in chosen.values()]))}
    return [{'position': pos, 'slot': chosen.get(pos),
             'row': brand_row(brands[chosen[pos].brand_id], year, region) if pos in chosen else None} for pos in (1, 2)]


def selected_category(request, context):
    """업종 묶음(group)과 세부 업종(category)을 검사합니다. 세부 업종이 묶음과 맞지 않으면 세부 업종을 풉니다."""
    group = request.GET.get('group', '전체')
    category = request.GET.get('category', '전체')
    if group not in context['group_names']:
        group = '전체'
    if category not in context['categories']:
        category = '전체'
    if category != '전체':
        if group == '전체':
            group = context['group_of'][category]
        elif context['group_of'][category] != group:
            category = '전체'
    return group, category


def group_categories(context, group):
    return [c['name'] for g in context['category_groups'] if g['name'] == group for c in g['categories']]


def list_context(request, saved_only=False):
    context = context_for(request)
    query = request.GET.get('query', '').strip()
    group, category = selected_category(request, context)
    region = request.GET.get('region', '전국')
    sort = request.GET.get('sort', 'stores')
    if region not in ['전국', *REGIONS]:
        region = '전국'
    if sort not in dict(context['sorts']):
        sort = 'stores'
    qs = context['all_brands']
    if saved_only:
        qs = qs.filter(slug__in=context['saved_ids'])
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(category__icontains=query) | Q(english_name__icontains=query))
    if category != '전체':
        qs = qs.filter(category=category)
    elif group != '전체':
        qs = qs.filter(category__in=group_categories(context, group))
    qs = annotate_year(qs, context['year'], region)
    store_key = 'y_stores'
    if region != '전국':
        qs = qs.filter(y_region_stores__gt=0)
        store_key = 'y_region_stores'
    order = {'name': ['name', 'id'], 'closed': [F('y_closed').asc(nulls_last=True), 'id'],
             'sales': [F('y_sales').desc(nulls_last=True), 'id'], 'opened': [F('y_opened').desc(nulls_last=True), 'id'],
             'stores': [F(store_key).desc(nulls_last=True), 'id']}[sort]
    rows, pages = paginate(request, qs.order_by(*order), context['year'], region)
    context.update(pages)
    current = next((g for g in context['category_groups'] if g['name'] == group), None)
    context.update(rows=rows, query=query, group=group, current_group=current, category=category, region=region, sort=sort,
                   saved_only=saved_only, page='saved' if saved_only else 'list',
                   ad_rows=[] if saved_only else ad_rows(context['year'], region))
    return context


@require_GET
def blist(request):
    return render(request, 'blist.html', list_context(request))


@login_required
@require_GET
def bsaved(request):
    return render(request, 'bsaved.html', list_context(request, saved_only=True))


@login_required
@require_GET
def bview(request, slug):
    context = context_for(request)
    brand = get_object_or_404(with_stats(visible_brands()), slug=slug)
    row = brand_row(brand, context['year'])
    regions = [{'name': name, 'count': row['region_counts'].get(name)} for name in REGIONS]
    maximum = max([r['count'] or 0 for r in regions] + [1])
    for region in regions:
        region['width'] = round((region['count'] or 0) / maximum * 100, 2)
    top_regions = sorted(regions, key=lambda r: r['count'] if r['count'] is not None else -1, reverse=True)[:7]
    trend = list(brand.annual_stats.all())
    maximum = max([v or 0 for s in trend for v in [s.opened, s.closed]] + [1])
    chart = [{'year': s.year, 'opened': s.opened, 'closed': s.closed,
              'opened_height': round((s.opened or 0) / maximum * 85, 2),
              'closed_height': round((s.closed or 0) / maximum * 85, 2)} for s in trend]
    # 연도별 정보공개서 창업 부담금이 있으면 그 해 값을, 없으면 브랜드 기본 견적을 씁니다.
    stat = row['stat']
    if stat and stat.startup_cost_krw is not None:
        costs, cost_total, cost_is_yearly = stat.startup_cost_breakdown.items(), stat.startup_cost_krw, True
    else:
        costs, cost_total, cost_is_yearly = brand.costs.items(), brand.initial_cost_krw, False
    context.update(page='detail', row=row, brand=brand, regional_rows=regions,
                   top_regions=top_regions, chart=chart, costs=costs, cost_total=cost_total, cost_is_yearly=cost_is_yearly)
    context.update(review_context(request, brand))
    return render(request, 'bview.html', context)


def startup_cost(row):
    stat = row['stat']
    if stat and stat.startup_cost_krw is not None:
        return stat.startup_cost_krw
    return row['brand'].initial_cost_krw


def selected_rows(context):
    rows = []
    for brand in context['compare_brands']:
        rows.append(brand_row(brand, context['year']))
    return rows


@login_required
@require_GET
def bcompare(request):
    context = context_for(request)
    rows = selected_rows(context)
    comparisons = [
        ('연말 매장 수', [r['stores'] for r in rows], '개'),
        ('연간 신규 개업', [r['stat'].opened if r['stat'] else None for r in rows], '개'),
        ('연간 폐업', [r['stat'].closed if r['stat'] else None for r in rows], '개'),
        ('평균 월 매출', [r['monthly'] for r in rows], '만원'),
        ('창업비용 (만원)', [round(startup_cost(r) / 10000) if startup_cost(r) is not None else None for r in rows], '만원'),
        ('평당 평균 연매출', [r['per_pyeong_annual'] for r in rows], '만원/평·년'),
        ('평당 평균 월매출', [r['per_pyeong_monthly'] for r in rows], '만원/평·월'),
        ('기준 면적 환산 월매출', [r['reference_per_pyeong'] for r in rows], '만원/평·월'),
        ('기준 면적', [r['brand'].area_sqm for r in rows], '㎡'),
    ]
    comparisons += [(f'{name} 매장 수', [r['region_counts'].get(name) for r in rows], '개') for name in REGIONS]
    # Each metric has its own unit/scale; unlike units are never drawn on a shared axis.
    metrics = [{'id': str(i), 'label': label, 'values': values, 'unit': unit} for i, (label, values, unit) in enumerate(comparisons)]
    context.update(page='compare', rows=rows, comparisons=comparisons, comparison_metrics=metrics,
                   comparison_data={'brands': [r['brand'].name for r in rows], 'metrics': metrics})
    return render(request, 'bcompare.html', context)


@login_required
@require_GET
def bregion(request):
    context = context_for(request)
    region = request.GET.get('region', '서울')
    if region not in REGIONS:
        region = '서울'
    query = request.GET.get('query', '').strip()
    category = request.GET.get('category', '전체')
    if category not in context['categories']:
        category = '전체'
    year = context['year']
    brands = context['all_brands']
    if query:
        brands = brands.filter(Q(name__icontains=query) | Q(english_name__icontains=query))
    if category != '전체':
        brands = brands.filter(category=category)
    # 타일은 전체 브랜드 기준, 요약·목록은 검색 조건 기준입니다.
    regional = RegionalStat.objects.filter(annual_stat__year=year, annual_stat__brand__in=context['all_brands'])
    sums = dict(regional.values('region').annotate(total=Sum('stores')).values_list('region', 'total'))
    tiles = [{'name': name, 'total': sums.get(name) or 0} for name in REGIONS]
    summary = RegionalStat.objects.filter(annual_stat__year=year, annual_stat__brand__in=brands, region=region).aggregate(
        total=Sum('stores'), active=Count('id', filter=Q(stores__gt=0)))
    qs = annotate_year(brands, year, region).order_by(F('y_region_stores').desc(nulls_last=True), 'id')
    rows, pages = paginate(request, qs, year, region)
    for row in rows:
        row['share'] = round(row['stores'] / row['stat'].stores * 100, 1) if row['stores'] is not None and row['stat'] and row['stat'].stores else None
    context.update(pages)
    context.update(page='regions', region=region, rows=rows, tiles=tiles, query=query, category=category,
                   total=summary['total'] or 0, active_count=summary['active'])
    return render(request, 'bregion.html', context)


@require_GET
def guide(request):
    context = context_for(request)
    context['page'] = 'guide'
    return render(request, 'guide.html', context)


def return_to_page(request):
    target = request.POST.get('next', reverse('brands:blist'))
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = reverse('brands:blist')
    return redirect(target)


@require_POST
def compare_toggle(request, slug):
    brand = get_object_or_404(visible_brands(), slug=slug)
    context = context_for(request)
    selected = context['compare_ids']
    if brand.slug in selected:
        selected.remove(brand.slug)
    elif len(selected) >= 2:
        messages.info(request, '최대 2개 브랜드까지 비교할 수 있어요. 기존 브랜드를 먼저 빼주세요.')
    else:
        selected.append(brand.slug)
    request.session['tantan-compare'] = selected
    return return_to_page(request)


@require_POST
def compare_clear(request):
    request.session['tantan-compare'] = []
    return return_to_page(request)


@login_required
@require_POST
def saved_toggle(request, slug):
    brand = get_object_or_404(visible_brands(), slug=slug)
    saved, created = SavedBrand.objects.get_or_create(user=request.user, brand=brand)
    if not created: saved.delete()
    return return_to_page(request)


@login_required
@require_GET
def compare_csv(request):
    context = context_for(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="tantan_compare_{context["year"]}.csv"'
    response.write('﻿')
    writer = csv.writer(response)
    writer.writerow(['데이터 구분', '기준연도', '브랜드', '전국 매장 수', '연간 개업 수', '연간 폐업 수', '평균 월 매출(만원)', '창업비용(원)', '평당 평균 연매출(만원/평·년)', '평당 평균 월매출(만원/평·월)'])
    def safe(value):
        text = str(value) if value is not None else ''
        return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text
    for row in selected_rows(context):
        s = row['stat']
        values = ['가상 예시' if row['brand'].is_demo else '실제 데이터', context['year'], row['brand'].name,
                  row['stores'], s.opened if s else None, s.closed if s else None, row['monthly'], row['brand'].initial_cost_krw, row['per_pyeong_annual'], row['per_pyeong_monthly']]
        writer.writerow([safe(v) for v in values])
    return response
