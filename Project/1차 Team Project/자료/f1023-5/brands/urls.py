from django.urls import path
from . import views
from .calculator import calculator

app_name = 'brands'
urlpatterns = [
    path('calculator/', calculator, name='calculator'),
    path('blist/', views.blist, name='blist'),
    path('bview/<slug:slug>/', views.bview, name='bview'),
    path('bcompare/', views.bcompare, name='bcompare'),
    path('bregion/', views.bregion, name='bregion'),
    path('bsaved/', views.bsaved, name='bsaved'),
    path('guide/', views.guide, name='guide'),
    path('compare/toggle/<slug:slug>/', views.compare_toggle, name='compare_toggle'),
    path('compare/clear/', views.compare_clear, name='compare_clear'),
    path('saved/toggle/<slug:slug>/', views.saved_toggle, name='saved_toggle'),
    path('compare/csv/', views.compare_csv, name='compare_csv'),
    # 창업비용 조회 API
    path('api/startup-cost/<slug:slug>/', views.startup_cost_api, name='startup_cost_api'),
]
