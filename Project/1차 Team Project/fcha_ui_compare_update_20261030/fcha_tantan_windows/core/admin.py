from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ModerationPolicy,ModerationEvent,FAQ,Notice,SupportTicket

@admin.register(ModerationPolicy)
class PolicyAdmin(admin.ModelAdmin):
    def has_add_permission(self,request):return not ModerationPolicy.objects.exists()
    def has_delete_permission(self,request,obj=None):return False

@admin.register(ModerationEvent)
class EventAdmin(admin.ModelAdmin):
    list_display=('target_type','target_id','action','actor','created_at')
    list_filter=('action','target_type')
    readonly_fields=('target_type','target_id','action','reason','actor','created_at')
    def has_add_permission(self,request):return False
    def has_delete_permission(self,request,obj=None):return False

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display=('question','category','audience','order','is_published')
    list_filter=('category','audience','is_published')
    search_fields=('question','answer')

admin.site.register(Notice)

@admin.register(SupportTicket)
class TicketAdmin(admin.ModelAdmin):
    list_display=('title','user','category','status','created_at','answered_at')
    list_filter=('status','category')
    readonly_fields=('user','category','title','content','created_at','answered_at')
    def save_model(self,request,obj,form,change):
        if obj.answer.strip() and ('answer' in form.changed_data):
            obj.status='answered';obj.answered_at=timezone.now()
        super().save_model(request,obj,form,change)
