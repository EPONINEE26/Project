from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
class SignupForm(UserCreationForm):
    first_name = forms.CharField(label='닉네임', max_length=30)
    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'first_name', 'password1', 'password2')
class LoginForm(AuthenticationForm):
    username = forms.CharField(label='아이디', widget=forms.TextInput(attrs={'autocomplete':'username'}))
