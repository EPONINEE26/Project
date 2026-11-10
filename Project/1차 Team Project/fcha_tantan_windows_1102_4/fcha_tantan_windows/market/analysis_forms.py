from django import forms
from .analysis_models import StartupCondition

BASIC = ['location','store_status','total_budget_manwon','operation']
DETAIL = [f.name for f in StartupCondition._meta.fields if f.name not in ['id','user','updated_at'] + BASIC]
class StartupConditionForm(forms.ModelForm):
    channels = forms.MultipleChoiceField(label='판매 방식', choices=[('hall','홀'),('takeout','포장'),('delivery','배달')], required=False, widget=forms.CheckboxSelectMultiple)
    available_slots = forms.MultipleChoiceField(label='본인 투입 가능 시간 (영업시간과 별개)',choices=[('morning','오전'),('lunch','점심'),('afternoon','오후'),('evening','저녁'),('night','심야')],required=False,widget=forms.CheckboxSelectMultiple)
    target_ages = forms.MultipleChoiceField(label='주 고객 연령대', choices=[('10','10대'),('20','20대'),('30','30대'),('40','40대'),('50','50대'),('60','60대 이상')], required=False, widget=forms.CheckboxSelectMultiple)
    preferred_area_types = forms.MultipleChoiceField(label='선호 상권', choices=[('office','회사밀집'),('residential','주거밀집'),('retail','상가밀집')], required=False, widget=forms.CheckboxSelectMultiple)
    class Meta:
        model=StartupCondition
        exclude=['user','updated_at']
        widgets={'opening_date':forms.DateInput(attrs={'type':'date'})}
    def __init__(self,*args,**kwargs):
        if args and args[0] is not None:
            data=args[0].copy()
            for name,value in [('location_scope','dong'),('area_unit','pyeong'),('radius_m',500)]:
                if not data.get(name): data[name]=value
            args=(data,)+args[1:]
        super().__init__(*args,**kwargs)
        from brands.categories import all_category_choices
        self.fields['category']=forms.ChoiceField(label='희망 업종',required=False,choices=all_category_choices())
    @property
    def basic_fields(self): return [self[n] for n in BASIC]
    @property
    def detail_fields(self): return [self[n] for n in DETAIL]
    def clean(self):
        d=super().clean()
        if (d.get('latitude') is None) != (d.get('longitude') is None):
            self.add_error('latitude','위도와 경도를 함께 입력해주세요.')
        return d


class RegionConditionForm(StartupConditionForm):
    """지역 분석에서 받지 않는 조건은 저장된 값을 그대로 유지합니다."""
    class Meta(StartupConditionForm.Meta):
        exclude = StartupConditionForm.Meta.exclude + [
            'operation', 'management_manwon', 'deposit_manwon', 'premium_manwon',
            'experience', 'can_cook', 'opening_date',
        ]

    @property
    def basic_fields(self):
        return [self[name] for name in BASIC if name in self.fields]

    @property
    def detail_fields(self):
        return [self[name] for name in DETAIL if name in self.fields]

    def save(self, commit=True):
        if not self.instance.operation:
            self.instance.operation = 'unknown'
        return super().save(commit=commit)
