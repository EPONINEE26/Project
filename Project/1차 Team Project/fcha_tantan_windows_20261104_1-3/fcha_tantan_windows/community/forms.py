from django import forms
from django.db.models import Q
from django.utils import timezone
from brands.models import Brand, OwnerVerification
from brands.lookup import BrandLookupField
from .models import Post, Comment


def verified_brands(user):
    if not user.is_authenticated:return Brand.objects.none()
    ids=OwnerVerification.objects.filter(user=user,status='approved').filter(Q(contract_end_date__isnull=True)|Q(contract_end_date__gte=timezone.localdate())).values('brand_id')
    return Brand.objects.filter(pk__in=ids).order_by('name')


class VerifiedBrandMixin:
    def __init__(self,*args,user=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['brand'].queryset=verified_brands(user)
        self.fields['brand'].empty_label='인증된 브랜드를 선택하세요'
        if self.fields['brand'].queryset.count()==1:
            self.fields['brand'].initial=self.fields['brand'].queryset.first()


class PostForm(VerifiedBrandMixin,forms.ModelForm):
    class Meta:
        model=Post
        fields=('brand','topic','title','content')
        widgets={'content':forms.Textarea(attrs={'rows':10,'maxlength':10000})}


class CommentForm(VerifiedBrandMixin,forms.ModelForm):
    class Meta:
        model=Comment
        fields=('brand','content')
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'경험과 도움이 되는 의견을 나눠주세요.'})}


class TipsCommentForm(forms.ModelForm):
    """매장 준비 꿀팁은 일반회원도 댓글 내용만 입력합니다."""
    class Meta:
        model=Comment
        fields=('content',)
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'궁금한 점이나 도움이 되는 의견을 남겨주세요.'})}


class SelectBrandForm(forms.Form):
    brand=BrandLookupField(label='인증할 브랜드')
