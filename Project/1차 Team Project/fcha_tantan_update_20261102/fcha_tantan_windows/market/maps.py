from django.db.models import Exists,OuterRef,Q
from django.utils import timezone
from brands.models import OwnerVerification
from .models import StoreLocation


def public_stores():
    verified=OwnerVerification.objects.filter(user_id=OuterRef('owner_id'),brand_id=OuterRef('brand_id'),status='approved').filter(Q(contract_end_date__isnull=True)|Q(contract_end_date__gte=timezone.localdate()))
    return StoreLocation.objects.filter(is_public=True,status__in=['operating','transfer']).annotate(owner_verified=Exists(verified)).filter(owner_verified=True).select_related('brand')


def filtered_stores(request, region=None):
    qs=public_stores()
    for key,parameter in [('sido','region'),('sigungu','sigungu'),('dong','dong')]:
        value=(region if parameter=='region' and region is not None else request.GET.get(parameter,'')).strip()
        if value:qs=qs.filter(**{key:value})
    category=request.GET.get('category','전체');query=request.GET.get('query','').strip()
    if category!='전체':qs=qs.filter(brand__category=category)
    if query:qs=qs.filter(brand__name__icontains=query)
    return qs


def listing_point(item):
    if item.latitude is None or item.longitude is None:return None
    places=6 if item.exact_location_public else 3
    return {'id':item.pk,'lat':round(float(item.latitude),places),'lng':round(float(item.longitude),places),
            'name':item.title,'brand':item.brand.name,'price':item.premium_manwon,
            'label':f'{item.sido} {item.sigungu} {item.dong}',
            'exact':item.exact_location_public,'url':f'/market/transfer/{item.pk}/'}
