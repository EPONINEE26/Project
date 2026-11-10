from django.contrib import admin
from .analysis_models import DistrictPopulationStat


# 관리자 DistrictPopulationStat: 자치구별 길단위 유동인구 CSV → 지역상권분석 자치구 참고 영역(includes/district_population.html)
@admin.register(DistrictPopulationStat)
class DistrictPopulationStatAdmin(admin.ModelAdmin):
    list_display = ('district_code', 'district_name', 'period', 'total', 'unit')
    list_filter = ('district_name', 'period')
    search_fields = ('district_code', 'district_name')
from .models import FloatingPopulation, StoreLocation, TransferInquiry, TransferListing


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


# 관리자 TransferInquiry: 매물 문의·연락처 공개 동의 → 매물 상세의 문의 내역
@admin.register(TransferInquiry)
class TransferInquiryAdmin(admin.ModelAdmin):
    list_display = ('listing', 'sender', 'kind', 'share_phone', 'is_read', 'created_at')
    list_filter = ('kind', 'is_read')

from .analysis_models import StartupCondition, DataSource, CommercialArea, IndustryCode, PopulationStat, IndustrySales, StoreTrend, PublicStore, Attractor, BrandOperation


# 상권 분석 모델을 기본 관리자로 등록합니다. 각 모델의 데이터·출력 위치는 analysis_models.py 주석 참고.
for model in [StartupCondition, DataSource, CommercialArea, IndustryCode, PopulationStat, IndustrySales, StoreTrend, PublicStore, Attractor, BrandOperation]:
    admin.site.register(model)
