import csv
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from accounts.models import SavedBrand
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from .models import Brand
from .constants import REGIONS
from .models import StartupCost


def visible_brands():
    # 실제 브랜드가 들어오면 예시 브랜드를 목록에서 제외합니다.
    qs = Brand.objects.all()
    if qs.filter(is_demo=False).exists():
        qs = qs.filter(is_demo=False)
    return qs.prefetch_related('annual_stats__regional_stats').order_by('id')


def context_for(request):
    # 여러 화면에서 함께 사용하는 연도, 비교함, 관심 목록입니다.
    brands = list(visible_brands()) # 실제 브랜드 조회는 visible_brands()에서 결정
    stats = []
    years = []
    available = []
    sources = []
    updated_at = ''
    is_demo = bool(brands) # 브랜드를 필터링하는 기능이 아님, 화면에 전달할 상태값을 계산하는 용도
    for brand in brands:
        available.append(brand.slug)
        if not brand.is_demo:
            is_demo = False
        for stat in brand.annual_stats.all():
            stats.append(stat)
            if stat.year not in years:
                years.append(stat.year)
            if stat.source_label not in sources:
                sources.append(stat.source_label)
            if updated_at == '' or stat.updated_at > updated_at:
                updated_at = stat.updated_at
    years.sort(reverse=True)

    # 기본 연도는 2026년
    default_year = 2026
    # 2026년 데이터가 없으면 가장 최근 연도 선택
    if years and 2026 not in years:
        default_year = years[0]
    try:
        year = int(request.GET.get('year', default_year))
    except ValueError:
        year = default_year
    if years and year not in years:
        year = default_year

    compare = []
    for slug in request.session.get('tantan-compare', []):
        if slug in available and slug not in compare and len(compare) < 2:
            compare.append(slug)
    saved = list(SavedBrand.objects.filter(user=request.user).values_list('brand__slug', flat=True)) if request.user.is_authenticated else []
    compare_brands = []
    for slug in compare:
        for brand in brands:
            if brand.slug == slug:
                compare_brands.append(brand)
    request.session['tantan-compare'] = compare
    sources.sort()
    source_label = ' / '.join(sources)
    if not source_label:
        source_label = '데이터 없음'
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
        'categories': ['전체', '카페', '치킨', '편의점', '미용실'],
        'sorts': [('stores', '매장 수 많은 순'), ('sales', '평균 월 매출 높은 순'),
                  ('opened', '신규 개업 많은 순'), ('closed', '폐업 수 적은 순'), ('name', '브랜드 이름순')],
    }
    return context


def brand_row(brand, year, region='전국'):
    # 선택 연도에 해당하는 통계를 찾습니다. 없으면 None입니다.
    stat = None
    for annual in brand.annual_stats.all():
        if annual.year == year:
            stat = annual
            break
    region_counts = {}
    monthly = None
    if stat:
        for regional in stat.regional_stats.all():
            region_counts[regional.region] = regional.stores
        if stat.annual_sales_krw is not None:
            monthly = round(stat.annual_sales_krw / 12 / 10000)
    # 전국 매장 수 계산 : 디장고, 파이썬에선 None, json에서는 null
    if stat and region == '전국':
        total_stores = stat.total_stores       # brands2.json의 total_stores (전체 매장 수)
        franchise_stores = stat.stores         # brands2.json의 stores (가맹점 수)
        direct_stores = stat.direct_stores     # brands2.json의 direct_stores (직영점 수)

        # 전체 매장 수가 None이 아니면 해당 값을 우선 사용
        if total_stores is not None:
            stores = total_stores

        # 전체 매장 수가 없고, 가맹점 또는 직영점 수 중 하나라도 값이 있으면 합산
        # 계산할 때 None은 0으로 취급하지만, DB에 저장된 None은 변경하지 않음
        elif franchise_stores is not None or direct_stores is not None:
            stores = (franchise_stores or 0) + (direct_stores or 0)

        # 전체 매장 수, 가맹점 수, 직영점 수가 모두 없으면 None
        else:
            stores = None

    # 전국이 아닌 경우 기존 지역별 가맹점 수 사용
    else:
        stores = region_counts.get(region)
    try:
        area_record = stat.area_sales if stat else None
    except ObjectDoesNotExist:
        area_record = None
    per_pyeong = area_record.annual_sales_per_pyeong_krw if area_record else None
    return {'brand': brand, 'stat': stat, 'monthly': monthly, 'stores': stores, 'region_counts': region_counts,
            'area_pyeong': round(brand.area_sqm / 3.305785, 1),
            'reference_per_pyeong': round(stat.annual_sales_krw / 12 / 10000 / (brand.area_sqm / 3.305785), 2) if stat and stat.annual_sales_krw is not None and brand.area_sqm > 0 else None,
            'per_pyeong_annual': round(per_pyeong / 10000, 2) if per_pyeong is not None else None,
            'per_pyeong_monthly': round(per_pyeong / 12 / 10000, 2) if per_pyeong is not None else None,
            'area_source': area_record.source_label if area_record else ''}


