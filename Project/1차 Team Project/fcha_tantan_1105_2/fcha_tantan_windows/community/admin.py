from django.contrib import admin
from core.models import ModerationEvent
from .models import Post, Comment, Report


# 관리자 게시글·댓글 공통: 공개 상태 변경·검토 이력 저장 → 커뮤니티 노출 제어
class ModeratedAdmin(admin.ModelAdmin):
    list_display=('id','author','brand','moderation_state','is_demo','created_at')
    list_filter=('moderation_state','is_demo','created_at')
    search_fields=('author__username','brand__name','content')
    readonly_fields=('moderation_original','created_at','updated_at')
    autocomplete_fields=('brand','author')
    actions=('blind','remove','publish')
    def change_state(self,request,queryset,state):
        for item in queryset:
            item.moderation_state=state;item.save(update_fields=['moderation_state','updated_at'])
            ModerationEvent.objects.create(target_type=item._meta.label_lower,target_id=item.pk,action=state,reason=item.moderation_reason,actor=request.user)
    @admin.action(description='1차: 블라인드 처리')
    def blind(self,request,queryset):self.change_state(request,queryset,'blind')
    @admin.action(description='2차: 삭제 사유 안내로 대체')
    def remove(self,request,queryset):self.change_state(request,queryset,'removed')
    @admin.action(description='검토 완료: 공개 복원')
    def publish(self,request,queryset):self.change_state(request,queryset,'visible')
    def save_model(self,request,obj,form,change):
        super().save_model(request,obj,form,change)
        if 'moderation_state' in form.changed_data:
            ModerationEvent.objects.create(target_type=obj._meta.label_lower,target_id=obj.pk,action=obj.moderation_state,reason=obj.moderation_reason,actor=request.user)

# 관리자 Post: 점주 게시글 → 커뮤니티 목록·상세·작성자 글 목록
admin.site.register(Post,ModeratedAdmin)
# 관리자 Comment: 게시글 댓글 → 커뮤니티 상세 댓글 목록
admin.site.register(Comment,ModeratedAdmin)
# 관리자 Report: 게시글·댓글 신고 → 관리자 신고 검토 목록
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display=('id','reporter','post','comment','reason','processed','created_at')
    list_filter=('processed',)
    readonly_fields=('reporter','post','comment','reason','created_at')
