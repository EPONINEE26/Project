from datetime import timedelta
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST, require_GET
from accounts.forms import normalize_phone
from accounts.models import MemberProfile
from brands.constants import REGIONS
from core.documents import validate_evidence, precheck
from brands.lookup import BrandLookupField
from brands.views import context_for
from .models import BusinessProposal, PartnerAccount, PartnerInquiry, PartnerPlan

DEFAULT_PROPOSAL_LIMIT = 5


class InquiryForm(forms.ModelForm):
    agree_privacy = forms.BooleanField(label='[필수] 상담을 위한 개인정보(담당자명·연락처·이메일) 수집·이용에 동의합니다. 상담 종료 후 1년간 보관합니다.')
    class Meta:
        model = PartnerInquiry
        fields = ('company', 'brand_name', 'contact_name', 'phone', 'email', 'plan', 'ad_position', 'cpc_bid_krw', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 4})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = PartnerPlan.objects.filter(is_active=True)
    def clean(self):
        data = super().clean()
        position, bid = data.get('ad_position'), data.get('cpc_bid_krw')
        if position and (bid is None or bid < 1):
            self.add_error('cpc_bid_krw', '광고 문의는 1원 이상의 희망 CPC를 입력해주세요.')
        if bid is not None and not position:
            self.add_error('ad_position', '입찰할 광고 구좌를 선택해주세요.')
        return data
    def clean_phone(self):
        return normalize_phone(self.cleaned_data['phone'])


class PartnerApplyForm(forms.ModelForm):
    business_file = forms.FileField(label='사업자등록증', validators=[validate_evidence], help_text='PDF·JPG·PNG, 최대 10MB')
    authorization_file = forms.FileField(label='본사 재직·권한 증빙', validators=[validate_evidence], help_text='재직증명서 또는 위임장. PDF·JPG·PNG, 최대 10MB')
    brand = BrandLookupField(help_text='담당하는 브랜드명을 입력하고 목록에서 고르세요.')
    class Meta:
        model = PartnerAccount
        fields = ('brand', 'company', 'contact_name', 'contact_phone', 'business_number', 'plan', 'business_file', 'authorization_file')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['plan'].queryset = PartnerPlan.objects.filter(is_active=True)
    def clean_contact_phone(self):
        return normalize_phone(self.cleaned_data['contact_phone'])
    def clean_business_number(self):
        digits = ''.join(ch for ch in self.cleaned_data['business_number'] if ch.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError('사업자등록번호 10자리를 입력해주세요.')
        return f'{digits[:3]}-{digits[3:5]}-{digits[5:]}'


class ProposalForm(forms.ModelForm):
    class Meta:
        model = BusinessProposal
        fields = ('title', 'message')
        widgets = {'message': forms.Textarea(attrs={'rows': 5, 'maxlength': 2000})}


# 화면 출력: partners/pricing.html · 조회 데이터: PartnerAccount, PartnerPlan
@require_http_methods(['GET', 'POST'])
def pricing(request):
    form = InquiryForm(request.POST or None, initial={'plan': request.GET.get('plan'), 'ad_position': request.GET.get('ad_position')})
    if request.method == 'POST' and form.is_valid():
        inquiry = form.save(commit=False)
        inquiry.agree_privacy_at = timezone.now()
        inquiry.save()
        messages.success(request, '입점·광고 문의를 접수했습니다. 담당자가 영업일 기준으로 연락드립니다.')
        return redirect('partners:pricing')
    context = context_for(request)
    plans = list(PartnerPlan.objects.filter(is_active=True))
    context.update(page='partners', form=form, plans=plans, has_example=any(p.is_example for p in plans),
                   partner=PartnerAccount.objects.filter(user=request.user).first() if request.user.is_authenticated else None)
    return render(request, 'partners/pricing.html', context)


# 화면 출력: partners/apply.html · 조회 데이터: PartnerAccount
@login_required
@require_http_methods(['GET', 'POST'])
def apply(request):
    account = PartnerAccount.objects.filter(user=request.user).first()
    if account:
        return redirect('partners:leads' if account.is_approved else 'partners:pricing')
    form = PartnerApplyForm(request.POST or None, request.FILES or None, initial={'plan': request.GET.get('plan'), 'ad_position': request.GET.get('ad_position')})
    if request.method == 'POST' and form.is_valid():
        account = form.save(commit=False)
        account.user = request.user
        account.save()
        precheck(account, ['business_file','authorization_file'])
        messages.success(request, '파트너 신청을 접수했습니다. 관리자 승인 후 예비창업자 사업제안 기능이 열립니다.')
        return redirect('partners:pricing')
    context = context_for(request)
    context.update(page='partners', form=form)
    return render(request, 'partners/apply.html', context)


def approved_partner(request):
    account = PartnerAccount.objects.filter(user=request.user, status='approved').select_related('brand', 'plan').first()
    if account is None:
        messages.info(request, '승인된 브랜드 파트너만 이용할 수 있어요.')
    return account


def proposal_limit(account):
    return account.plan.monthly_proposal_limit if account.plan else DEFAULT_PROPOSAL_LIMIT


def sent_this_month(account):
    start = timezone.localdate().replace(day=1)
    return account.proposals.filter(created_at__date__gte=start).count()


def masked(name):
    return (name[:1] + '*' * max(len(name) - 1, 1)) if name else '회원'


# 화면 출력: partners/leads.html · 조회 데이터: MemberProfile
@login_required
@require_GET
def leads(request):
    account = approved_partner(request)
    if account is None:
        return redirect('partners:pricing')
    region, category = request.GET.get('region', ''), request.GET.get('category', '')
    profiles = (MemberProfile.objects.filter(agree_proposal=True, is_complete=True, user__is_active=True)
                .exclude(wants_startup=False).exclude(user=request.user).select_related('user').order_by('-agree_proposal_at', '-id'))
    if region in REGIONS:
        profiles = profiles.filter(desired_region=region)
    context = context_for(request)
    if category in context['categories'] and category != '전체':
        profiles = profiles.filter(desired_category__in=[category, '전체'])
    page_obj = Paginator(profiles, 10).get_page(request.GET.get('page'))
    recent = set(account.proposals.filter(created_at__gte=timezone.now() - timedelta(days=30)).values_list('member_id', flat=True))
    leads = [{'profile': p, 'name': masked(p.user.first_name or p.user.username), 'proposed': p.user_id in recent}
             for p in page_obj.object_list]
    params = request.GET.copy(); params.pop('page', None)
    context.update(page='partners', account=account, leads=leads, page_obj=page_obj, page_query=params.urlencode(),
                   page_range=list(page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)),
                   lead_region=region, lead_category=category, form=ProposalForm(),
                   limit=proposal_limit(account), used=sent_this_month(account),
                   sent=account.proposals.select_related('member', 'member__member_profile')[:20])
    return render(request, 'partners/leads.html', context)


