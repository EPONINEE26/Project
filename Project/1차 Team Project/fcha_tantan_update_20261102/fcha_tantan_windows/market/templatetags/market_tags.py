from django import template
from market.models import TransferListing

register = template.Library()


@register.inclusion_tag('market/includes/transfer_widget.html', takes_context=True)
def transfer_widget(context):
    # 메인·브랜드 탐색·지역 살펴보기 오른쪽에 고정되는 양도양수 패널입니다.
    listings = TransferListing.objects.filter(status='open').select_related('brand')[:3]
    return {'listings': listings, 'request': context.get('request'),
            'total': TransferListing.objects.filter(status='open').count()}
