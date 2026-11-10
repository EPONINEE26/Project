# 2026-11-05 전체 작업 코드와 설명
소스·DB 미변경. 검증된 수정안 사본입니다.

## 1. community/models.py | 23줄 | TOPICS
제시 코드로 교체
```python
    TOPICS=[('free','자유 이야기'),('operation','매장 운영'),('marketing','홍보·마케팅'),('question','점주 질문'),('transfer','양도·양수 경험'),('store_tips','매장 준비 꿀팁')]
```
설명: 글을 분류하는 선택 목록으로, store_tips는 저장할 값이고 매장 준비 꿀팁은 화면에 보여줄 이름입니다.

## 2. community/models.py | 27줄 | topic
제시 코드로 교체
```python
    topic=models.CharField('분류',max_length=12,choices=TOPICS,default='free')
```
설명: 선택한 분류를 저장하는 칸으로, choices=TOPICS는 선택 목록을 연결하고 default=free는 기본 분류를 정합니다.

## 3. community/models.py | 25·52줄 | Comment.brand
제시 코드로 교체
```python
    brand=models.ForeignKey('brands.Brand',on_delete=models.PROTECT,null=True,blank=True)
```
설명: null=True는 DB에 빈 값을 허용하고 blank=True는 입력 생략을 허용하여 브랜드 없는 일반회원 댓글을 저장하게 합니다.

## 4. community/forms.py | 9~12줄 | verified_brands
함수·클래스의 설정과 들여쓰기를 설명하는 코드
```python
def verified_brands(user):
    if not user.is_authenticated:return Brand.objects.none()
    ids=OwnerVerification.objects.filter(user=user,status='approved').filter(Q(contract_end_date__isnull=True)|Q(contract_end_date__gte=timezone.localdate())).values('brand_id')
    return Brand.objects.filter(pk__in=ids).order_by('name')
```
설명: 로그인 여부·승인 상태·계약 종료일을 확인하여 해당 회원의 유효한 인증 브랜드만 가져옵니다.

## 5. community/forms.py | 15~21줄 | VerifiedBrandMixin
함수·클래스의 설정과 들여쓰기를 설명하는 코드
```python
class VerifiedBrandMixin:
    def __init__(self,*args,user=None,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['brand'].queryset=verified_brands(user)
        self.fields['brand'].empty_label='인증된 브랜드를 선택하세요'
        if self.fields['brand'].queryset.count()==1:
            self.fields['brand'].initial=self.fields['brand'].queryset.first()
```
설명: 브랜드 선택 목록을 본인의 인증 브랜드로 제한하고 하나뿐이면 기본 선택값을 설정합니다.

## 6. community/forms.py | 31~36줄 | CommentForm
함수·클래스의 설정과 들여쓰기를 설명하는 코드
```python
class CommentForm(VerifiedBrandMixin,forms.ModelForm):
    brand=forms.ModelChoiceField(queryset=Brand.objects.none(),required=True,label='브랜드')
    class Meta:
        model=Comment
        fields=('brand','content')
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'경험과 도움이 되는 의견을 나눠주세요.'})}
```
설명: 기존 게시판에서는 인증 브랜드와 댓글 내용을 입력받고 required=True로 브랜드 선택을 필수로 정합니다.

## 7. community/forms.py | 45~50줄 | TipsCommentForm
함수·클래스의 설정과 들여쓰기를 설명하는 코드
```python
class TipsCommentForm(forms.ModelForm):
    """매장 준비 꿀팁은 일반회원도 댓글 내용만 입력합니다."""
    class Meta:
        model=Comment
        fields=('content',)
        widgets={'content':forms.Textarea(attrs={'rows':3,'maxlength':2000,'placeholder':'궁금한 점이나 도움이 되는 의견을 남겨주세요.'})}
```
설명: 꿀팁에서는 fields=(content,)로 댓글 내용만 입력받고 브랜드 선택을 요구하지 않습니다.

## 8. community/views.py | 14줄 | forms import
제시 코드로 교체
```python
from .forms import PostForm, CommentForm, TipsCommentForm, SelectBrandForm, verified_brands
```
설명: 다른 파일에 있는 입력창과 인증 브랜드 조회 함수를 이 파일에서 사용할 수 있게 가져옵니다.

