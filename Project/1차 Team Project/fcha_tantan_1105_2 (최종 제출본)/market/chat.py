"""전체 대화: 로그인한 회원이 참여한 양도양수 1:1 채팅 목록과 새 채팅 수.

대화방 = 매물 문의(TransferInquiry) 1건. 참여자는 문의자(sender)와 매물 등록자(listing.owner)뿐입니다.
새 채팅 = 상대가 보낸 안 읽은 메시지 + (등록자에게) 아직 확인하지 않은 첫 문의.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.db.models.functions import Coalesce, Greatest
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET
from .models import TransferInquiry


def conversations(user):
    rows = (TransferInquiry.objects.filter(Q(sender=user) | Q(listing__owner=user))
            .select_related('listing', 'listing__owner', 'sender')
            .annotate(last_message_at=Max('chat_messages__created_at'),
                      unread_messages=Count('chat_messages', filter=Q(chat_messages__is_read=False) & ~Q(chat_messages__sender=user)))
            .annotate(last_activity=Greatest('created_at', Coalesce('last_message_at', 'created_at')))
            .order_by('-last_activity', '-pk'))
    items = []
    for inquiry in rows:
        is_owner = inquiry.listing.owner_id == user.pk
        partner = inquiry.sender if is_owner else inquiry.listing.owner
        last = inquiry.chat_messages.order_by('-created_at', '-pk').first()
        unread = inquiry.unread_messages + (1 if is_owner and not inquiry.is_read else 0)
        items.append({'inquiry': inquiry, 'partner': partner, 'is_owner': is_owner, 'unread': unread,
                      'last_text': last.body if last else inquiry.message,
                      'last_at': last.created_at if last else inquiry.created_at})
    return items


@login_required
@require_GET
def chat_list(request):
    from brands.views import context_for
    items = conversations(request.user)
    context = context_for(request)
    context.update(page='chats', conversations=items, unread_total=sum(i['unread'] for i in items))
    return render(request, 'market/chat_list.html', context)


@login_required
@require_GET
def chat_summary(request):
    # 본인 대화 전체를 반환하고 펼침 패널에서 스크롤합니다.
    items = conversations(request.user)
    return JsonResponse({
        'unread': sum(i['unread'] for i in items),
        'unread_people': len({i['partner'].pk for i in items if i['unread']}),
        'items': [{'url': reverse('market:transfer_chat', args=[i['inquiry'].pk]), 'partner': i['partner'].first_name or i['partner'].username,
                   'listing': i['inquiry'].listing.title, 'text': i['last_text'][:60], 'unread': i['unread'],
                   'at': timezone.localtime(i['last_at']).strftime('%m.%d %H:%M')} for i in items],
    })
