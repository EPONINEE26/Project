from django.shortcuts import render
from brands.views import list_context

# 화면 출력: index.html · 화면 컨텍스트/폼을 템플릿에 전달
def index(request):
    context = list_context(request)
    context['page'] = 'home'
    return render(request, 'index.html', context)
