"""네이버·카카오·구글 간편로그인 보조 코드 (django-allauth).

Client ID/Secret은 .env에만 두고 settings에서 읽습니다. 키가 없는 제공자는 버튼을 숨깁니다.
"""
from django.conf import settings
from django.dispatch import receiver
from django.shortcuts import redirect
from allauth.account.signals import user_signed_up
from .models import MemberProfile

PROVIDER_LABELS = [('naver', '네이버'), ('kakao', '카카오'), ('google', '구글')]


def social_providers(request):
    enabled = settings.SOCIALACCOUNT_PROVIDERS
    return {'social_providers': [{'id': key, 'label': label} for key, label in PROVIDER_LABELS if key in enabled]}


@receiver(user_signed_up)
def create_social_profile(sender, request, user, **kwargs):
    # 간편로그인으로 처음 가입하면 추가 정보 입력 전까지 미완성 프로필로 둡니다.
    if kwargs.get('sociallogin') is not None:
        MemberProfile.objects.get_or_create(user=user, defaults={'signup_source': 'social', 'is_complete': False})


class ProfileCompletionMiddleware:
    """간편로그인 가입자가 추가 정보(동의 포함)를 입력하기 전에는 다른 화면으로 가지 않게 합니다."""
    ALLOWED = ('/accounts/profile/', '/accounts/email/', '/accounts/logout/', '/oauth/', '/static/', '/admin/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and not request.path.startswith(self.ALLOWED):
            profile = MemberProfile.objects.filter(user=user).only('is_complete').first()
            if profile is not None and not profile.is_complete:
                return redirect('accounts:profile')
        return self.get_response(request)
