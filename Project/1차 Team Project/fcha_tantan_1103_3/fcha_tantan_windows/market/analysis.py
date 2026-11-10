from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from django.db.models import Q, Count, Max
from .analysis_forms import StartupConditionForm
from .analysis_models import StartupCondition, CommercialArea, PopulationStat, IndustrySales, StoreTrend, PublicStore, BrandOperation, IndustryCode
from .industry_mapping import category_filter


def area_store_summary(area, condition):
    result = {'available': False, 'category': condition.category if condition else '전체'}
    if not area:
        result['note'] = '위치를 저장해 하나의 상권에 연결하면 매장 집계를 표시합니다. 경계 밖·중첩 위치는 집계하지 않습니다.'
        return result
    # A single latest snapshot prevents counting the same store across dates.
    snapshot = PublicStore.objects.aggregate(latest=Max('reference_on'))['latest']
    if snapshot is None:
        result['note'] = '공공 매장 자료가 아직 연결되지 않았습니다.'
        return result
    qs = PublicStore.objects.filter(area=area, reference_on=snapshot)
    if not qs.exists():
        result['note'] = '최신 스냅샷에서 이 상권에 연결된 매장이 없습니다. 실제 매장이 없다는 뜻은 아닙니다.'
        return result
    predicate, status = category_filter(result['category'])
    if status == 'unmapped' and IndustryCode.objects.filter(brand_category=result['category'], verified=True).exists():
        status = 'verified'
    result.update(available=True, reference_on=snapshot, total=qs.count(),
                  category_status=status, category_total=None if status == 'unmapped' else qs.filter(predicate).count(),
                  industries=list(qs.values('industry_id', 'industry__name').annotate(total=Count('id')).order_by('-total', 'industry__name', 'industry_id')),
                  sources=list(qs.values_list('source__name', flat=True).order_by('source__name').distinct()))
    return result


def condition_context(request, form_class=StartupConditionForm):
    condition = StartupCondition.objects.filter(user=request.user).first()
    if request.method == 'POST' and request.POST.get('condition_action') == 'delete':
        StartupCondition.objects.filter(user=request.user).delete()
        messages.success(request,'저장된 분석 조건을 삭제했습니다.')
        return redirect(request.path), None, None
    form = form_class(request.POST if request.method == 'POST' else None, instance=condition)
    if request.method == 'POST' and form.is_valid():
        condition = form.save(commit=False)
        condition.user = request.user
        condition.save()
        messages.success(request,'창업 조건을 저장했습니다. 두 페이지에 함께 적용됩니다.')
        return redirect(request.path), None, None
    return None, form, condition


def inside_ring(x,y,ring):
    inside=False
    for a,b in zip(ring,ring[1:]+ring[:1]):
        ax,ay=map(Decimal,map(str,a[:2])); bx,by=map(Decimal,map(str,b[:2]))
        if (ay>y)!=(by>y) and x < (bx-ax)*(y-ay)/(by-ay)+ax:
            inside=not inside
    return inside


def contains(geometry,x,y):
    if not geometry: return False
    polygons=[geometry['coordinates']] if geometry.get('type')=='Polygon' else geometry.get('coordinates',[]) if geometry.get('type')=='MultiPolygon' else []
    return any(rings and inside_ring(x,y,rings[0]) and not any(inside_ring(x,y,r) for r in rings[1:]) for rings in polygons)


def selected_area(condition):
    if not condition or condition.longitude is None or condition.latitude is None: return None, '정확한 좌표를 선택하면 검증된 공식 상권 경계와 연결합니다.'
    # 공식 검증 상태를 바꾸지 않고 명시한 로컬 미리보기 버전만 함께 조회합니다.
    areas = CommercialArea.objects.filter(Q(verified=True) | Q(version='project-preview-20261103')).select_related('source')
    matches=[a for a in areas if contains(a.boundary,condition.longitude,condition.latitude)]
    # 공식 검증 자료가 있으면 로컬 미리보기보다 우선합니다.
    official = [a for a in matches if a.verified]
    if official:
        matches = official
    if len(matches)!=1: return None, '공식 상권이 없거나 여러 경계·버전이 겹칩니다. 코드·경계 검증 후 분석합니다.'
    area = matches[0]
    note = '' if area.verified else '세미 프로젝트 미리보기 · 경계 좌표계·기준일 미확인 · 인구 단위·평균/누계 미확인'
    return area, note


