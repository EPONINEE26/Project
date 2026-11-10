from django.urls import path
from . import views
from .calculator import calculator
from django.views.generic import RedirectView
from .lookup import brand_lookup
from . import reviews

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
    # 2026-11-05 맞춤 브랜드 추천 페이지 삭제(지역상권분석과 중복). 예전 링크·즐겨찾기는 지역상권분석으로 보냅니다.
    path('recommend/', RedirectView.as_view(pattern_name='brands:bregion', query_string=True), name='recommend'),
    path('lookup/', brand_lookup, name='lookup'),
    path('bview/<slug:slug>/verify/', reviews.verify, name='verify'),
    path('bview/<slug:slug>/review/', reviews.write_review, name='write_review'),
    path('contracts/<int:pk>/', reviews.contract_file, name='contract_file'),
]
