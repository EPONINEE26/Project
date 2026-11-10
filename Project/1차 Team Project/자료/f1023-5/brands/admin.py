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
