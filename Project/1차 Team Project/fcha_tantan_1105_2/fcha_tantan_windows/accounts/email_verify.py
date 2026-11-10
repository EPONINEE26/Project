"""회원가입 이메일 인증: 인증번호 받기 → 6자리 입력 → 인증 확인.

- 인증번호는 해시로만 저장, 10분 후 만료, 5회 틀리면 새로 받아야 합니다.
- 같은 이메일로 60초 안에 다시 보낼 수 없고, 한 세션에서 1시간에 5번까지 보낼 수 있습니다.
- 인증에 성공하면 세션에 이메일을 기록하고, 회원가입 저장 때 30분 안에 인증한 같은 이메일인지 확인합니다.
- 개발 환경(.env에 EMAIL_HOST 없음)에서는 메일 대신 runserver 콘솔에 인증 메일 내용이 찍힙니다.
"""
import secrets
import logging
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from django.views.decorators.http import require_POST
from .models import EmailVerification

CODE_TTL = timedelta(minutes=10)
VERIFIED_TTL = timedelta(minutes=30)
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_ATTEMPTS = 5
MAX_SENDS_PER_HOUR = 5
SESSION_KEY = 'email-verified'


def code_hash(email, code):
    return salted_hmac('fcha-email-verify', f'{email}:{code}').hexdigest()


def normalize(email):
    return (email or '').strip().lower()


def verified_email(request):
    """이 세션에서 30분 안에 인증한 이메일. 없으면 ''."""
    data = request.session.get(SESSION_KEY) or {}
    try:
        verified_at = timezone.datetime.fromisoformat(data.get('at', ''))
    except ValueError:
        return ''
    return data.get('email', '') if timezone.now() - verified_at <= VERIFIED_TTL else ''


def clear_verified(request):
    request.session.pop(SESSION_KEY, None)


def error(message, status=400, **extra):
    return JsonResponse({'ok': False, 'message': message, **extra}, status=status)


@require_POST
def send_code(request):
    email = normalize(request.POST.get('email'))
    try:
        validate_email(email)
    except ValidationError:
        return error('올바른 이메일 주소를 입력해주세요.')
    users = get_user_model().objects.filter(email__iexact=email)
    if request.user.is_authenticated:
        users = users.exclude(pk=request.user.pk)
    if users.exists():
        return error('이미 가입된 이메일입니다.')
    now = timezone.now()
    last = EmailVerification.objects.filter(email=email).first()
    if last and now - last.created_at < RESEND_COOLDOWN:
        wait = int((RESEND_COOLDOWN - (now - last.created_at)).total_seconds()) + 1
        return error(f'{wait}초 뒤에 다시 받을 수 있어요.', status=429, cooldown=wait)
    sent = [t for t in request.session.get('email-verify-sends', []) if now.timestamp() - t < 3600]
    if len(sent) >= MAX_SENDS_PER_HOUR:
        return error('인증번호 요청이 너무 많아요. 잠시 후 다시 시도해주세요.', status=429)
    code = f'{secrets.randbelow(1000000):06d}'
    record = EmailVerification.objects.create(email=email, code_hash=code_hash(email, code))
    try:
        delivered = send_mail('[프차 탄탄] 이메일 인증번호',
                  f'프차 탄탄 회원가입 인증번호는 {code} 입니다.\n10분 안에 입력해주세요. 요청하지 않았다면 이 메일을 무시하세요.',
                  settings.DEFAULT_FROM_EMAIL, [email])
        if delivered != 1:
            raise RuntimeError('Email backend did not accept message')
    except Exception:
        record.delete()
        logging.getLogger(__name__).warning('Verification email delivery failed; check SMTP configuration.')
        return error('인증메일 발송에 실패했습니다. 관리자에게 메일 서버 설정을 확인해달라고 요청해주세요.', status=503)
    request.session['email-verify-sends'] = sent + [now.timestamp()]
    clear_verified(request)
    return JsonResponse({'ok': True, 'message': ('개발 모드: 인증번호는 서버를 실행한 PC의 터미널에 출력됩니다. 실제 이메일 발송은 관리자 SMTP 설정이 필요합니다.' if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend' else '인증번호를 보냈어요. 메일함(스팸함 포함)을 확인해주세요.'),
                         'cooldown': int(RESEND_COOLDOWN.total_seconds())})


@require_POST
def check_code(request):
    email = normalize(request.POST.get('email'))
    code = (request.POST.get('code') or '').strip()
    record = EmailVerification.objects.filter(email=email, verified_at__isnull=True).first()
    if record is None or timezone.now() - record.created_at > CODE_TTL:
        return error('인증번호가 만료됐거나 없어요. 인증번호를 다시 받아주세요.')
    if record.attempts >= MAX_ATTEMPTS:
        return error('5회 틀려서 이 인증번호는 더 쓸 수 없어요. 다시 받아주세요.')
    if not (len(code) == 6 and code.isdigit() and constant_time_compare(record.code_hash, code_hash(email, code))):
        record.attempts += 1
        record.save(update_fields=['attempts'])
        return error(f'인증번호가 맞지 않아요. ({record.attempts}/{MAX_ATTEMPTS})')
    record.verified_at = timezone.now()
    record.save(update_fields=['verified_at'])
    request.session[SESSION_KEY] = {'email': email, 'at': record.verified_at.isoformat()}
    return JsonResponse({'ok': True, 'message': '이메일 인증이 완료됐어요.'})
