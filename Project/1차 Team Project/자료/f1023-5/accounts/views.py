from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods
from brands.views import context_for
from .forms import SignupForm, LoginForm

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
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect(safe_next(request))
    context = context_for(request)
    context.update(form=form, next=safe_next(request))
    return render(request, 'accounts/signup.html', context)
