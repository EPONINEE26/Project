from django import template
import re


register = template.Library()

@register.filter
def number(value):
    return '미제공' if value is None or value == '' else format(value, ',')

@register.filter
def money(value):
    return '미제공' if value is None or value == '' else f'{round(value / 10000):,}만원'

#  브랜드 이름에 특수기호 삭제
@register.filter
def clean_brand_name(value):
    if value is None:
        return ''
    return re.sub(r'[^가-힣ㄱ-ㅎㅏ-ㅣa-zA-Z0-9\s]', '', str(value)).strip()

