from django.contrib import admin
from django.urls import include, path
from brands import api_views

urlpatterns = [
    path('accounts/', include('accounts.urls')),
    path('admin/', admin.site.urls),
    path('', include('home.urls')),
    path('brands/', include('brands.urls')),
    path('api/v1/brands/', api_views.brand_list),
    path('api/v1/brands/<slug:slug>/', api_views.brand_detail),
]
