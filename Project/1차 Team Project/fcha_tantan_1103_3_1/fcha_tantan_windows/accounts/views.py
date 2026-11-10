from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from brands.views import context_for
from .forms import SignupForm, LoginForm, ProfileForm, profile_initial
from .models import MemberProfile
from .email_verify import clear_verified, verified_email

def safe_next(request):
    value = request.POST.get('next', request.GET.get('next', ''))
    return value if url_has_allowed_host_and_scheme(value, allowed_hosts={request.get_host()}, require_https=request.is_secure()) else reverse('home:index')

class MemberLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(context_for(self.request))
        return context

@require_http_methods(['GET','POST'])
def signup(request):
    if request.user.is_authenticated: return redirect('home:index')
    form = SignupForm(request.POST or None, request=request)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        clear_verified(request)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        if user.member_profile.wants_startup:
            messages.success(request, '가입을 환영합니다. 입력하신 창업 조건으로 맞춤 브랜드를 추천해드려요.')
        else:
            messages.success(request, '가입을 환영합니다.')
        return redirect(safe_next(request))
    context = context_for(request)
    context.update(form=form, next=safe_next(request), verified_email=verified_email(request))
    return render(request, 'accounts/signup.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def profile(request):
    """간편로그인 첫 가입 시 추가 정보 입력, 이후에는 내 정보·창업 조건·동의 수정."""
    existing = MemberProfile.objects.filter(user=request.user).first()
    form = ProfileForm(request.POST or None, user=request.user, initial=profile_initial(request.user), request=request)
    if request.method == 'POST' and form.is_valid():
        first_time = existing is None or not existing.is_complete
        saved = form.save_profile(request.user, source=existing.signup_source if existing else 'local')
        clear_verified(request)
        messages.success(request, '정보를 저장했습니다.')
        if first_time:
            return redirect('brands:recommend' if saved.wants_startup else 'home:index')
        return redirect('accounts:profile')
    context = context_for(request)
    context.update(form=form, page='profile', completing=existing is not None and not existing.is_complete,
                   verified_email=verified_email(request),
                   email_on_file=request.user.email if existing and existing.email_verified_at else '')
    return render(request, 'accounts/profile.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def withdraw(request):
    from django.contrib.auth import logout
    from django.db import transaction
    from .models import EmailVerification
    error = ''
    if request.method == 'POST':
        if request.POST.get('confirmation') != '회원탈퇴' or request.POST.get('agree') != 'yes':
            error = '탈퇴 안내에 동의하고 회원탈퇴를 정확히 입력해주세요.'
        elif request.user.has_usable_password() and not request.user.check_password(request.POST.get('password', '')):
            error = '현재 비밀번호를 확인해주세요.'
        elif not request.user.has_usable_password() and verified_email(request) != request.user.email.lower():
            error = '현재 계정 이메일로 인증을 완료해주세요.'
        elif request.user.is_superuser:
            error = '최고관리자 계정은 이 화면에서 탈퇴할 수 없습니다.'
        else:
            with transaction.atomic():
                EmailVerification.objects.filter(email__iexact=request.user.email).delete()
                request.user.delete()
            logout(request)
            messages.success(request, '회원탈퇴가 완료됐습니다.')
            return redirect('home:index')
    context = context_for(request)
    context.update(error=error, needs_password=request.user.has_usable_password())
    return render(request, 'accounts/withdraw.html', context)
