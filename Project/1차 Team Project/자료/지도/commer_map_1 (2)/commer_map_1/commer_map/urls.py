from django.contrib import admin
from django.urls import path
from myapp.views import commercial_map_view  # 별칭(as) 없이 직접 임포트

urlpatterns = [
    path('admin/', admin.site.urls),
    path(
        'cmap/', commercial_map_view, name='cmap'
    ),  # /cmap 경로로 정확히 연결
]