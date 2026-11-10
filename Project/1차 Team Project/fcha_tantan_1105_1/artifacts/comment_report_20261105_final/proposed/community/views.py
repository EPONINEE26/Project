from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from brands.views import context_for
from brands.models import OwnerVerification
from core.moderation import flag_content, sanitize
from core.models import ModerationEvent
from .models import Post, Comment, Report
# from .forms import PostForm, CommentForm, SelectBrandForm, verified_brands
# f같은 폴더의 forms.py에서 입력창 클래스들과 인증 브랜드 조회 함수를 가져와 views.py에서 사용할 수 있게 함.
from .forms import PostForm, CommentForm, TipsCommentForm, SelectBrandForm, verified_brands


def context(request):
    result=context_for(request);result['page']='community'
    result['can_post']=verified_brands(request.user).exists()
    return result


def owner_required(request):
    if not verified_brands(request.user).exists():
        messages.info(request,'게시글·댓글 작성은 점주 인증 승인 후 이용할 수 있어요.')
        return redirect('community:verify')

def may_comment(user,post):
    """꿀팁은 로그인 회원, 다른 분류는 기존 인증 점주만 댓글 허용."""
    return user.is_authenticated and (post.topic=='store_tips' or verified_brands(user).exists())

def record_match(obj,request,fields):
    found=flag_content(obj,request,fields);obj.save()
    if found:
        ModerationEvent.objects.create(target_type=obj._meta.label_lower,target_id=obj.pk,action=obj.moderation_state,reason=obj.moderation_reason,actor=request.user)
        messages.info(request,'비속어를 제거했습니다. 검토가 필요한 내용은 블라인드되며 관리자 확인 후 공개됩니다.')

# 꿀팁에는 내용만 받는 폼을, 다른 게시판에는 브랜드도 받는 폼을 선택하며, data는 제출 내용이고 instance는 수정할 댓글
def comment_form_for(post,user,data=None,instance=None):
    if post.topic=='store_tips':
        return TipsCommentForm(data,instance=instance)
    return CommentForm(data,user=user,instance=instance)


# 화면 출력: community/index.html · 조회 데이터: Post
@require_GET
def index(request):
    query=request.GET.get('query','').strip()[:100];topic=request.GET.get('topic','')
    posts=Post.objects.select_related('author','brand').annotate(comment_total=Count('comments')).order_by('-created_at','-pk')
    if topic in dict(Post.TOPICS):posts=posts.filter(topic=topic)
    if query:posts=posts.filter(moderation_state='visible').filter(Q(title__icontains=query)|Q(content__icontains=query))
    page_obj=Paginator(posts,10).get_page(request.GET.get('page'))
    params=request.GET.copy();params.pop('page',None)
    data=context(request);data.update(posts=page_obj,topics=Post.TOPICS,topic=topic,query=query,page_obj=page_obj,page_query=params.urlencode(),page_range=list(page_obj.paginator.get_elided_page_range(page_obj.number)))
    return render(request,'community/index.html',data)


# 앞쪽 중복 함수 자리에 작성자 본인의 게시글을 삭제하는 delete()를 두어, urls.py가 views.delete를 찾지 못하는 오류를 해결
@login_required
@require_POST
def delete(request,pk):
    post=get_object_or_404(Post,pk=pk,author=request.user)
    post.delete();messages.success(request,'게시글을 삭제했습니다.')
    return redirect('community:index')

# 화면 출력: community/detail.html · 조회 데이터: Comment, Post
# 게시글 종류에 맞는 댓글 입력창과 댓글 작성 가능 여부인 can_comment를 화면에 전달
@require_GET
def detail(request,pk):
    post=get_object_or_404(Post.objects.select_related('author','brand'),pk=pk)
    comments=post.comments.select_related('author','brand') if post.moderation_state=='visible' else Comment.objects.none()
    # 게시글 상세 화면에 분류별 댓글 입력창과 댓글 작성 가능 여부를 게시글·댓글 목록과 함께 전달
    data=context(request);data.update(post=post,comments_list=comments,form=comment_form_for(post,request.user),can_comment=may_comment(request.user,post),is_author=request.user.pk==post.author_id)
    return render(request,'community/detail.html',data)


# 화면 출력: community/form.html · 화면 컨텍스트/폼을 템플릿에 전달
@login_required
@require_http_methods(['GET','POST'])
def edit(request,pk=None):
    post=get_object_or_404(Post,pk=pk,author=request.user) if pk else None
    blocked=owner_required(request)
    if blocked:return blocked
    form=PostForm(request.POST or None,instance=post,user=request.user)
    if request.method=='POST' and form.is_valid():
        item=form.save(commit=False);item.author=request.user
        record_match(item,request,('title','content'))
        messages.success(request,'게시글을 저장했습니다.');return redirect('community:detail',pk=item.pk)
    data=context(request);data.update(form=form,post=post)
    return render(request,'community/form.html',data)


# 화면 출력: community/detail.html · 화면 컨텍스트/폼을 템플릿에 전달
# 현재 같은 이름의 함수가 두 개여서 뒤쪽의 예전 함수가 앞쪽의 새 함수를 덮어쓰고 있음. 뒤쪽 것을 삭제해야 앞쪽에 작성한 꿀팁 댓글 처리가 사용
# 두 번째 댓글 등록 함수와 그 위 주석을 게시글 삭제 함수로 교체하여 중복을 없애고, 작성자 본인의 게시글을 삭제한 뒤 목록으로 돌아가게 함
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


# 화면 출력: community/form.html · 조회 데이터: Comment
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


# 로그인한 회원의 삭제 요청을 받아 본인의 댓글만 삭제하고, 삭제한 댓글이 달렸던 게시글 화면으로 돌아감
@login_required
@require_POST
def comment_delete(request,pk):
    comment=get_object_or_404(Comment,pk=pk,author=request.user);post_id=comment.post_id
    comment.delete();return redirect('community:detail',pk=post_id)
    


@login_required
@require_POST
def report(request,kind,pk):
    obj=get_object_or_404(Post if kind=='post' else Comment,pk=pk)
    reason,_=sanitize(request.POST.get('reason','운영정책 위반 검토 요청')[:300])
    Report.objects.get_or_create(reporter=request.user,**{kind:obj},defaults={'reason':reason or '검토 요청'})
    messages.success(request,'신고를 접수했습니다. 관리자가 내용을 검토합니다.')
    return redirect('community:detail',pk=obj.pk if kind=='post' else obj.post_id)


# 화면 출력: community/verify.html · 조회 데이터: OwnerVerification
@login_required
@require_http_methods(['GET','POST'])
def verify(request):
    form=SelectBrandForm(request.POST or None)
    if request.method=='POST' and form.is_valid():return redirect('brands:verify',slug=form.cleaned_data['brand'].slug)
    data=context(request);data.update(form=form,verifications=OwnerVerification.objects.filter(user=request.user).select_related('brand'))
    return render(request,'community/verify.html',data)

