from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from .views import context_for, brand_row
from .models import StartupCost


class CalculatorForm(forms.Form):
    brand = forms.ChoiceField(label='기준 브랜드')
    investment = forms.IntegerField(label='초기 투자금', min_value=0, max_value=100000000)
    sales = forms.IntegerField(label='예상 월 매출', min_value=0, max_value=100000000)
    rent = forms.IntegerField(label='월세', min_value=0, max_value=100000000)
    labor = forms.IntegerField(label='월 인건비', min_value=0, max_value=100000000)
    other = forms.IntegerField(label='기타 월 고정비', min_value=0, max_value=100000000, required=False, help_text='선택 입력 · 미입력 시 0만원(비용 제외). 공과금·점주 급여·이자·세금 적립 등 포함할 비용의 합계')
    variable_rate = forms.IntegerField(label='변동비율', min_value=0, max_value=100, required=False, help_text='선택 입력 · 미입력 시 0%(비용 제외). 원재료·로열티·카드/배달 수수료 등 매출 연동 비용 합계')
    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['brand'].choices = choices
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
    choices = [(b.slug, b.name) for b in context['all_brands']]
    slug = request.POST.get('brand', request.GET.get('brand', choices[0][0] if choices else ''))
    brand = next((b for b in context['all_brands'] if b.slug == slug), None)
    initial = {'brand': slug}
    row = brand_row(brand, context['year']) if brand else None
    if row:
        if row['stat'] and row['stat'].annual_sales_krw is not None:
            initial['sales'] = int((Decimal(row['stat'].annual_sales_krw) / 12 / 10000).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
            # 1. 선택한 브랜드와 연도의 신규 창업비용 조회
            costs = list(
                StartupCost.objects.filter(
                    brand=brand,
                    year=context['year']
                ).values_list('item__code', 'amount_krw')
            )

            investment_krw = None

            # 2. 신규 데이터가 존재하면 4개 항목 합산
            if costs:
                amounts = dict(costs)

                required_codes = {
                    'franchise_fee_krw',
                    'education_fee_krw',
                    'guarantee_deposit_krw',
                    'other_cost_krw'
                }

                if required_codes.issubset(amounts) and all(
                    amounts[code] is not None for code in required_codes
                ):
                    investment_krw = sum(
                        amounts[code] for code in required_codes
                    )

            # 3. 신규 데이터가 없을 경우 기존 연도별 데이터 사용
            else:
                history = brand.costs.get('history', [])
                selected = next(
                    (item for item in history if item.get('year') == context['year']),
                    None
                )

                if selected is not None:
                    investment_krw = selected.get('startup_cost_krw')
                elif brand.is_demo:
                    investment_krw = brand.initial_cost_krw

            # 4. 원 단위를 만원 단위로 변환
            if investment_krw is not None:
                initial['investment'] = int(
                    (Decimal(investment_krw) / 10000).quantize(
                        Decimal('1'),
                        rounding=ROUND_HALF_UP
                    )
                )
    form = CalculatorForm(request.POST if request.method == 'POST' else None, initial=initial, choices=choices)
    result = calculate(form.cleaned_data) if request.method == 'POST' and form.is_valid() else None
    context.update(page='calculator', form=form, result=result, calculator_brand=brand, row=row)
    return render(request, 'calculator.html', context)
