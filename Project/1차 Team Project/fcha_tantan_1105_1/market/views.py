from django import forms
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.http import Http404
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from accounts.models import MemberProfile
from brands.constants import REGIONS
from brands.lookup import BrandLookupField
from brands.views import context_for
from .models import FloatingPopulation, StoreLocation, TransferInquiry, TransferListing, TransferDocument
from .maps import listing_point
from core.moderation import flag_content

PAGE_SIZE = 10


def brand_field(required=True):
    # 브랜드가 1만 개가 넘어 드롭다운 대신 검색 입력칸을 씁니다.
    return BrandLookupField(required=required, help_text='브랜드명을 입력하고 목록에서 고르세요.' + ('' if required else ' 아직 정하지 않았다면 비워두세요.'))


class StoreForm(forms.ModelForm):
    brand = brand_field(required=False)
    class Meta:
        model = StoreLocation
        fields = ('store_name', 'brand', 'status', 'postcode', 'address', 'address_detail', 'sido', 'sigungu', 'dong',
                  'latitude', 'longitude', 'area_pyeong', 'opened_on', 'memo')
        widgets = {'postcode': forms.TextInput(attrs={'readonly': True, 'data-postcode': 'postcode'}),
                   'address': forms.TextInput(attrs={'readonly': True, 'data-postcode': 'address'}),
                   'address_detail': forms.TextInput(attrs={'data-postcode': 'detail'}),
                   'sido': forms.HiddenInput(attrs={'data-postcode': 'sido'}),
                   'sigungu': forms.HiddenInput(attrs={'data-postcode': 'sigungu'}),
                   'dong': forms.HiddenInput(attrs={'data-postcode': 'dong'}),
                   'latitude': forms.NumberInput(attrs={'data-map': 'lat', 'step': '0.000001', 'readonly': True}),
                   'longitude': forms.NumberInput(attrs={'data-map': 'lng', 'step': '0.000001', 'readonly': True}),
                   'opened_on': forms.DateInput(attrs={'type': 'date'}),
                   'memo': forms.Textarea(attrs={'rows': 3})}

    def clean(self):
        data = super().clean()
        lat, lng = data.get('latitude'), data.get('longitude')
        if (lat is None) != (lng is None):
            raise forms.ValidationError('위도와 경도는 함께 입력해주세요.')
        if lat is not None and not (33 <= lat <= 39 and 124 <= lng <= 132):
            raise forms.ValidationError('대한민국 범위의 좌표가 아닙니다.')
        return data


class PopulationForm(forms.ModelForm):
    class Meta:
        model = FloatingPopulation
        fields = ('measured_on', 'day_type', 'time_slot', 'count', 'method', 'source_note')
        widgets = {'measured_on': forms.DateInput(attrs={'type': 'date'})}


class MultipleDocumentInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleDocumentField(forms.FileField):
    def clean(self, data, initial=None):
        files = data if isinstance(data, (list, tuple)) else ([data] if data else [])
        if len(files) > 5:
            raise forms.ValidationError('서류는 한 번에 최대 5개까지 첨부할 수 있습니다.')
        cleaned = [super(MultipleDocumentField, self).clean(item, initial) for item in files]
        for item in cleaned:
            FileExtensionValidator(['pdf', 'jpg', 'jpeg', 'png'])(item)
            if item.size > 10 * 1024 * 1024:
                raise forms.ValidationError('각 서류는 10MB 이하로 첨부해주세요.')
        return cleaned


