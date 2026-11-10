from django.conf import settings
from .moderation import policy


def site_tools(request):
    config=getattr(request,'moderation_policy',None) or policy()
    return {'site_language': 'en' if request.COOKIES.get('tantan-language')=='en' else 'ko',
            'filter_terms': config.blocked_terms if config.enabled else [],
            'kakao_js_key': settings.KAKAO_JS_KEY}
