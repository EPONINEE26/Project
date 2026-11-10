from decimal import Decimal
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET
from .analysis_forms import StartupConditionForm
from .analysis_models import StartupCondition, CommercialArea, PopulationStat, IndustrySales, StoreTrend, PublicStore, BrandOperation


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
    matches=[a for a in CommercialArea.objects.filter(verified=True) if contains(a.boundary,condition.longitude,condition.latitude)]
    if len(matches)!=1: return None, '공식 상권이 없거나 여러 경계·버전이 겹칩니다. 코드·경계 검증 후 분석합니다.'
    return matches[0], ''


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
    return {'age_groups':age_groups,'age_stat':age_stat,'condition':condition,'analysis_area':area,'area_note':note,'population_metrics':metrics,'industry_sales':sales,'store_trends':trends,'analysis_candidates':candidate_brands(condition,brands,year)}

@login_required
@require_GET
def area_geometry(request):
    condition=StartupCondition.objects.filter(user=request.user).first()
    area,note=selected_area(condition)
    return JsonResponse({'geometry':area.boundary if area else None,'name':area.name if area else None,'note':note})