## 9. community/views.py | 28~30줄 | may_comment
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
def may_comment(user,post):
    """꿀팁은 로그인 회원, 다른 분류는 기존 인증 점주만 댓글 허용."""
    return user.is_authenticated and (post.topic=='store_tips' or verified_brands(user).exists())
```
설명: 로그인했고 꿀팁 글이거나 인증 브랜드가 있으면 댓글을 작성할 수 있다는 결과를 돌려줍니다.

## 10. community/views.py | 39~42줄 | comment_form_for
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
def comment_form_for(post,user,data=None,instance=None):
    if post.topic=='store_tips':
        return TipsCommentForm(data,instance=instance)
    return CommentForm(data,user=user,instance=instance)
```
설명: 게시글 종류에 맞는 입력창을 선택하며 data는 제출 내용이고 instance는 수정할 기존 댓글입니다.

## 11. community/views.py | 57~76줄 / 116~131줄 | comment_create
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
@login_required
@require_POST
def comment_create(request,pk):
    post=get_object_or_404(Post,pk=pk,moderation_state='visible')
    if post.topic!='store_tips':
        blocked=owner_required(request)
        if blocked:return blocked
    form=comment_form_for(post,request.user,request.POST)
    if form.is_valid():
        comment=form.save(commit=False);comment.author=request.user;comment.post=post
        if post.topic=='store_tips':
            comment.brand=verified_brands(request.user).first()
        record_match(comment,request,('content',))
        return redirect('community:detail',pk=post.pk)
    data=context(request);data.update(post=post,comments_list=post.comments.select_related('author','brand'),form=form,can_comment=may_comment(request.user,post),is_author=request.user.pk==post.author_id)
    return render(request,'community/detail.html',data,status=400)
```
설명: 공개 글 조회→분류별 인증 확인→입력 검사→작성자·글 연결→내용 검수와 저장→게시글 이동 순서로 댓글을 등록합니다.

## 12. community/views.py | 88~94줄 | detail
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
@require_GET
def detail(request,pk):
    post=get_object_or_404(Post.objects.select_related('author','brand'),pk=pk)
    comments=post.comments.select_related('author','brand') if post.moderation_state=='visible' else Comment.objects.none()
    # 게시글 상세 화면에 분류별 댓글 입력창과 댓글 작성 가능 여부를 게시글·댓글 목록과 함께 전달
    data=context(request);data.update(post=post,comments_list=comments,form=comment_form_for(post,request.user),can_comment=may_comment(request.user,post),is_author=request.user.pk==post.author_id)
    return render(request,'community/detail.html',data)
```
설명: 게시글·댓글 목록과 분류에 맞는 댓글 입력창 및 can_comment를 화면에 전달합니다.

## 13. community/views.py | 135~149줄 | comment_edit
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
@login_required
@require_http_methods(['GET','POST'])
def comment_edit(request,pk):
    comment=get_object_or_404(Comment.objects.select_related('post'),pk=pk,author=request.user,post__moderation_state='visible')
    # 꿀팁이 아닌 댓글에만 점주 인증을 요구하고, instance=comment로 수정할 댓글을 지정하여 게시글 종류에 맞는 입력창으로 수정
    if comment.post.topic!='store_tips':
        blocked=owner_required(request)
        if blocked:return blocked
    form=comment_form_for(comment.post,request.user,request.POST if request.method=='POST' else None,instance=comment)

    if request.method=='POST' and form.is_valid():
        item=form.save(commit=False);record_match(item,request,('content',))
        return redirect('community:detail',pk=comment.post_id)
    data=context(request);data.update(form=form,comment=comment)
    return render(request,'community/form.html',data)
```
설명: 본인 댓글을 찾아 꿀팁은 일반회원도 수정하도록 하며 instance로 기존 댓글을 지정합니다.

## 14. community/views.py | 153~157줄 | comment_delete
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
@login_required
@require_POST
def comment_delete(request,pk):
    comment=get_object_or_404(Comment,pk=pk,author=request.user);post_id=comment.post_id
    comment.delete();return redirect('community:detail',pk=post_id)
```
설명: 로그인한 작성자 본인의 댓글만 삭제하고 해당 게시글 화면으로 돌아갑니다.

## 15. community/views.py | 79~84줄 | delete
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
@login_required
@require_POST
def delete(request,pk):
    post=get_object_or_404(Post,pk=pk,author=request.user)
    post.delete();messages.success(request,'게시글을 삭제했습니다.')
    return redirect('community:index')
