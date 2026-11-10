from django.contrib import admin
from .models import Brand,AnnualStat,RegionalStat
@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display=('name','slug','category','is_demo')
    search_fields=('name','slug')
    list_filter=('category','is_demo')
@admin.register(AnnualStat)
class AnnualStatAdmin(admin.ModelAdmin):
    list_display=('brand','year','stores','opened','closed','source_label')
    list_filter=('year',)
admin.site.register(RegionalStat)

from .models import AreaSales
admin.site.register(AreaSales)

from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from .models import AdSlot, BrandReview, OwnerVerification


@admin.register(AdSlot)
class AdSlotAdmin(admin.ModelAdmin):
    list_display = ('position', 'brand', 'advertiser', 'starts_on', 'ends_on', 'is_active')
    list_filter = ('position', 'is_active')
    autocomplete_fields = ('brand',)


@admin.register(OwnerVerification)
class OwnerVerificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'brand', 'store_name', 'contract_start_date', 'status', 'submitted_at', 'download')
    list_filter = ('status',)
    search_fields = ('user__username', 'brand__name', 'store_name')
    readonly_fields = ('download', 'submitted_at', 'reviewed_at')
    exclude = ('contract_file',)
    actions = ('approve', 'reject')

    @admin.display(description='계약서')
    def download(self, obj):
        return format_html('<a href="{}">내려받기</a>', reverse('brands:contract_file', args=[obj.pk])) if obj.pk else '-'

    @admin.action(description='선택한 인증 승인')
    def approve(self, request, queryset):
        queryset.update(status='approved', reviewed_at=timezone.now(), reject_reason='')

    @admin.action(description='선택한 인증 반려')
    def reject(self, request, queryset):
        queryset.update(status='rejected', reviewed_at=timezone.now())


@admin.register(BrandReview)
class BrandReviewAdmin(admin.ModelAdmin):
    list_display = ('brand', 'user', 'rating', 'title', 'is_hidden', 'created_at')
    list_filter = ('rating', 'is_hidden')
    search_fields = ('brand__name', 'user__username', 'title')