def list_context(request, saved_only=False):
    context = context_for(request)
    query = request.GET.get('query', '').strip()
    category = request.GET.get('category', '전체')
    region = request.GET.get('region', '전국')
    sort = request.GET.get('sort', 'stores')
    if category not in context['categories']:
        category = '전체'
    if region not in ['전국', *REGIONS]:
        region = '전국'
    if sort not in dict(context['sorts']):
        sort = 'stores'
    rows = []
    for brand in context['all_brands']:
        if saved_only and brand.slug not in context['saved_ids']:
            continue
        if query and query not in brand.name and query not in brand.category:
            continue
        if category != '전체' and brand.category != category:
            continue
        row = brand_row(brand, context['year'], region) # brand_row() 함수가 브랜드 통계를 가공해서 화면으로 전달하는 역할
        if region != '전국' and not row['stores']:
            continue
        rows.append(row)
    if sort == 'name':
        rows.sort(key=lambda row: row['brand'].name)
    elif sort == 'closed':
        rows.sort(key=lambda row: row['stat'].closed if row['stat'] and row['stat'].closed is not None else float('inf'))
    else:
        def value(row):
            v = None
            if sort == 'sales':
                v = row['monthly']
            elif sort == 'opened' and row['stat']:
                v = row['stat'].opened
            elif sort == 'stores':
                v = row['stores']
            if v is None:
                return -1
            return v
        rows.sort(key=value, reverse=True)
    context.update(rows=rows, query=query, category=category, region=region, sort=sort,
                saved_only=saved_only, page='saved' if saved_only else 'list')
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
    brand = get_object_or_404(visible_brands(), slug=slug)
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
    # 창업비용 항목의 영문 이름을 한글로 변환
    cost_names = {
        'franchise_fee_krw': '가맹비',
        'education_fee_krw': '교육비',
        'guarantee_deposit_krw': '보증금',
        'interior_cost_krw': '인테리어 비용',
        'equipment_cost_krw': '설비 비용',
        'other_cost_krw': '기타 비용',
    }

    # 선택한 연도에 해당하는 창업비용 찾기
    cost_history = brand.costs.get('history', [])

    selected_cost = next(
        (item for item in cost_history if item.get('year') == context['year']),
        None
    )

    # 선택 연도 자료가 있으면 해당 세부 비용 사용
    # 기존 더미 브랜드는 기존 비용 구조 유지
    if selected_cost is not None:
        breakdown = selected_cost.get('startup_cost_breakdown') or {}
    else:
        breakdown = (
            brand.costs
            if brand.is_demo
            else {}
        )

    # 실제 비용 항목만 추출
    cost_items = [
        (cost_names.get(name, name), value)
        for name, value in breakdown.items()
        if value is not None
        and isinstance(value, (int, float))
        and not isinstance(value, bool)
    ]
    # 선택 연도의 초기 창업비용 합계
    if selected_cost is not None:
        selected_cost_total = selected_cost.get('startup_cost_krw')
    elif brand.is_demo:
        selected_cost_total = brand.initial_cost_krw
    else:
        selected_cost_total = None

    # -------------------------------------------------
    # 신규 StartupCost 데이터 연결
    # 2024~2025년 신규 데이터 우선 사용
    # 신규 데이터가 없으면 기존 Brand.costs 유지
    # -------------------------------------------------
    # 출처 정보 초기화
    cost_source = None

    new_costs = StartupCost.objects.filter(
        brand=brand,
        year=context['year']
    ).select_related('item').order_by(
        'item__display_order'
    )
    
    # 신규 데이터가 존재할 경우
    if new_costs.exists():
        # 신규 데이터가 사용되면 출처 정보 저장
        cost_source = "priority_brands.json (19개 브랜드 추출 자료) · 원자료 검증 필요"
        # 기존 HTML에서 사용하는 (항목명, 금액) 구조
        cost_items = [
            (cost.item.name, cost.amount_krw)
            for cost in new_costs
        ]

        # 총창업비용 계산
        amounts = [cost.amount_krw for cost in new_costs]

        if all(amount is not None for amount in amounts):
            selected_cost_total = sum(amounts)
        else:
            selected_cost_total = None


    context.update(page='detail', row=row, brand=brand, regional_rows=regions,
            top_regions=top_regions, chart=chart, costs=cost_items, cost_total=selected_cost_total,cost_source=cost_source)
    return render(request, 'bview.html', context)

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
    # 선택한 브랜드의 연도별 창업비용 조회

    startup_cost_totals = []

    for row in rows:
        brand = row['brand']
        year = context['year']

        costs = list(
            StartupCost.objects.filter(
                brand=brand,
                year=year
            ).values_list('item__code', 'amount_krw')
        )

        # 신규 데이터가 있을 때
        if costs:
            amounts = dict(costs)

            required_codes = {
                'franchise_fee_krw',
                'education_fee_krw',
                'guarantee_deposit_krw',
                'other_cost_krw',
            }

            # 필수 항목 4개가 모두 있고 금액이 NULL이 아닌 경우
            if required_codes.issubset(amounts) and all(
                amounts[code] is not None
                for code in required_codes
            ):
                total = sum(amounts[code] for code in required_codes)
                startup_cost_totals.append(round(total / 10000))
            else:
                startup_cost_totals.append(None)

        # 신규 데이터가 없는 경우 기존 연도별 데이터 사용
        else:
            history = brand.costs.get('history', [])
            selected = next(
                (item for item in history if item.get('year') == year),
                None
            )

            if selected is not None:
                total = selected.get('startup_cost_krw')
            elif brand.is_demo:
                total = brand.initial_cost_krw
            else:
                total = None

            startup_cost_totals.append(
                round(total / 10000) if total is not None else None
            )
    comparisons = [
        ('연말 매장 수', [r['stores'] for r in rows], '개'),
        ('연간 신규 개업', [r['stat'].opened if r['stat'] else None for r in rows], '개'),
        ('연간 폐업', [r['stat'].closed if r['stat'] else None for r in rows], '개'),
        ('평균 월 매출', [r['monthly'] for r in rows], '만원'),
        # 창업비용 부분만 변경
        ('창업비용 (만원)', startup_cost_totals, '만원'),
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
    rows = [brand_row(b, context['year'], region) for b in context['all_brands']]
    rows.sort(key=lambda r: r['stores'] if r['stores'] is not None else -1, reverse=True)
    for row in rows:
        row['share'] = round(row['stores'] / row['stat'].stores * 100, 1) if row['stores'] is not None and row['stat'] and row['stat'].stores else None
    tiles = [{'name': name, 'total': sum(r['region_counts'].get(name) or 0 for r in rows)} for name in REGIONS]
    context.update(page='regions', region=region, rows=rows, tiles=tiles,
                   total=sum(r['stores'] or 0 for r in rows), active_count=sum(bool(r['stores']) for r in rows))
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
    response['Content-Disposition'] = (f'attachment; filename="tantan_compare_{context["year"]}.csv"')

    # 엑셀 한글 깨짐 방지
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['데이터 구분','기준연도','브랜드','전국 매장 수','연간 개업 수','연간 폐업 수','평균 월 매출(만원)','창업비용(원)','평당 평균 연매출(만원/평·년)','평당 평균 월매출(만원/평·월)'])

    def safe(value):
        text = str(value) if value is not None else ''
        return "'" + text if text.lstrip().startswith(
            ('=', '+', '-', '@')
        ) else text

    # 선택한 브랜드 목록
    for row in selected_rows(context):

        brand = row['brand']
        year = context['year']
        s = row['stat']

        # 1. 신규 StartupCost 조회
        costs = list(
            StartupCost.objects.filter(brand=brand,year=year).values_list('item__code', 'amount_krw'))
        startup_cost_krw = None

        # 2. 신규 데이터가 있는 경우
        if costs:
            amounts = dict(costs)

            required_codes = {'franchise_fee_krw','education_fee_krw','guarantee_deposit_krw','other_cost_krw'}

            if (len(costs) == len(required_codes) and required_codes.issubset(amounts) 
                and all(amounts[code] is not None for code in required_codes)):
                startup_cost_krw = sum(amounts[code] for code in required_codes)

        # 3. 신규 데이터가 없는 경우 기존 데이터 사용
        else:
            history = (brand.costs or {}).get('history', [])

            selected = next(
                (
                    item for item in history
                    if item.get('year') == year
                ),
                None
            )

            if selected is not None:
                startup_cost_krw = selected.get(
                    'startup_cost_krw'
                )

            elif brand.is_demo:
                startup_cost_krw = brand.initial_cost_krw

        # 4. CSV 한 행 작성
        values = [
            '가상 예시' if brand.is_demo else '실제 데이터',
            year,
            brand.name,
            row['stores'],
            s.opened if s else None,
            s.closed if s else None,
            row['monthly'],
            startup_cost_krw,
            row['per_pyeong_annual'],
            row['per_pyeong_monthly']
        ]

        writer.writerow([safe(v) for v in values])

    return response


