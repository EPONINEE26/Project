from django.urls import path
from . import views

urlpatterns = [
    # 1. 기존에 만들었던 상권 지도 화면
    path('map/', views.commercial_map_view, name='commercial_map'),
    
    # 2. 새로 추가한 자치구별/소분류별 업체 수 통계 화면
    path('stats/', views.store_stats_view, name='store_stats'),
]