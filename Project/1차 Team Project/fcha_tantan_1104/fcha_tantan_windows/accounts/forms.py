import re
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from django.utils import timezone
from brands.constants import REGIONS
from .email_verify import verified_email
from .models import MemberProfile

# 창업 목적일 때만 묻는 항목(화면에서는 ‘예’를 고르면 펼쳐집니다)
STARTUP_FIELDS = ['startup_purpose', 'budget_manwon', 'target_monthly_sales_manwon', 'desired_region', 'desired_category', 'agree_proposal']
STARTUP_REQUIRED = []


def normalize_phone(value):
    digits = re.sub(r'\D', '', value or '')
    if not re.fullmatch(r'01[016789]\d{7,8}', digits):
        raise forms.ValidationError('휴대전화 번호를 확인해주세요. 예: 010-1234-5678')
    return f'{digits[:3]}-{digits[3:-4]}-{digits[-4:]}'


class ProfileFieldsMixin(forms.Form):
    """회원가입과 프로필 수정에서 함께 쓰는 입력 항목입니다. 주민등록번호는 받지 않습니다."""
    email = forms.EmailField(label='이메일', widget=forms.EmailInput(attrs={'autocomplete': 'email', 'data-email-input': '1'}),
                             help_text='인증번호를 받아 입력한 뒤 ‘인증 확인’을 눌러주세요.')
    phone = forms.CharField(label='휴대전화', max_length=13,
                            widget=forms.TextInput(attrs={'inputmode': 'tel', 'placeholder': '010-1234-5678', 'autocomplete': 'tel'}))
    postcode = forms.CharField(label='우편번호', max_length=5, widget=forms.TextInput(attrs={'readonly': True, 'data-postcode': 'postcode'}))
    address = forms.CharField(label='주소', max_length=200, widget=forms.TextInput(attrs={'readonly': True, 'data-postcode': 'address'}),
                              help_text='주소 검색 버튼으로 입력합니다.')
    address_detail = forms.CharField(label='상세주소', max_length=100, required=False, widget=forms.TextInput(attrs={'data-postcode': 'detail'}))
    wants_startup = forms.ChoiceField(label='창업을 목적으로 가입하시나요?', widget=forms.RadioSelect(attrs={'data-startup-toggle': '1'}),
                                      choices=[('yes', '예, 창업을 준비하고 있어요'), ('no', '아니요 (정보 탐색·가맹점 운영·브랜드 담당 등)')])
    startup_purpose = forms.ChoiceField(label='창업 방식', required=False, choices=[('', '선택하세요')] + MemberProfile.PURPOSES)
    budget_manwon = forms.IntegerField(label='창업 예산 (만원)', min_value=0, max_value=1000000, required=False,
                                       widget=forms.NumberInput(attrs={'inputmode': 'numeric', 'step': 1}),
                                       help_text='정보공개서 창업 부담금(가맹비·교육비·보증금·기타) 기준으로 비교합니다. 임대보증금·권리금은 별도입니다.')
    target_monthly_sales_manwon = forms.IntegerField(label='목표 월 매출 (만원)', min_value=0, max_value=1000000, required=False,
                                                     widget=forms.NumberInput(attrs={'inputmode': 'numeric', 'step': 1}))
    desired_region = forms.ChoiceField(label='희망 지역', required=False, choices=[('', '선택하세요')] + [(r, r) for r in REGIONS])
    desired_category = forms.ChoiceField(label='희망 업종', required=False, choices=[('전체', '전체 업종')], initial='전체',
                                         help_text='외식·서비스·도소매 안의 세부 업종을 고르세요. 정하지 않았다면 ‘전체 업종’.')
    agree_marketing = forms.BooleanField(label='[선택] 이벤트·혜택 등 마케팅 정보 수신에 동의합니다.', required=False)
    agree_proposal = forms.BooleanField(
        label='[선택] 브랜드 사업제안 수신에 동의합니다. 닉네임·희망 지역·업종·예산·목표 매출·창업 방식을 승인된 브랜드 파트너에게 제공하며, 연락처는 내가 제안을 수락할 때만 공개됩니다.',
        required=False)

    startup_names = STARTUP_FIELDS

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        # 업종 목록은 DB에 들어온 브랜드 기준(대분류별 묶음)입니다.
        from brands.categories import all_category_choices
        self.fields['desired_category'].choices = all_category_choices()
        from market.analysis_forms import StartupConditionForm
        condition_form = StartupConditionForm()
        for name, field in condition_form.fields.items():
            import copy
            field = copy.deepcopy(field)
            field.required = False
            self.fields['plan_' + name] = field
        self.startup_names = STARTUP_FIELDS + ['plan_' + n for n in condition_form.fields]


    @property
    def startup_fields(self):
        from market.analysis_forms import BASIC
        return [self['plan_' + name] for name in BASIC]

    @property
    def startup_detail_fields(self):
        from market.analysis_forms import DETAIL
        return [self['plan_' + name] for name in DETAIL] + [self[n] for n in ('startup_purpose','agree_proposal')]


    def current_user(self):
        return getattr(self, 'profile_user', None)

    def email_already_verified(self, email):
        # 지금 쓰는 이메일을 이미 인증했다면(내 정보 수정) 다시 인증하지 않아도 됩니다.
        user = self.current_user()
        if user is None or not user.pk or (user.email or '').lower() != email:
            return False
        profile = MemberProfile.objects.filter(user=user).first()
        return bool(profile and profile.email_verified_at)

    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        users = get_user_model().objects.filter(email__iexact=email)
        user = self.current_user()
        if user is not None and user.pk:
            users = users.exclude(pk=user.pk)
        if users.exists():
            raise forms.ValidationError('이미 가입된 이메일입니다.')
        self.email_newly_verified = False
        if not self.email_already_verified(email):
            if self.request is None or verified_email(self.request) != email:
                raise forms.ValidationError('이메일 인증을 완료해주세요. (인증번호 받기 → 입력 → 인증 확인)')
            self.email_newly_verified = True
        return email

    def clean(self):
        data = super().clean()
        if data.get('wants_startup') == 'yes':
            from market.analysis_forms import StartupConditionForm
            payload = self.data.copy()
            for name in StartupConditionForm().fields:
                key = 'plan_' + name
                if hasattr(self.data, 'getlist'):
                    payload.setlist(name, self.data.getlist(key))
                else:
                    payload[name] = self.data.get(key)
            self.condition_form = StartupConditionForm(payload)
            if not self.condition_form.is_valid():
                for name, errors in self.condition_form.errors.items():
                    for error in errors:
                        self.add_error('plan_' + name if name != '__all__' else None, error)
            for name in STARTUP_REQUIRED:
                if data.get(name) in (None, ''):
                    self.add_error(name, '창업 목적이면 꼭 입력해주세요.')
        else:
            # 창업 목적이 아니면 창업 조건은 저장하지 않습니다.
            for name in STARTUP_FIELDS:
                data[name] = False if name == 'agree_proposal' else ('' if name not in ('budget_manwon', 'target_monthly_sales_manwon') else None)
        return data

    def save_profile(self, user, source='local'):
        data = self.cleaned_data
        profile, _ = MemberProfile.objects.get_or_create(user=user, defaults={'signup_source': source})
        now = timezone.now()
        profile.wants_startup = data['wants_startup'] == 'yes'
        for key in ('phone', 'postcode', 'address', 'address_detail', 'startup_purpose', 'budget_manwon',
                    'target_monthly_sales_manwon', 'desired_region', 'desired_category', 'agree_marketing'):
            if key in ('budget_manwon','target_monthly_sales_manwon','desired_region','desired_category') and key not in self.data:
                continue  # 새 입력 화면에서 받지 않는 기존 값은 보존합니다.
            setattr(profile, key, data[key])
        if data['agree_proposal'] and not profile.agree_proposal:
            profile.agree_proposal_at = now
        profile.agree_proposal = data['agree_proposal']
        if profile.agree_privacy_at is None:
            profile.agree_privacy_at = now
        if getattr(self, 'email_newly_verified', False):
            profile.email_verified_at = now
        profile.is_complete = True
        profile.save()
        if data['wants_startup'] == 'yes' and hasattr(self, 'condition_form'):
            from market.analysis_models import StartupCondition
            StartupCondition.objects.update_or_create(user=user, defaults=self.condition_form.cleaned_data)

        user.email = data['email']
        if 'first_name' in data:
            user.first_name = data['first_name']
        user.save(update_fields=['email', 'first_name'])
        return profile