#  데이터 변경 확인하면서 추가 진행

# 창업비용 조회 API
@require_GET
def startup_cost_api(request, slug):
    from django.http import JsonResponse
    from .models import StartupCost

    # 브랜드 조회
    brand = get_object_or_404(
        Brand.objects.filter(is_demo=False),
        slug=slug
    )

    # 조회 연도 확인
    try:
        year = int(request.GET.get('year', '2025'))
    except (ValueError, TypeError):
        return JsonResponse(
            {'error': '연도는 숫자로 입력해야 합니다.'},
            status=400
        )

    # 해당 브랜드, 해당 연도의 창업비용 조회
    costs = StartupCost.objects.filter(
        brand=brand,
        year=year
    ).select_related('item', 'source').order_by(
        'item__display_order'
    )

    # 데이터가 없는 연도
    if not costs.exists():
        return JsonResponse({
            'brand': brand.name,
            'slug': brand.slug,
            'year': year,
            'total_cost_krw': None,
            'items': {},
            'message': '해당 연도의 창업비용 데이터가 없습니다.'
        })

    items = {}
    total = 0
    has_missing = False

    for cost in costs:
        amount = cost.amount_krw

        items[cost.item.code] = amount

        if amount is None:
            has_missing = True
        else:
            total += amount

    return JsonResponse({
        'brand': brand.name,
        'slug': brand.slug,
        'year': year,
        'total_cost_krw': None if has_missing else total,
        'items': items,
        'source': 'priority_brands.json (19-brand category extract)'
    })