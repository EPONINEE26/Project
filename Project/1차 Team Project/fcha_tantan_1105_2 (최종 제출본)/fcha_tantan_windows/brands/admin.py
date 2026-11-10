from django.contrib import admin
from .models import Brand,AnnualStat,RegionalStat
# 관리자 Brand: 브랜드 기본정보 → 홈·브랜드 목록/상세·비교·추천·지역상권 후보 카드
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display=('name','slug','category','is_demo')
    search_fields=('name','slug')
    list_filter=('category','is_demo')
# 관리자 AnnualStat: 연도별 공시 매출·매장 수·창업비용 → 브랜드 목록/상세·비교·계산기
@admin.register(AnnualStat)
class AnnualStatAdmin(admin.ModelAdmin):
    list_display=('brand','year','stores','opened','closed','source_label')
    list_filter=('year',)
# 관리자 RegionalStat: 브랜드 지역별 통계 → 선택 지역의 브랜드 매출·매장 수
admin.site.register(RegionalStat)

from .models import AreaSales
# 관리자 AreaSales: 공시 면적당 매출 → 브랜드 상세·비교의 평당 매출
admin.site.register(AreaSales)

from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import AdSlot, BrandReview, OwnerVerification


# 관리자 AdSlot: 광고 구좌·입찰가·노출기간 → 홈·브랜드 탐색 광고 카드
@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ('position', 'brand', 'advertiser', 'cpc_bid_krw', 'starts_on', 'ends_on', 'is_active')
    list_filter = ('position', 'is_active')
    autocomplete_fields = ('brand',)


# 관리자 OwnerVerification: 점주 인증 신청·증빙·승인 상태 → 인증 내역·점주 기능 접근 확인
@admin.register(OwnerVerification)
class OwnerVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'brand', 'store_name', 'contract_start_date', 'status', 'submitted_at', 'download')
    list_filter = ('status',)
    search_fields = ('user__username', 'brand__name', 'store_name')
    readonly_fields = ('download', 'business_download', 'document_check', 'submitted_at', 'reviewed_at')
    exclude = ('contract_file', 'business_file')
    actions = ('approve', 'reject')

    @admin.display(description='계약서')
    def download(self, obj):
        return format_html('<a href="{}">내려받기</a>', reverse('brands:contract_file', args=[obj.pk])) if obj.pk else '-'

    @admin.display(description='사업자등록증')
    def business_download(self, obj):
        return format_html('<a href="{}">비공개 서류 열기</a>', reverse('core:evidence', args=['owner',obj.pk,'business'])) if obj.pk and obj.business_file else '미제출'

    @admin.action(description='선택한 인증 승인')
    def approve(self, request, queryset):
        queryset.update(status='approved', reviewed_at=timezone.now(), reject_reason='')

    @admin.action(description='선택한 인증 반려')
    def reject(self, request, queryset):
        queryset.update(status='rejected', reviewed_at=timezone.now())


# 관리자 BrandReview: 인증 점주 후기 → 브랜드 상세 후기·후기 작성 화면
@admin.register(BrandReview)
class BrandReviewAdmin(admin.ModelAdmin):
    list_display = ('brand', 'user', 'rating', 'title', 'is_hidden', 'moderation_state', 'created_at')
    list_filter = ('rating', 'is_hidden')
    search_fields = ('brand__name', 'user__username', 'title')

    readonly_fields = ('moderation_original',)
    actions = ('blind', 'remove', 'publish')
    @admin.action(description='1차 블라인드')
    def blind(self,request,queryset): queryset.update(moderation_state='blind')
    @admin.action(description='2차 삭제 안내')
    def remove(self,request,queryset): queryset.update(moderation_state='removed')
    @admin.action(description='검토 완료 공개')
    def publish(self,request,queryset): queryset.update(moderation_state='visible',is_hidden=False)
