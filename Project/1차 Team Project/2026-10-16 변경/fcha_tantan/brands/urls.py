from django.urls import path
from . import views

app_name = 'brands'
urlpatterns = [
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
]
