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
from .forms import PostForm, CommentForm, SelectBrandForm, can_write, is_founder


def context(request):
    result=context_for(request);result['page']='community'
    result['can_post']=can_write(request.user)
    result['is_founder']=is_founder(request.user)
    return result


def owner_required(request):
    # 작성 가능: 승인된 점주 인증 회원 또는 예비 창업주(창업 목적 회원)
    if not can_write(request.user):
        messages.info(request,'게시글·댓글은 점주 인증 승인 회원 또는 예비 창업주(마이페이지에서 창업 목적 선택)만 작성할 수 있어요.')
        return redirect('community:verify')


def record_match(obj,request,fields):
    found=flag_content(obj,request,fields);obj.save()
    if found:
        ModerationEvent.objects.create(target_type=obj._meta.label_lower,target_id=obj.pk,action=obj.moderation_state,reason=obj.moderation_reason,actor=request.user)
        messages.info(request,'비속어를 제거했습니다. 검토가 필요한 내용은 블라인드되며 관리자 확인 후 공개됩니다.')


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


# 화면 출력: community/detail.html · 조회 데이터: Comment, Post
@require_GET
def detail(request,pk):
    post=get_object_or_404(Post.objects.select_related('author','brand'),pk=pk)
    comments=post.comments.select_related('author','brand') if post.moderation_state=='visible' else Comment.objects.none()
    data=context(request);data.update(post=post,comments_list=comments,form=CommentForm(user=request.user),is_author=request.user.pk==post.author_id)
    return render(request,'community/detail.html',data)


# 화면 출력: community/form.html · 화면 컨텍스트/폼을 템플릿에 전달
@login_required
@require_http_methods(['GET','POST'])
def edit(request,pk=None):
    post=get_object_or_404(Post,pk=pk,author=request.user) if pk else None
    blocked=owner_required(request)
    if blocked:return blocked
    topic=request.GET.get('topic')
    initial={'topic':topic} if not post and topic in dict(Post.TOPICS) else None
    form=PostForm(request.POST or None,instance=post,user=request.user,initial=initial)
    if request.method=='POST' and form.is_valid():
        item=form.save(commit=False);item.author=request.user
        record_match(item,request,('title','content'))
        messages.success(request,'게시글을 저장했습니다.');return redirect('community:detail',pk=item.pk)
    data=context(request);data.update(form=form,post=post)
    return render(request,'community/form.html',data)


@login_required
@require_POST
def delete(request,pk):
    post=get_object_or_404(Post,pk=pk,author=request.user)
    post.delete();messages.success(request,'게시글을 삭제했습니다.')
    return redirect('community:index')


# 화면 출력: community/detail.html · 화면 컨텍스트/폼을 템플릿에 전달
@login_required
@require_POST
def comment_create(request,pk):
    post=get_object_or_404(Post,pk=pk,moderation_state='visible')
    blocked=owner_required(request)
    if blocked:return blocked
    form=CommentForm(request.POST,user=request.user)
    if form.is_valid():
        comment=form.save(commit=False);comment.author=request.user;comment.post=post
        record_match(comment,request,('content',))
        return redirect('community:detail',pk=post.pk)
    data=context(request);data.update(post=post,comments_list=post.comments.select_related('author','brand'),form=form,is_author=request.user.pk==post.author_id)
    return render(request,'community/detail.html',data,status=400)


# 화면 출력: community/form.html · 조회 데이터: Comment
@login_required
@require_http_methods(['GET','POST'])
def comment_edit(request,pk):
    comment=get_object_or_404(Comment.objects.select_related('post'),pk=pk,author=request.user,post__moderation_state='visible')
    blocked=owner_required(request)
    if blocked:return blocked
    form=CommentForm(request.POST or None,instance=comment,user=request.user)
    if request.method=='POST' and form.is_valid():
        item=form.save(commit=False);record_match(item,request,('content',))
        return redirect('community:detail',pk=comment.post_id)
    data=context(request);data.update(form=form,comment=comment)
    return render(request,'community/form.html',data)


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
