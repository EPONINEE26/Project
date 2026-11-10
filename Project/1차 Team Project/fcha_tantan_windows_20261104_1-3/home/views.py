from django.shortcuts import render
from brands.views import list_context

def index(request):
    context = list_context(request)
    context['page'] = 'home'
    return render(request, 'index.html', context)