```
설명: 본인 게시글을 삭제하고 목록으로 이동하며 urls.py가 참조하는 views.delete 함수를 제공합니다.

## 16. community/views.py | 32~36줄 | record_match
완성 코드 시트의 단일 함수 구성 참고 / 같은 이름의 함수를 중복 추가하지 않음
```python
def record_match(obj,request,fields):
    found=flag_content(obj,request,fields);obj.save()
    if found:
        ModerationEvent.objects.create(target_type=obj._meta.label_lower,target_id=obj.pk,action=obj.moderation_state,reason=obj.moderation_reason,actor=request.user)
        messages.info(request,'비속어를 제거했습니다. 검토가 필요한 내용은 블라인드되며 관리자 확인 후 공개됩니다.')
```
설명: 금지어를 검사하고 댓글을 저장하며 감지 결과에 따라 검토 기록과 안내 메시지를 만듭니다.

## 17. community/urls.py | 생성된 파일 / 명령 실행 위치 | 댓글·게시글 주소
주소 연결 설명용
```python
from django.urls import path
from . import views
app_name='community'
urlpatterns=[path('',views.index,name='index'),path('new/',views.edit,name='new'),path('verify/',views.verify,name='verify'),
 path('<int:pk>/',views.detail,name='detail'),path('<int:pk>/edit/',views.edit,name='edit'),path('<int:pk>/delete/',views.delete,name='delete'),
 path('<int:pk>/comments/',views.comment_create,name='comment_create'),path('comments/<int:pk>/edit/',views.comment_edit,name='comment_edit'),
 path('comments/<int:pk>/delete/',views.comment_delete,name='comment_delete'),
 path('report/post/<int:pk>/',views.report,{'kind':'post'},name='report_post'),path('report/comment/<int:pk>/',views.report,{'kind':'comment'},name='report_comment')]

```
설명: 주소와 함수 이름을 연결하며 comment_create는 댓글 등록, comment_delete는 댓글 삭제, delete는 게시글 삭제입니다.

## 18. community/migrations/0002_owner_tips_member_comments.py | 생성된 파일 / 명령 실행 위치 | DB 변경 기록
Django가 생성하는 파일이며 초기 마이그레이션에 웹 요청 처리 함수를 넣지 않음
```python
# Generated by Django 5.2.18 on 2026-11-05 03:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('brands', '0008_adslot_cpc_bid_krw'),
        ('community', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='brand',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='brands.brand'),
        ),
        migrations.AlterField(
            model_name='post',
            name='topic',
            field=models.CharField(choices=[('free', '자유 이야기'), ('operation', '매장 운영'), ('marketing', '홍보·마케팅'), ('question', '점주 질문'), ('transfer', '양도·양수 경험'), ('store_tips', '매장 준비 꿀팁')], default='free', max_length=12, verbose_name='분류'),
        ),
    ]

```
설명: Comment.brand의 빈 값 허용과 Post.topic의 꿀팁 선택 항목을 DB 변경 기록에 반영합니다.

## 19. community/templates/community/author.html | 6줄 | 작성자 표시
제시 코드로 교체
```django
        <small class="owner-brand">{% if item.brand_id %}{{ item.brand.name|clean_brand_name }} 점주{% else %}일반회원{% endif %}{% if item.is_demo %} · 예시{% endif %}</small>
```
설명: 브랜드가 있으면 브랜드명과 점주를, 없으면 일반회원을 표시합니다.

## 20. community/templates/community/detail.html | 84줄 | 댓글 입력창 조건
현재 82~84줄 전체를 이 한 줄로 교체 / 84줄 한 줄만 다시 쓰는 작업이 아님
```django
            {% elif can_comment %}
```
설명: 댓글 작성 권한이 참일 때 입력창을 보여주며 HTML 주석 안의 can_post도 실행되므로 옛 조건을 함께 교체해야 합니다.

## 21. community/templates/community/detail.html | 85줄 | 댓글 등록 폼
제시 코드로 교체
```django
<form method="post" action="{% url 'community:comment_create' post.pk %}" class="form-stack comment-form">{% csrf_token %}{% include 'includes/form_fields.html' %}<button class="button">댓글 등록</button></form>
```
설명: post.pk로 댓글이 달릴 게시글 번호를 전달하고 csrf_token과 입력 내용을 댓글 등록 주소로 제출합니다.