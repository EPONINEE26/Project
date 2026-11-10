from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ModerationPolicy,ModerationEvent,FAQ,Notice,SupportTicket

# 관리자 ModerationPolicy: 비속어·공개 제한 정책 → 게시물 필터·삭제 안내 문구
@admin.register(ModerationPolicy)
class PolicyAdmin(admin.ModelAdmin):
    def has_add_permission(self,request):return not ModerationPolicy.objects.exists()
    def has_delete_permission(self,request,obj=None):return False

# 관리자 ModerationEvent: 게시물 검토 작업 이력 → 관리자 검토 로그(일반 화면 비공개)
@admin.register(ModerationEvent)
class EventAdmin(admin.ModelAdmin):
    list_display=('target_type','target_id','action','actor','created_at')
    list_filter=('action','target_type')
    readonly_fields=('target_type','target_id','action','reason','actor','created_at')
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False

# 관리자 FAQ: 공개 FAQ·분류·대상 → 고객센터·챗봇 답변 자료
@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display=('question','category','audience','order','is_published')
    list_filter=('category','audience','is_published')
    search_fields=('question','answer')

# 관리자 Notice: 공개 공지 → 고객센터 공지 목록
admin.site.register(Notice)

# 관리자 SupportTicket: 회원 문의·관리자 답변 → 내 문의 목록/상세
@admin.register(SupportTicket)
class TicketAdmin(admin.ModelAdmin):
    list_display=('title','user','category','status','created_at','answered_at')
    list_filter=('status','category')
    readonly_fields=('user','category','title','content','created_at','answered_at')
    def save_model(self,request,obj,form,change):
        if obj.answer.strip() and ('answer' in form.changed_data):
            obj.status='answered';obj.answered_at=timezone.now()
        super().save_model(request,obj,form,change)
