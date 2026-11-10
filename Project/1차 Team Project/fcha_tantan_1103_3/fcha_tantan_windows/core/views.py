from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme
from brands.views import context_for
from .models import FAQ,Notice,SupportTicket
from .moderation import sanitize


@require_GET
def help_center(request):
    query=request.GET.get('query','').strip()[:100];category=request.GET.get('category','');audience=request.GET.get('audience','all')
    faqs=FAQ.objects.filter(is_published=True)
    if query:faqs=faqs.filter(Q(question__icontains=query)|Q(answer__icontains=query)|Q(question_en__icontains=query)|Q(answer_en__icontains=query))
    if category in dict(FAQ.CATEGORIES):faqs=faqs.filter(category=category)
    if audience in ('member','owner','partner'):faqs=faqs.filter(audience__in=['all',audience])
    data=context_for(request);data.update(page='help',faqs=faqs[:60],help_categories=FAQ.CATEGORIES,query=query,help_category=category,audience=audience,notices=Notice.objects.filter(is_published=True)[:5])
    return render(request,'core/help.html',data)


class TicketForm(forms.ModelForm):
    class Meta:
        model=SupportTicket
        fields=('category','title','content')
        widgets={'content':forms.Textarea(attrs={'rows':7,'maxlength':3000})}


@login_required
@require_http_methods(['GET','POST'])
def ticket_new(request):
    form=TicketForm(request.POST or None)
    if request.method=='POST' and form.is_valid():
        ticket=form.save(commit=False);ticket.user=request.user;ticket.save()
        messages.success(request,'문의를 접수했습니다. 내 문의 내역에서 답변을 확인하세요.')
        return redirect('core:ticket_detail',pk=ticket.pk)
    data=context_for(request);data.update(page='help',form=form)
    return render(request,'core/ticket_form.html',data)


@login_required
@require_GET
def tickets(request):
    data=context_for(request);data.update(page='help',tickets=SupportTicket.objects.filter(user=request.user))
    return render(request,'core/tickets.html',data)


@login_required
@require_GET
def ticket_detail(request,pk):
    ticket=get_object_or_404(SupportTicket,pk=pk,user=request.user)
    data=context_for(request);data.update(page='help',ticket=ticket)
    return render(request,'core/ticket_detail.html',data)


@require_POST
def language(request):
    lang=request.POST.get('language','ko')
    target=request.POST.get('next','/')
    if not url_has_allowed_host_and_scheme(target,{request.get_host()},require_https=request.is_secure()):target='/'
    response=redirect(target);response.set_cookie('tantan-language','en' if lang=='en' else 'ko',max_age=31536000,samesite='Lax')
    return response


@require_POST
def chatbot(request):
    question,_=sanitize(request.POST.get('question','').strip()[:500])
    if not question:return JsonResponse({'error':'질문을 입력해주세요.'},status=400)
    if not request.session.session_key:request.session.create()
    key='chat-limit:'+request.session.session_key
    if cache.add(key,1,60):count=1
    else:
        try:count=cache.incr(key)
        except ValueError:cache.set(key,1,60);count=1
    if count>30:return JsonResponse({'error':'잠시 뒤 다시 질문해주세요.'},status=429)
    from .chat import respond
    result=respond(question,request.user,request.POST.get('language','ko'),request.POST.get('path',''))
    return JsonResponse(result,json_dumps_params={'ensure_ascii':False})


@login_required
@require_GET
def evidence(request,kind,pk,document):
    if kind=='owner':
        from brands.models import OwnerVerification
        obj=get_object_or_404(OwnerVerification,pk=pk)
        allowed={'contract':'contract_file','business':'business_file'}
    elif kind=='partner':
        from partners.models import PartnerAccount
        obj=get_object_or_404(PartnerAccount,pk=pk)
        allowed={'business':'business_file','authorization':'authorization_file'}
    else:raise Http404
    if not (request.user.is_staff or obj.user_id==request.user.pk) or document not in allowed:raise Http404
    file=getattr(obj,allowed[document])
    if not file:raise Http404
    from pathlib import Path
    try:handle=file.open('rb')
    except OSError:raise Http404
    response=FileResponse(handle,as_attachment=True,filename=f'{kind}_{pk}_{document}{Path(file.name).suffix}')
    response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
    return response
