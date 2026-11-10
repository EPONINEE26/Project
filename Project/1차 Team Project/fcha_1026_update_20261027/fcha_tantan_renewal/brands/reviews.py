"""점주 후기: 계약서 인증(관리자 승인) + 계약 시작 6개월 이상인 점주만 작성할 수 있습니다."""
from datetime import date
from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from .models import BrandReview, OwnerVerification

MIN_MONTHS = 6
ALLOWED_EXTENSIONS = ('.pdf', '.jpg', '.jpeg', '.png')
MAX_UPLOAD = 10 * 1024 * 1024


def add_months(day, months):
    # 6개월 뒤 같은 날짜(말일 보정). 예: 8/31 + 6개월 → 2/28(29)
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    for last in (31, 30, 29, 28):
        try:
            return date(year, month, min(day.day, last))
        except ValueError:
            continue


def months_operated(start, today=None):
    today = today or timezone.localdate()
    months = (today.year - start.year) * 12 + today.month - start.month
    if today.day < start.day:
        months -= 1
    return max(months, 0)


def eligible_verification(user, brand, today=None):
    """승인된 인증 중 계약 시작 후 6개월이 지난 것. 없으면 None."""
    if not user.is_authenticated:
        return None
    today = today or timezone.localdate()
    for verification in OwnerVerification.objects.filter(user=user, brand=brand, status='approved').order_by('contract_start_date'):
        if add_months(verification.contract_start_date, MIN_MONTHS) <= today:
            return verification
    return None


def review_context(request, brand):
    reviews = BrandReview.objects.filter(brand=brand, is_hidden=False).select_related('user', 'verification')
    summary = reviews.aggregate(avg=Avg('rating'), count=Count('id'))
    page = Paginator(reviews, 5).get_page(request.GET.get('review_page'))
    for review in page.object_list:
        review.months = months_operated(review.verification.contract_start_date)
    user = request.user
    status = None
    if user.is_authenticated:
        latest = OwnerVerification.objects.filter(user=user, brand=brand).first()
        status = latest.status if latest else None
    return {'reviews': page, 'review_avg': round(summary['avg'], 1) if summary['avg'] is not None else None,
            'review_count': summary['count'], 'review_stars': round(summary['avg'] or 0),
            'review_eligible': eligible_verification(user, brand) is not None,
            'my_review': BrandReview.objects.filter(user=user, brand=brand).first() if user.is_authenticated else None,
            'verification_status': status}


class VerificationForm(forms.ModelForm):
    class Meta:
        model = OwnerVerification
        fields = ('store_name', 'contract_start_date', 'contract_end_date', 'contract_file')
        widgets = {'contract_start_date': forms.DateInput(attrs={'type': 'date'}),
                   'contract_end_date': forms.DateInput(attrs={'type': 'date'})}
        help_texts = {'contract_file': 'PDF·JPG·PNG, 10MB 이하. 주민등록번호 뒷자리·계좌번호 등은 가린 뒤 올려주세요. 관리자만 열람합니다.'}

    def clean_contract_start_date(self):
        value = self.cleaned_data['contract_start_date']
        if value > timezone.localdate():
            raise forms.ValidationError('계약 시작일은 오늘 이후일 수 없습니다.')
        return value

    def clean_contract_file(self):
        file = self.cleaned_data['contract_file']
        if not file.name.lower().endswith(ALLOWED_EXTENSIONS):
            raise forms.ValidationError('PDF, JPG, PNG 파일만 올릴 수 있습니다.')
        if file.size > MAX_UPLOAD:
            raise forms.ValidationError('10MB 이하 파일만 올릴 수 있습니다.')
        return file

    def clean(self):
        data = super().clean()
        start, end = data.get('contract_start_date'), data.get('contract_end_date')
        if start and end and end < start:
            self.add_error('contract_end_date', '종료일은 시작일 이후여야 합니다.')
        return data


class ReviewForm(forms.ModelForm):
    rating = forms.TypedChoiceField(label='별점', coerce=int, choices=[(i, f'{i}점') for i in range(5, 0, -1)],
                                    widget=forms.RadioSelect)
    class Meta:
        model = BrandReview
        fields = ('rating', 'title', 'content')
        widgets = {'content': forms.Textarea(attrs={'rows': 6, 'maxlength': 2000})}


def brand_for(slug):
    from .views import visible_brands
    return get_object_or_404(visible_brands(), slug=slug)


@login_required
@require_http_methods(['GET', 'POST'])
def verify(request, slug):
    from .views import context_for
    brand = brand_for(slug)
    form = VerificationForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        verification = form.save(commit=False)
        verification.user, verification.brand = request.user, brand
        verification.save()
        messages.success(request, '계약서 인증을 접수했습니다. 관리자 확인 후 후기를 작성할 수 있어요.')
        return redirect(reverse('brands:bview', args=[brand.slug]) + '#reviews')
    context = context_for(request)
    context.update(page='detail', brand=brand, form=form,
                   verifications=OwnerVerification.objects.filter(user=request.user, brand=brand))
    return render(request, 'reviews/verify.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def write_review(request, slug):
    from .views import context_for
    brand = brand_for(slug)
    verification = eligible_verification(request.user, brand)
    if verification is None:
        messages.info(request, '후기는 계약서 인증이 승인되고 계약 시작 후 6개월이 지난 점주만 작성할 수 있어요.')
        return redirect('brands:verify', slug=brand.slug)
    review = BrandReview.objects.filter(user=request.user, brand=brand).first()
    form = ReviewForm(request.POST or None, instance=review)
    if request.method == 'POST' and form.is_valid():
        review = form.save(commit=False)
        review.user, review.brand, review.verification = request.user, brand, verification
        review.save()
        messages.success(request, '후기를 저장했습니다.')
        return redirect(reverse('brands:bview', args=[brand.slug]) + '#reviews')
    context = context_for(request)
    context.update(page='detail', brand=brand, form=form, verification=verification,
                   months=months_operated(verification.contract_start_date))
    return render(request, 'reviews/write.html', context)


@staff_member_required
@require_GET
def contract_file(request, pk):
    # 계약서 사본은 공개 정적 경로에 두지 않고 관리자만 내려받습니다.
    verification = get_object_or_404(OwnerVerification, pk=pk)
    if not verification.contract_file:
        raise Http404
    return FileResponse(verification.contract_file.open('rb'), as_attachment=True,
                        filename=f'contract_{verification.pk}{verification.contract_file.name[verification.contract_file.name.rfind("."):]}')
