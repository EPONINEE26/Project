from django.contrib import admin
from django.urls import include, path
from brands import api_views

admin.site.site_header = '프차 탄탄 관리자'
admin.site.site_title = '프차 탄탄 관리자'

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('oauth/', include('allauth.urls')),
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('brands/', include('brands.urls')),
    path('partners/', include('partners.urls')),
    path('market/', include('market.urls')),
    path('api/v1/brands/', api_views.brand_list),
    path('api/v1/brands/<slug:slug>/', api_views.brand_detail),
]
