from django.contrib import admin
from .models import EmailVerification, MemberProfile, SavedBrand
@admin.register(SavedBrand)
class SavedBrandAdmin(admin.ModelAdmin):
    list_display = ('user', 'brand', 'created_at')
    search_fields = ('user__username', 'brand__name')


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'signup_source', 'email_verified_at', 'wants_startup', 'desired_region', 'desired_category', 'budget_manwon',
                    'agree_marketing', 'agree_proposal', 'is_complete', 'created_at')
    list_filter = ('signup_source', 'wants_startup', 'agree_marketing', 'agree_proposal', 'is_complete', 'desired_region')
    search_fields = ('user__username', 'user__first_name')


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'attempts', 'verified_at')
    search_fields = ('email',)
    readonly_fields = ('email', 'code_hash', 'attempts', 'created_at', 'verified_at')