class TransferForm(forms.ModelForm):
    documents = MultipleDocumentField(label='임대 계약서 등 증빙 서류', required=False,
        widget=MultipleDocumentInput(attrs={'accept': '.pdf,.jpg,.jpeg,.png'}),
        help_text='임대 계약서 등 확인 서류를 첨부해주세요. PDF·JPG·PNG, 최대 5개, 각 10MB 이하. 관리자만 열람합니다.')
    brand = BrandLookupField(widget=forms.TextInput(attrs={
        'data-brand-lookup': '1', 'data-brand-name-only': '1',
        'autocomplete': 'off', 'placeholder': '브랜드명 검색',
    }))
    class Meta:
        model = TransferListing
        fields = ('brand', 'title', 'sido', 'sigungu', 'dong', 'address', 'address_detail', 'latitude', 'longitude', 'premium_manwon', 'deposit_manwon',
                  'monthly_rent_manwon', 'management_fee_manwon', 'monthly_sales_manwon', 'monthly_profit_manwon',
                  'area_pyeong', 'parking_spaces', 'facilities', 'contract_status', 'contract_end_date', 'available_from', 'description', 'status')
        widgets = {'address':forms.TextInput(attrs={'data-postcode':'address'}),
                   'address_detail':forms.TextInput(attrs={'data-postcode':'detail'}),
                   'sido':forms.HiddenInput(attrs={'data-postcode':'sido'}),
                   'sigungu':forms.HiddenInput(attrs={'data-postcode':'sigungu'}),
                   'dong':forms.HiddenInput(attrs={'data-postcode':'dong'}),
                   'latitude':forms.NumberInput(attrs={'data-map':'lat','step':'0.000001','readonly':True}),
                   'longitude':forms.NumberInput(attrs={'data-map':'lng','step':'0.000001','readonly':True}),
                   'available_from':forms.DateInput(attrs={'type':'date'}),
                   'contract_end_date': forms.DateInput(attrs={'type': 'date'}),
                   'description': forms.Textarea(attrs={'rows': 6})}

    def clean(self):
        data=super().clean()
        if not data.get('documents') and not (self.instance.pk and self.instance.documents.exists()):
            self.add_error('documents', '임대 계약서 등 증빙 서류를 1개 이상 첨부해주세요.')
        lat,lng=data.get('latitude'),data.get('longitude')
        if (lat is None)!=(lng is None):raise forms.ValidationError('위도와 경도는 함께 입력해주세요.')
        if lat is not None and not (33<=lat<=39 and 124<=lng<=132):raise forms.ValidationError('대한민국 범위의 좌표를 입력해주세요.')
        return data


class InquiryForm(forms.ModelForm):
    class Meta:
        model = TransferInquiry
        fields = ('kind', 'message', 'share_phone')
        widgets = {'message': forms.Textarea(attrs={'rows': 4, 'maxlength': 1000})}


def map_context():
    # 카카오 지도 JavaScript 키가 .env에 있을 때만 지도를 띄웁니다.
    return {'kakao_js_key': settings.KAKAO_JS_KEY}


# ── 매장 위치·유동인구 ──────────────────────────────

# 화면 출력: market/store_list.html · 조회 데이터: StoreLocation
@login_required
@require_GET
def store_list(request):
    context = context_for(request)
    stores = (StoreLocation.objects.filter(owner=request.user).select_related('brand')
              .annotate(population_count=Count('populations'), population_avg=Avg('populations__count', filter=Q(populations__time_slot='all'))))
    context.update(page='stores', stores=stores)
    return render(request, 'market/store_list.html', context)


# 화면 출력: market/store_form.html · 화면 컨텍스트/폼을 템플릿에 전달
@login_required
@require_http_methods(['GET', 'POST'])
def store_edit(request, pk=None):
    store = get_object_or_404(StoreLocation, pk=pk, owner=request.user) if pk else None
    form = StoreForm(request.POST or None, instance=store)
    if request.method == 'POST' and form.is_valid():
        store = form.save(commit=False)
        store.owner = request.user
        store.save()
        messages.success(request, '매장 위치를 저장했습니다.')
        return redirect('market:store_detail', pk=store.pk)
    context = context_for(request)
    context.update(page='stores', form=form, store=store, **map_context())
    return render(request, 'market/store_form.html', context)


# 화면 출력: market/store_detail.html · 조회 데이터: StoreLocation
@login_required
@require_http_methods(['GET', 'POST'])
def store_detail(request, pk):
    store = get_object_or_404(StoreLocation.objects.select_related('brand'), pk=pk, owner=request.user)
    form = PopulationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        population = form.save(commit=False)
        population.store = store
        population.save()
        messages.success(request, '유동인구 기록을 추가했습니다.')
        return redirect('market:store_detail', pk=store.pk)
    populations = store.populations.all()
    summary = {slot: populations.filter(time_slot=slot).aggregate(avg=Avg('count'), n=Count('id'))
               for slot, _ in FloatingPopulation.TIME_SLOTS}
    summary_rows = [{'label': label, 'avg': round(summary[slot]['avg']) if summary[slot]['avg'] is not None else None, 'n': summary[slot]['n']}
                    for slot, label in FloatingPopulation.TIME_SLOTS if summary[slot]['n']]
    context = context_for(request)
    context.update(page='stores', store=store, form=form, populations=populations, summary_rows=summary_rows, **map_context())
    return render(request, 'market/store_detail.html', context)


