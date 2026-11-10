from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import MemberLoginView, signup, profile
from . import email_verify
app_name = 'accounts'
urlpatterns = [path('login/',MemberLoginView.as_view(),name='login'), path('signup/',signup,name='signup'), path('logout/',LogoutView.as_view(),name='logout'),
               path('profile/', profile, name='profile'),
               path('email/send/', email_verify.send_code, name='email_send'),
               path('email/check/', email_verify.check_code, name='email_check')]
