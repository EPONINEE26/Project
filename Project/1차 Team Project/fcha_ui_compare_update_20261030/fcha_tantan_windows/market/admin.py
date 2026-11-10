from django.contrib import admin
from .models import FloatingPopulation, StoreLocation, TransferInquiry, TransferListing


class PopulationInline(admin.TabularInline):
    model = FloatingPopulation
    extra = 0


@admin.register(StoreLocation)
class StoreLocationAdmin(admin.ModelAdmin):
    list_display = ('store_name', 'brand', 'owner', 'status', 'sido', 'sigungu', 'latitude', 'longitude', 'updated_at')
    list_filter = ('status', 'sido')
    search_fields = ('store_name', 'address', 'owner__username', 'brand__name')
    autocomplete_fields = ('brand',)
    inlines = [PopulationInline]


@admin.register(FloatingPopulation)
class FloatingPopulationAdmin(admin.ModelAdmin):
    list_display = ('store', 'measured_on', 'day_type', 'time_slot', 'count', 'method')
    list_filter = ('method', 'time_slot', 'day_type')


@admin.register(TransferListing)
class TransferListingAdmin(admin.ModelAdmin):
    list_display = ('title', 'brand', 'owner', 'sido', 'sigungu', 'premium_manwon', 'contract_status', 'status', 'created_at')
    list_filter = ('status', 'contract_status', 'sido', 'moderation_state')
    readonly_fields = ('moderation_original',)
    actions = ('blind','remove','publish')
    @admin.action(description='1차 블라인드')
    def blind(self,request,queryset):queryset.update(moderation_state='blind')
    @admin.action(description='2차 삭제 안내')
    def remove(self,request,queryset):queryset.update(moderation_state='removed')
    @admin.action(description='공개 복원')
    def publish(self,request,queryset):queryset.update(moderation_state='visible')
    search_fields = ('title', 'brand__name', 'owner__username')
    autocomplete_fields = ('brand',)


@admin.register(TransferInquiry)
class TransferInquiryAdmin(admin.ModelAdmin):
    list_display = ('listing', 'sender', 'kind', 'share_phone', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')
