from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .maps import public_stores,filtered_stores

@login_required
@require_GET
def locations(request):
    qs=filtered_stores(request)
    located=qs.exclude(latitude=None).exclude(longitude=None)
    points=[{'id':s.pk,'name':s.brand.name,'brand':s.brand.name,'lat':float(s.latitude),'lng':float(s.longitude),'area':f'{s.sido} {s.sigungu} {s.dong}'} for s in located[:500]]
    counts=list(qs.values('brand__name').annotate(total=Count('id')).order_by('-total')[:20])
    return JsonResponse({'points':points,'total':qs.count(),'located':located.count(),'limit':500,'counts':counts,'source':'verified_owner_public_locations'},json_dumps_params={'ensure_ascii':False})

@login_required
@require_GET
def area_options(request):
    qs=public_stores()
    if request.GET.get('region'):qs=qs.filter(sido=request.GET['region'])
    districts=list(qs.exclude(sigungu='').order_by('sigungu').values_list('sigungu',flat=True).distinct())
    if request.GET.get('sigungu'):qs=qs.filter(sigungu=request.GET['sigungu'])
    dongs=list(qs.exclude(dong='').order_by('dong').values_list('dong',flat=True).distinct())
    return JsonResponse({'districts':districts,'dongs':dongs,'source':'registered_stores','manual_entry_allowed':True},json_dumps_params={'ensure_ascii':False})
