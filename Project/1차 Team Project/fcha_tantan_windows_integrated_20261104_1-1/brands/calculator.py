from collections import defaultdict
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .views import context_for, brand_row
from .lookup import find_brand, lookup_label

class CalculatorForm(forms.Form):
    brand = forms.ChoiceField(label='기준 브랜드', required=False)
    investment = forms.IntegerField(label='초기 투자금', min_value=0, max_value=100000000)
    sales = forms.IntegerField(label='예상 월 매출', min_value=0, max_value=100000000)
    rent = forms.IntegerField(label='월세', min_value=0, max_value=100000000)
    labor = forms.IntegerField(label='월 인건비', min_value=0, max_value=100000000)
    other = forms.IntegerField(label='기타 월 고정비', min_value=0, max_value=100000000, required=False, help_text='선택 입력 · 미입력 시 0만원(비용 제외). 공과금·점주 급여·이자·세금 적립 등 포함할 비용의 합계')
    variable_rate = forms.IntegerField(label='변동비율', min_value=0, max_value=100, required=False, help_text='선택 입력 · 미입력 시 0%(비용 제외). 원재료·로열티·카드/배달 수수료 등 매출 연동 비용 합계')
    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].choices = choices
        # 브랜드는 위쪽 ‘참고값 불러오기’ 검색칸에서 고르고, 여기서는 숨김값으로만 보냅니다.
        self.fields['brand'].widget = forms.HiddenInput()
        for key, field in self.fields.items():
            if key != 'brand': field.widget.attrs.update(step='1', inputmode='numeric')

    def clean_other(self):
        return self.cleaned_data['other'] or 0

    def clean_variable_rate(self):
        return self.cleaned_data['variable_rate'] or 0

def calculate(values):
    # Keep arithmetic exact even though form inputs are whole numbers.
    values = {key: Decimal(str(values[key])) for key in ('investment','sales','rent','labor','other','variable_rate')}
    fixed = values['rent'] + values['labor'] + values['other']
    contribution = Decimal('1') - values['variable_rate'] / 100
    variable = values['sales'] * values['variable_rate'] / 100
    profit = values['sales'] - fixed - variable
    bep = fixed / contribution if contribution > 0 else None
    exact_months = values['investment'] / profit if profit > 0 else None
    months = int(exact_months.to_integral_value(rounding=ROUND_CEILING)) if exact_months is not None else None
    return {'fixed': fixed, 'variable': variable, 'profit': profit, 'bep': bep, 'months': months,
            'investment': values['investment'], 'sales': values['sales'], 'rate': values['variable_rate']}

@login_required
@require_http_methods(['GET','POST'])
def calculator(request):
    context = context_for(request)
    # Load every real brand once; preserve names from Brand.name without display cleanup.
    options = list(context['all_brands'].order_by('category','name','id').values('slug','name','category','company'))
    choices = [('', '선택 안 함 · 직접 입력')] + [(item['slug'],item['name']) for item in options]
    groups = defaultdict(list)
    for item in options: groups[item['category'] or '미분류'].append(item)
    grouped_options = [{'name':key,'brands':items} for key,items in groups.items()]
    raw = request.POST.get('brand', request.GET.get('brand', ''))
    brand = find_brand(raw, context['all_brands'])
    slug = brand.slug if brand else ''
    initial = {'brand': slug}
    row = brand_row(brand, context['year']) if brand else None
    if row:
        if row['stat'] and row['stat'].annual_sales_krw is not None:
            initial['sales'] = int((Decimal(row['stat'].annual_sales_krw) / 12 / 10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        if brand.initial_cost_krw is not None: initial['investment'] = int((Decimal(brand.initial_cost_krw) / 10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    form = CalculatorForm(request.POST if request.method == 'POST' else None, initial=initial, choices=choices)
    result = calculate(form.cleaned_data) if request.method == 'POST' and form.is_valid() else None
    context.update(page='calculator', form=form, result=result, calculator_brand=brand, row=row,
                   brand_lookup_value=lookup_label(brand) if brand else '', calculator_options=options, calculator_groups=grouped_options, calculator_brand_count=len(options))
    return render(request, 'calculator.html', context)