def candidate_brands(condition,brands,year,limit=8):
    if not condition: return []
    from django.db.models import OuterRef,Subquery
    from brands.models import AnnualStat
    stats=AnnualStat.objects.filter(brand=OuterRef('pk'),year=year)
    qs=brands.annotate(analysis_cost=Subquery(stats.values('startup_cost_krw')[:1]))
    if condition.category and condition.category != '전체': qs=qs.filter(category=condition.category)
    # 적합도가 검증되지 않았으므로 점수를 만들지 않고 예산 확인 가능 후보를 먼저 정렬합니다.
    qs=qs.order_by('name','id')
    results=[]
    for brand in qs:
        cost=brand.analysis_cost
        if cost is None: cost=brand.initial_cost_krw
        known=sum(v for v in [condition.deposit_manwon,condition.premium_manwon,condition.reserve_manwon] if v is not None)*10000
        if cost is not None and cost+known > condition.total_budget_manwon*10000: continue
        op=BrandOperation.objects.filter(brand=brand).first()
        warnings=[]; reasons=[]
        if cost is None: warnings.append('창업 부담금 미확인')
        else: reasons.append(f'공시 창업 부담금 {cost//10000:,}만원: 총예산에서 확인된 보증금·권리금·운영자금을 뺀 범위 이내')
        if any(v is None for v in [condition.deposit_manwon,condition.premium_manwon,condition.reserve_manwon]): warnings.append('보증금·권리금·운영자금 일부 미입력: 전체 비용 적합성 미확인')
        if op:
            sqm=condition.area * (Decimal('3.305785') if condition.area_unit=='pyeong' else 1) if condition.area is not None else None
            if sqm is not None and op.minimum_area_sqm is not None and sqm < op.minimum_area_sqm: continue
            if condition.staff_count is not None and op.required_staff is not None and condition.staff_count < op.required_staff: continue
            if condition.operation=='staff' and op.staff_operation_allowed is False: continue
            if condition.channels and op.channels and not set(condition.channels).issubset(op.channels): continue
            if op.minimum_area_sqm is not None and sqm is not None: reasons.append('확인된 최소 면적 충족')
            if op.required_staff is not None and condition.staff_count is not None: reasons.append('확인된 필요 인원 충족')
            warnings.append('본사 출점 승인·영업시간 확인 필요')
            if op.restrictions: warnings.append(op.restrictions)
            source=f'{op.source.name} / 확인일 {op.checked_on}'
        else:
            warnings.append('브랜드 가격대·면적·인력·운영 조건 미등록')
            source='운영 조건 출처 미등록'
        warnings.append('지역 소비·경쟁 적합성 판단 보류. 전국 평균매출은 동네 예상매출이 아닙니다.')
        results.append({'brand':brand,'reasons':reasons,'warnings':warnings,'source':source,'cost_known':cost is not None,'cost_manwon':cost/10000 if cost is not None else None})
        if len(results)>=limit*4: break
    results.sort(key=lambda x:(not x['cost_known'],x['brand'].name))
    return results[:limit]


def analysis_context(condition,brands,year):
    area,note=selected_area(condition)
    metrics=[]; sales=[]; trends=[]
    if area:
        for kind,label in [('floating','유동인구'),('resident','상주인구·가구'),('worker','직장인구')]:
            stat=PopulationStat.objects.filter(area=area,kind=kind).select_related('source').order_by('-period').first()
            metrics.append({'label':label,'stat':stat})
        sales=IndustrySales.objects.filter(area=area).select_related('industry','source').order_by('-period','industry__name')[:12]
        trends=StoreTrend.objects.filter(area=area).select_related('industry','source').order_by('-period','industry__name')[:12]
    else: metrics=[{'label':label,'stat':None} for label in ['유동인구','상주인구·가구','직장인구']]
    age_groups=[]
    age_stat=next((m['stat'] for m in metrics if m['stat'] and m['stat'].kind=='floating'),None)
    if age_stat and isinstance(age_stat.by_age,dict):
        values=[(str(k),v) for k,v in age_stat.by_age.items() if isinstance(v,(int,float)) and not isinstance(v,bool) and v>=0]
        denominator=sum(v for _,v in values)
        age_groups=[{'label':k,'value':v,'width':round(v/denominator*100,1) if denominator else 0} for k,v in values]
    cards = [population_card(metric) for metric in metrics]
    return {'floating_card': cards[0], 'focus_population_cards': cards[1:], 'public_store_summary':area_store_summary(area,condition),'age_groups':age_groups,'age_stat':age_stat,'condition':condition,'analysis_area':area,'area_note':note,'population_metrics':metrics,'industry_sales':sales,'store_trends':trends,'analysis_candidates':candidate_brands(condition,brands,year)}

@login_required
@require_GET
def area_geometry(request):
    condition=StartupCondition.objects.filter(user=request.user).first()
    area,note=selected_area(condition)
    return JsonResponse({'geometry':area.boundary if area else None,'name':area.name if area else None,'note':note,'verified':bool(area and area.verified)})


def population_card(metric):
    """원본 수치만 표시하며 부분 누락이 있는 분포의 비율은 만들지 않습니다."""
    stat = metric['stat']
    def entries(data):
        if not isinstance(data, dict):
            return []
        return [{'label': str(k), 'value': v} for k, v in data.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0]
    age_data = stat.by_age if stat else {}
    ages = entries(age_data)
    denominator = sum(item['value'] for item in ages)
    complete = isinstance(age_data, dict) and len(ages) == len(age_data)
    top = sorted(ages, key=lambda item: item['value'], reverse=True)[:2] if denominator and complete else []
    for item in top:
        item['width'] = round(item['value'] / denominator * 100, 1)
    day_data = stat.by_day if stat and isinstance(stat.by_day, dict) else {}
    # 해석이 명확한 주중/주말 쌍 또는 월~일의 완전한 세트만 합산합니다.
    days = []
    for weekday, weekend in [('weekday', 'weekend'), ('주중', '주말')]:
        if set(day_data) == {weekday, weekend} and len(entries(day_data)) == 2:
            days = [{'label': '주중', 'value': day_data[weekday]}, {'label': '주말', 'value': day_data[weekend]}]
            break
    for keys in [('mon','tue','wed','thu','fri','sat','sun'), ('월','화','수','목','금','토','일')]:
        if set(day_data) == set(keys) and len(entries(day_data)) == 7:
            days = [{'label': '주중', 'value': sum(day_data[k] for k in keys[:5])}, {'label': '주말', 'value': sum(day_data[k] for k in keys[5:])}]
    day_total = sum(item['value'] for item in days)
    for item in days:
        item['width'] = round(item['value'] / day_total * 100, 1) if day_total else 0
    if not day_total:
        days = []
    return dict(metric, top_ages=top, days=days, breakdowns=[
        {'label': '연령별 원자료', 'items': ages},
        {'label': '요일별 원자료', 'items': entries(day_data)},
        {'label': '시간대별 원자료', 'items': entries(stat.by_time if stat else {})}])
