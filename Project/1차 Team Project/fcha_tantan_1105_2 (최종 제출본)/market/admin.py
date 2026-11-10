from django.contrib import admin
from django import forms
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from .analysis_models import DistrictPopulationStat


# 관리자 DistrictPopulationStat: 자치구별 길단위 유동인구 CSV → 지역상권분석 자치구 참고 영역(includes/district_population.html)
@admin.register(DistrictPopulationStat)
class DistrictPopulationStatAdmin(admin.ModelAdmin):
    list_display = ('district_code', 'district_name', 'period', 'total', 'unit')
    list_filter = ('district_name', 'period')
    search_fields = ('district_code', 'district_name')
from .models import FloatingPopulation, StoreLocation, TransferInquiry, TransferListing, TransferDocument


# 관리자 FloatingPopulation: 회원 매장별 유동인구 측정 기록 → 내 매장 상세(공공 상권·자치구 통계와 별개)
class PopulationInline(admin.TabularInline):
    model = FloatingPopulation
    extra = 0


# 관리자 StoreLocation: 회원 등록 매장·후보지 위치 → 내 매장 목록/상세·공개 점주 지도
@admin.register(StoreLocation)
class StoreLocationAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'brand', 'owner', 'status', 'sido', 'sigungu', 'latitude', 'longitude', 'updated_at')
    list_filter = ('status', 'sido')
    search_fields = ('store_name', 'address', 'owner__username', 'brand__name')
    autocomplete_fields = ('brand',)
    inlines = [PopulationInline]


# 관리자 FloatingPopulation: 회원 매장별 유동인구 측정 기록 → 내 매장 상세(공공 상권·자치구 통계와 별개)
@admin.register(FloatingPopulation)
class FloatingPopulationAdmin(admin.ModelAdmin):
    list_display = ('store', 'measured_on', 'day_type', 'time_slot', 'count', 'method')
    list_filter = ('method', 'time_slot', 'day_type')


# 관리자 TransferListing: 양도양수 매물·금액·공개 상태 → 매물 목록/상세·내 매물
class TransferDocumentInline(admin.TabularInline):
    model = TransferDocument
    extra = 0
    fields = ('download', 'uploaded_at')
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='증빙 서류 확인')
    def download(self, obj):
        return format_html('<a href="{}">{}</a>', reverse('admin:market_transfer_document', args=[obj.pk]), obj.original_name)


class TransferApprovalForm(forms.ModelForm):
    class Meta:
        model = TransferListing
        fields = '__all__'

    def clean(self):
        data = super().clean()
        if data.get('approval_status') == 'approved' and not (self.instance.pk and self.instance.documents.exists()):
            self.add_error('approval_status', '증빙 서류가 첨부된 매물만 승인할 수 있습니다.')
        return data


@admin.register(TransferListing)
class TransferListingAdmin(admin.ModelAdmin):
    form = TransferApprovalForm
    inlines = [TransferDocumentInline]
    list_display = ('title', 'brand', 'owner', 'approval_status', 'sido', 'sigungu', 'premium_manwon', 'contract_status', 'status', 'created_at')
    list_filter = ('approval_status', 'status', 'contract_status', 'sido', 'moderation_state')
    readonly_fields = ('moderation_original', 'reviewed_at', 'reviewed_by')
    actions = ('approve', 'reject', 'blind','remove','publish')

    def get_urls(self):
        return [path('document/<int:pk>/', self.admin_site.admin_view(self.document), name='market_transfer_document')] + super().get_urls()

    def document(self, request, pk):
        document = get_object_or_404(TransferDocument.objects.select_related('listing'), pk=pk)
        if not self.has_view_or_change_permission(request, document.listing):
            raise PermissionDenied
        try:
            response = FileResponse(document.file.open('rb'), as_attachment=True, filename=document.original_name)
        except FileNotFoundError:
            raise Http404
        response['Cache-Control'] = 'private, no-store'
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    def save_model(self, request, obj, form, change):
        if 'approval_status' in form.changed_data:
            obj.reviewed_at = timezone.now()
            obj.reviewed_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='증빙 서류 확인 후 승인', permissions=['change'])
    def approve(self, request, queryset):
        ids = list(queryset.filter(documents__isnull=False).values_list('pk', flat=True).distinct())
        queryset.filter(pk__in=ids).update(approval_status='approved', reviewed_at=timezone.now(), reviewed_by=request.user)
        self.message_user(request, f'{len(ids)}건 승인했습니다. 증빙 서류 없는 매물은 제외했습니다.')

    @admin.action(description='매물 반려', permissions=['change'])
    def reject(self, request, queryset):
        queryset.update(approval_status='rejected', reviewed_at=timezone.now(), reviewed_by=request.user)
    @admin.action(description='1차 블라인드')
    def blind(self,request,queryset):queryset.update(moderation_state='blind')
    @admin.action(description='2차 삭제 안내')
    def remove(self,request,queryset):queryset.update(moderation_state='removed')
    @admin.action(description='공개 복원')
    def publish(self,request,queryset):queryset.update(moderation_state='visible')
    search_fields = ('title', 'brand__name', 'owner__username')
    autocomplete_fields = ('brand',)


# 관리자 TransferInquiry: 매물 문의·연락처 공개 동의 → 매물 상세의 문의 내역
@admin.register(TransferInquiry)
class TransferInquiryAdmin(admin.ModelAdmin):
    list_display = ('listing', 'sender', 'kind', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')

from .analysis_models import StartupCondition, DataSource, CommercialArea, IndustryCode, PopulationStat, IndustrySales, StoreTrend, PublicStore, Attractor, BrandOperation


# 상권 분석 모델을 기본 관리자로 등록합니다. 각 모델의 데이터·출력 위치는 analysis_models.py 주석 참고.
for model in [StartupCondition, DataSource, CommercialArea, IndustryCode, PopulationStat, IndustrySales, StoreTrend, PublicStore, Attractor, BrandOperation]:
    admin.site.register(model)