PRIVACY_LABEL = '[필수] 개인정보 수집·이용에 동의합니다. (이메일·휴대전화·주소·창업 조건 / 회원 관리·맞춤 추천 / 탈퇴 시까지 보관)'
PROFILE_ORDER = ['phone', 'postcode', 'address', 'address_detail', 'wants_startup'] + STARTUP_FIELDS + ['agree_privacy', 'agree_marketing']


class SignupForm(ProfileFieldsMixin, UserCreationForm):
    first_name = forms.CharField(label='닉네임', max_length=30)
    agree_privacy = forms.BooleanField(label=PRIVACY_LABEL)
    field_order = ['username', 'first_name', 'email', 'password1', 'password2'] + PROFILE_ORDER
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'first_name', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = '아이디'

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            self.save_profile(user)
        return user


class ProfileForm(ProfileFieldsMixin):
    """간편로그인 후 추가 정보 입력 + 내 정보 수정."""
    first_name = forms.CharField(label='닉네임', max_length=30)
    agree_privacy = forms.BooleanField(label=PRIVACY_LABEL)
    field_order = ['first_name', 'email'] + PROFILE_ORDER

    def __init__(self, *args, user=None, **kwargs):
        self.profile_user = user
        super().__init__(*args, **kwargs)


def profile_initial(user):
    profile = getattr(user, 'member_profile', None)
    initial = {'first_name': user.first_name, 'email': user.email}
    if profile:
        for key in ('phone', 'postcode', 'address', 'address_detail', 'startup_purpose', 'budget_manwon',
                    'target_monthly_sales_manwon', 'desired_region', 'desired_category', 'agree_marketing', 'agree_proposal'):
            initial[key] = getattr(profile, key)
        if profile.wants_startup is not None:
            initial['wants_startup'] = 'yes' if profile.wants_startup else 'no'
        elif profile.budget_manwon is not None:
            initial['wants_startup'] = 'yes'  # 예전 가입자(창업 조건만 있는 경우)
        initial['agree_privacy'] = profile.agree_privacy_at is not None
    condition = getattr(user, 'startup_condition', None)
    if condition:
        from market.analysis_forms import StartupConditionForm
        initial.update({'plan_' + name: getattr(condition, name) for name in StartupConditionForm().fields})
    return initial


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='아이디', widget=forms.TextInput(attrs={'autocomplete':'username'}))
