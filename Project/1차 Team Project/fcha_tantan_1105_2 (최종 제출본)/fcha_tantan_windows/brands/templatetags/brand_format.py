from django import template
import re


register = template.Library()

@register.filter
def number(value):
    return '미제공' if value is None or value == '' else format(value, ',')

@register.filter
def money(value):
    return '미제공' if value is None or value == '' else f'{round(value / 10000):,}만원'

# 업종 드롭다운 아이콘 (brands/constants.py CATEGORY_ICONS · 묶음 아이콘)
@register.filter
def category_icon(value):
    from brands.constants import icon_for
    return icon_for(value)

# 커뮤니티 작성자 표시: 승인된 점주 인증의 가맹점명으로 '브랜드 ○○점 점주'
@register.filter
def owner_label(item):
    cached = getattr(item, '_owner_label', None)
    if cached is not None:
        return cached
    from brands.models import OwnerVerification
    if not item.brand_id:
        item._owner_label = '예비 창업주'  # 점주 인증 없이 창업 목적 회원으로 작성
        return item._owner_label
    brand = clean_brand_name(item.brand.name)
    store = (OwnerVerification.objects.filter(user_id=item.author_id, brand_id=item.brand_id, status='approved')
             .order_by('-reviewed_at', '-submitted_at').values_list('store_name', flat=True).first() or '').strip()
    if not store:
        label = f'{brand} 점주'
    elif brand.replace(' ', '') in store.replace(' ', ''):
        label = f'{store} 점주'  # 가맹점명에 이미 브랜드명이 들어 있으면 반복하지 않음
    else:
        label = f'{brand} {store} 점주'
    item._owner_label = label
    return label

#  브랜드 이름에 특수기호 삭제
@register.filter
def clean_brand_name(value):
    if value is None:
        return ''
    return re.sub(r'[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9\s]', '', str(value)).strip()

