from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse
from django.urls import path, re_path
from django.views.static import serve
from brands import views

def frontend(request):
    # 동일 출처 API 모드로 전환. dist는 수정하지 않아 정적 데모와 소스를 공유합니다.
    html = (settings.FRONTEND_DIR / 'index.html').read_text(encoding='utf-8')
    return HttpResponse(html.replace('src="js/config.js"','src="/app-config.js"'))

def frontend_config(request):
    return HttpResponse("window.TANTAN_CONFIG={mode:'api',apiBase:'/api/v1'};", content_type='application/javascript')

urlpatterns = [path('admin/',admin.site.urls),path('api/v1/brands/',views.brand_list),path('api/v1/brands/<slug:slug>/',views.brand_detail),path('app-config.js',frontend_config),path('',frontend)]
# 로컬 개발 전용. 운영 배포에서는 웹서버/CDN에서 dist/css, dist/js, dist/assets를 제공하세요.
if settings.DEBUG:
    urlpatterns += [re_path(r'^(?P<path>(?:css|js|assets)/.+)$',serve,{'document_root':settings.FRONTEND_DIR})]
