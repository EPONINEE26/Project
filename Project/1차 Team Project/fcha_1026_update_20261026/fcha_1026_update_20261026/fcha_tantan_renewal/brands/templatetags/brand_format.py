from django import template
register = template.Library()

@register.filter
def number(value):
    return '미제공' if value is None or value == '' else format(value, ',')

@register.filter
def money(value):
    return '미제공' if value is None or value == '' else f'{round(value / 10000):,}만원'