@login_required
@require_POST
def send_proposal(request, profile_id):
    account = approved_partner(request)
    if account is None:
        return redirect('partners:pricing')
    profile = get_object_or_404(MemberProfile, pk=profile_id, agree_proposal=True, is_complete=True)
    if sent_this_month(account) >= proposal_limit(account):
        messages.info(request, '이번 달 사업제안 발송 한도를 모두 사용했어요.')
    elif account.proposals.filter(member=profile.user, created_at__gte=timezone.now() - timedelta(days=30)).exists():
        messages.info(request, '같은 회원에게는 30일에 한 번만 제안할 수 있어요.')
    else:
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.partner, proposal.member = account, profile.user
            proposal.save()
            messages.success(request, '사업제안을 보냈습니다. 회원이 수락하면 연락처가 공개됩니다.')
        else:
            messages.info(request, '제목과 제안 내용을 입력해주세요.')
    return redirect('partners:leads')


# 화면 출력: partners/inbox.html · 조회 데이터: BusinessProposal, MemberProfile
@login_required
@require_GET
def inbox(request):
    context = context_for(request)
    proposals = BusinessProposal.objects.filter(member=request.user).select_related('partner__brand')
    context.update(page='proposals', proposals=proposals,
                   consent=MemberProfile.objects.filter(user=request.user, agree_proposal=True).exists())
    return render(request, 'partners/inbox.html', context)


@login_required
@require_POST
def respond(request, pk):
    proposal = get_object_or_404(BusinessProposal, pk=pk, member=request.user)
    action = request.POST.get('action')
    if proposal.status == 'sent' and action in ('accepted', 'declined'):
        proposal.status, proposal.responded_at = action, timezone.now()
        proposal.save(update_fields=['status', 'responded_at'])
        messages.success(request, '제안을 수락해 브랜드에 연락처가 공개됐습니다.' if action == 'accepted' else '제안을 거절했습니다.')
    return redirect('partners:inbox')