@login_required
@require_POST
def population_delete(request, pk):
    population = get_object_or_404(FloatingPopulation, pk=pk, store__owner=request.user)
    store_pk = population.store_id
    population.delete()
    messages.success(request, '유동인구 기록을 삭제했습니다.')
    return redirect('market:store_detail', pk=store_pk)


# ── 양도양수 ──────────────────────────────

# 화면 출력: market/transfer_list.html · 조회 데이터: TransferListing
@require_GET
def transfer_list(request):
    context = context_for(request)
    context['transfer_submission_notice'] = request.session.pop('transfer_submission_notice', False)
    query = request.GET.get('query', '').strip()
    sido = request.GET.get('sido', '')
    category = request.GET.get('category', '전체')
    listings = TransferListing.objects.filter(moderation_state='visible', approval_status='approved').exclude(status='closed').select_related('brand')
    if query:
        listings = listings.filter(Q(title__icontains=query) | Q(brand__name__icontains=query) | Q(sigungu__icontains=query) | Q(dong__icontains=query))
    if sido in REGIONS:
        listings = listings.filter(sido=sido)
    if category in context['categories'] and category != '전체':
        listings = listings.filter(brand__category=category)
    district = request.GET.get('sigungu','').strip()[:30]
    if district:listings=listings.filter(sigungu__icontains=district)
    bounds={}
    for name,field in [('max_premium','premium_manwon'),('max_deposit','deposit_manwon'),('max_rent','monthly_rent_manwon'),('min_area','area_pyeong'),('max_area','area_pyeong')]:
        raw=request.GET.get(name,'').strip()
        if raw.isdigit() and len(raw)<=9:
            bounds[name]=int(raw)
            listings=listings.filter(**{field+('__gte' if name=='min_area' else '__lte'):int(raw)})
    sort=request.GET.get('sort','latest')
    ordering={'latest':'-created_at','premium':'premium_manwon','rent':'monthly_rent_manwon','area':'-area_pyeong'}
    listings=listings.order_by(ordering.get(sort,'-created_at'),'-id')
    map_items=[point for item in listings.exclude(latitude=None).exclude(longitude=None)[:300] if (point:=listing_point(item))]
    page_obj = Paginator(listings, PAGE_SIZE).get_page(request.GET.get('page'))
    params = request.GET.copy(); params.pop('page', None)
    context.update(page='transfer', listings=page_obj.object_list, page_obj=page_obj, total_count=page_obj.paginator.count,
                   page_range=list(page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1)),
                   page_query=params.urlencode(), query=query, sido=sido, sigungu=district, category=category, transfer_map_points=map_items, transfer_sort=sort, bounds=bounds, **map_context())
    return render(request, 'market/transfer_list.html', context)


