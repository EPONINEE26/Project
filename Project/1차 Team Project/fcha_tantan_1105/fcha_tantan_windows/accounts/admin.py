from django.contrib import admin
from .models import EmailVerification, MemberProfile, SavedBrand
# 관리자 SavedBrand: 회원별 관심 브랜드 → 관심 목록·저장 버튼 상태
@admin.register(SavedBrand)
class SavedBrandAdmin(admin.ModelAdmin):
    list_display = ('user', 'brand', 'created_at')
    search_fields = ('user__username', 'brand__name')


# 관리자 MemberProfile: 회원 연락처·창업 희망조건·동의 → 내 정보·사업제안 대상 조회
@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'signup_source', 'email_verified_at', 'wants_startup', 'desired_region', 'desired_category', 'budget_manwon',
                    'agree_marketing', 'agree_proposal', 'is_complete', 'created_at')
    list_filter = ('signup_source', 'wants_startup', 'agree_marketing', 'agree_proposal', 'is_complete', 'desired_region')
    search_fields = ('user__username', 'user__first_name')


# 관리자 EmailVerification: 이메일 인증번호 해시·만료/시도 기록 → 가입·탈퇴 인증 처리(번호 원문 출력 없음)
@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'attempts', 'verified_at')
    search_fields = ('email',)
    readonly_fields = ('email', 'code_hash', 'attempts', 'created_at', 'verified_at')
