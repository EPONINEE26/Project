from django.contrib import admin
from .models import SavedBrand
@admin.register(SavedBrand)
class SavedBrandAdmin(admin.ModelAdmin):
    list_display = ('user', 'brand', 'created_at')
    search_fields = ('user__username', 'brand__name')
