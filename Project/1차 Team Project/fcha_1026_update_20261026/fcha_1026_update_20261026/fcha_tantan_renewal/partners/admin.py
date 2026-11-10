from django.contrib import admin
from django.utils import timezone
from .models import BusinessProposal, PartnerAccount, PartnerInquiry, PartnerPlan


@admin.register(PartnerPlan)
class PartnerPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'order', 'monthly_price_krw', 'monthly_proposal_limit', 'includes_ad_slot', 'is_active', 'is_example')
    list_editable = ('order', 'is_active')


@admin.register(PartnerInquiry)
class PartnerInquiryAdmin(admin.ModelAdmin):
    list_display = ('company', 'brand_name', 'contact_name', 'phone', 'plan', 'status', 'created_at')
    list_filter = ('status', 'plan')
    search_fields = ('company', 'brand_name', 'contact_name')


@admin.register(PartnerAccount)
class PartnerAccountAdmin(admin.ModelAdmin):
    list_display = ('company', 'brand', 'user', 'plan', 'status', 'created_at', 'approved_at')
    list_filter = ('status', 'plan')
    search_fields = ('company', 'brand__name', 'user__username')
    autocomplete_fields = ('brand',)
    actions = ('approve',)

    @admin.action(description='선택한 파트너 승인')
    def approve(self, request, queryset):
        queryset.update(status='approved', approved_at=timezone.now())


@admin.register(BusinessProposal)
class BusinessProposalAdmin(admin.ModelAdmin):
    list_display = ('partner', 'member', 'title', 'status', 'created_at', 'responded_at')
    list_filter = ('status',)
