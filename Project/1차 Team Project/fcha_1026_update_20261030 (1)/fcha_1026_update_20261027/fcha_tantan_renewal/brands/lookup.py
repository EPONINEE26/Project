"""브랜드 검색 입력칸. 12,000여 개 브랜드를 드롭다운으로 내려보내지 않고 입력한 글자로 찾습니다.

입력값 형식: "브랜드명 (slug)" — 자동완성에서 고르면 이 형식이 들어갑니다. 브랜드명이 하나뿐이면 이름만 써도 됩니다.
"""
import re
from django import forms
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .models import Brand

SLUG_AT_END = re.compile(r'\(([-\w]+)\)\s*$')


def lookup_label(brand):
    return f'{brand.name} ({brand.slug})'


def find_brand(value, queryset):
    value = (value or '').strip()
    if not value:
        return None
    match = SLUG_AT_END.search(value)
    if match:
        return queryset.filter(slug=match.group(1)).first()
    exact = list(queryset.filter(name=value)[:2]) or list(queryset.filter(slug=value)[:2])
    return exact[0] if len(exact) == 1 else None


class BrandLookupField(forms.Field):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', '브랜드')
        kwargs.setdefault('help_text', '브랜드명을 입력하고 목록에서 고르세요.')
        kwargs.setdefault('widget', forms.TextInput(attrs={'data-brand-lookup': '1', 'autocomplete': 'off',
                                                           'placeholder': '브랜드명 검색'}))
        super().__init__(*args, **kwargs)

    def queryset(self):
        from .views import visible_brands
        return visible_brands()

    def prepare_value(self, value):
        if isinstance(value, Brand):
            return lookup_label(value)
        if isinstance(value, int) or (isinstance(value, str) and value.isdigit()):
            brand = Brand.objects.filter(pk=int(value)).first()
            return lookup_label(brand) if brand else ''
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        brand = find_brand(value, self.queryset())
        if brand is None:
            raise forms.ValidationError('목록에서 브랜드를 골라주세요. 같은 이름이 여러 개면 괄호 안 식별자로 구분됩니다.')
        return brand


@require_GET
def brand_lookup(request):
    # 공개 정보(이름·업종·회사)만 돌려줍니다.
    from .views import visible_brands
    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'results': []})
    brands = visible_brands().filter(name__icontains=query).order_by('name')[:20]
    return JsonResponse({'results': [{'value': lookup_label(b), 'label': f'[{b.category}] {b.company}'.strip()} for b in brands]},
                        json_dumps_params={'ensure_ascii': False})
