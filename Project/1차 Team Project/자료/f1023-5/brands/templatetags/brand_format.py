from django import template
register = template.Library()

@register.filter
def number(value):
    return '미제공' if value is None or value == '' else format(value, ',')

# @register.filter
# def money(value):
#     return '미제공' if value is None or value == '' else f'{round(value / 10000):,}만원'

@register.filter
def money(value):
    # 값이 없으면 미제공
    if value is None or value == '':
        return '미제공'

    # 딕셔너리는 숫자로 계산할 수 없으므로 별도 처리
    if isinstance(value, dict):
        return '미제공'

    # 숫자가 아닌 값도 안전하게 처리
    try:
        return f'{round(float(value) / 10000):,}만원'
    except (TypeError, ValueError):
        return '미제공'