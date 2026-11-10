from django.contrib import admin
from django.utils import timezone
from django.urls import reverse
from django.utils.html import format_html
from .models import BusinessProposal, PartnerAccount, PartnerInquiry, PartnerPlan


# 관리자 PartnerPlan: 본사 서비스 요금제 → 입점/광고 요금제 화면
@admin.register(PartnerPlan)
class PartnerPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'monthly_price_krw', 'monthly_proposal_limit', 'is_active', 'is_example')
    list_editable = ('order', 'is_active')
    exclude = ('includes_ad_slot',)


# 관리자 PartnerInquiry: 본사 입점·광고 문의 접수 → 관리자 문의 목록
@admin.register(PartnerInquiry)
class PartnerInquiryAdmin(admin.ModelAdmin):
    list_display = ('company', 'brand_name', 'contact_name', 'phone', 'plan', 'ad_position', 'cpc_bid_krw', 'status', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('company', 'brand_name', 'contact_name')


# 관리자 PartnerAccount: 본사 계정·소속 브랜드·승인 상태 → 본사 신청·사업제안 접근 확인
@admin.register(PartnerAccount)
class PartnerAccountAdmin(admin.ModelAdmin):
    list_display = ('company', 'brand', 'user', 'plan', 'status', 'created_at', 'approved_at')
    list_filter = ('status', 'plan')
    search_fields = ('company', 'brand__name', 'user__username')
    autocomplete_fields = ('brand',)
    actions = ('approve',)
    exclude = ('business_file','authorization_file')
    readonly_fields = ('documents','document_check')
    @admin.display(description='증빙 자료')
    def documents(self,obj):
        if not obj.pk:return '-'
        return format_html('<a href="{}">사업자등록증</a> · <a href="{}">권한 증빙</a>', reverse('core:evidence',args=['partner',obj.pk,'business']),reverse('core:evidence',args=['partner',obj.pk,'authorization']))

    @admin.action(description='선택한 파트너 승인')
    def approve(self, request, queryset):
        queryset.update(status='approved', approved_at=timezone.now())


# 관리자 BusinessProposal: 본사→회원 사업제안·수락 상태 → 제안 발송 목록·회원 수신함
@admin.register(BusinessProposal)
class BusinessProposalAdmin(admin.ModelAdmin):
    list_display = ('partner', 'member', 'title', 'status', 'created_at', 'responded_at')
    list_filter = ('status',)