# 화면 출력: market/transfer_detail.html, market/transfer_hidden.html · 조회 데이터: MemberProfile, TransferListing
@require_http_methods(['GET', 'POST'])
def transfer_detail(request, pk):
    listing = get_object_or_404(TransferListing.objects.select_related('brand', 'owner'), pk=pk)
    is_owner = request.user.is_authenticated and listing.owner_id == request.user.id
    if listing.approval_status != 'approved' and not is_owner and not request.user.is_staff:
        raise Http404
    form = InquiryForm(request.POST or None)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if is_owner:
            messages.info(request, '내 매물에는 문의할 수 없어요.')
        elif listing.status == 'closed' or listing.moderation_state != 'visible' or listing.approval_status != 'approved':
            messages.info(request, '거래가 완료된 매물입니다.')
        elif form.is_valid():
            inquiry = form.save(commit=False)
            inquiry.listing, inquiry.sender = listing, request.user
            inquiry.save()
            messages.success(request, '문의를 보냈습니다. 등록자가 확인 후 연락드립니다.')
            return redirect('market:transfer_detail', pk=listing.pk)
    inquiries = []
    if listing.moderation_state != 'visible' and not is_owner:
        from django.http import HttpResponse
        from core.moderation import public_message
        return render(request,'market/transfer_hidden.html', {**context_for(request),'notice':public_message(listing),'page':'transfer'},status=200)
    if is_owner:
        inquiries = list(listing.inquiries.select_related('sender'))
        phones = dict(MemberProfile.objects.filter(user__in=[i.sender_id for i in inquiries]).values_list('user_id', 'phone'))
        for inquiry in inquiries:
            inquiry.phone = phones.get(inquiry.sender_id) if inquiry.share_phone else None
        listing.inquiries.filter(is_read=False).update(is_read=True)
    context = context_for(request)
    context.update(page='transfer', listing=listing, form=form, is_owner=is_owner, inquiries=inquiries, transfer_map_points=[listing_point(listing)] if listing_point(listing) else [], **map_context())
    return render(request, 'market/transfer_detail.html', context)


# 화면 출력: market/transfer_form.html · 화면 컨텍스트/폼을 템플릿에 전달
@login_required
@require_http_methods(['GET', 'POST'])
def transfer_edit(request, pk=None):
    listing = get_object_or_404(TransferListing, pk=pk, owner=request.user) if pk else None
    form = TransferForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=listing)
    if request.method == 'POST' and form.is_valid():
        listing = form.save(commit=False)
        listing.owner = request.user
        flag_content(listing, request, ('title','description','facilities'))
        listing.approval_status = 'pending'
        listing.reviewed_at = None
        listing.reviewed_by = None
        listing.approval_note = ''
        with transaction.atomic():
            listing.save()
            for document in form.cleaned_data['documents']:
                TransferDocument.objects.create(listing=listing, file=document, original_name=document.name[:255])
        request.session['transfer_submission_notice'] = True
        return redirect('market:transfer_list')
    context = context_for(request)
    context.update(page='transfer', form=form, listing=listing, **map_context())
    return render(request, 'market/transfer_form.html', context)


# 화면 출력: market/transfer_mine.html · 조회 데이터: TransferInquiry, TransferListing
@login_required
@require_GET
def transfer_mine(request):
    context = context_for(request)
    listings = (TransferListing.objects.filter(owner=request.user).select_related('brand')
                .annotate(inquiry_count=Count('inquiries'), unread=Count('inquiries', filter=Q(inquiries__is_read=False))))
    sent = TransferInquiry.objects.filter(sender=request.user).select_related('listing__brand')
    context.update(page='transfer', listings=listings, sent=sent)
    return render(request, 'market/transfer_mine.html', context)


@login_required
@require_POST
def transfer_delete(request,pk):
    listing=get_object_or_404(TransferListing,pk=pk,owner=request.user)
    listing.delete()
    messages.success(request,'매물을 삭제했습니다.')
    return redirect('market:transfer_mine')


class TransferChatForm(forms.Form):
    body = forms.CharField(label='메시지', max_length=1000, strip=True,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '메시지를 입력하세요', 'maxlength': 1000}))


@login_required
@require_http_methods(['GET', 'POST'])
def transfer_chat(request, pk):
    inquiry = get_object_or_404(
        TransferInquiry.objects.select_related('listing__owner', 'sender').filter(
            Q(sender=request.user) | Q(listing__owner=request.user)), pk=pk)
    is_owner = inquiry.listing.owner_id == request.user.pk
    partner = inquiry.sender if is_owner else inquiry.listing.owner
    form = TransferChatForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        inquiry.chat_messages.create(sender=request.user, body=form.cleaned_data['body'])
        return redirect('market:transfer_chat', pk=inquiry.pk)
    if is_owner:
        TransferInquiry.objects.filter(pk=inquiry.pk, is_read=False).update(is_read=True)
    context = context_for(request)
    context.update(page='transfer', inquiry=inquiry, partner=partner, form=form,
                   chat_messages=inquiry.chat_messages.select_related('sender'))
    return render(request, 'market/transfer_chat.html', context)
