from django.urls import path
from . import views
from . import closure_views

app_name='community'
urlpatterns=[path('',views.index,name='index'),path('new/',views.edit,name='new'),path('verify/',views.verify,name='verify'),
 path('<int:pk>/',views.detail,name='detail'),path('<int:pk>/edit/',views.edit,name='edit'),path('<int:pk>/delete/',views.delete,name='delete'),
 path('<int:pk>/comments/',views.comment_create,name='comment_create'),path('comments/<int:pk>/edit/',views.comment_edit,name='comment_edit'),
 path('comments/<int:pk>/delete/',views.comment_delete,name='comment_delete'),
 path('report/post/<int:pk>/',views.report,{'kind':'post'},name='report_post'),path('report/comment/<int:pk>/',views.report,{'kind':'comment'},name='report_comment')]


urlpatterns += [
    path("closure/", closure_views.closure_list, name="closure_list"),
    path("closure/verify/", closure_views.closure_verify, name="closure_verify"),
    path("closure/write/", closure_views.closure_write, name="closure_write"),
    path("closure/documents/<int:pk>/<str:kind>/", closure_views.closure_document, name="closure_document"),
    path("closure/<int:pk>/", closure_views.closure_detail, name="closure_detail"),
    path("closure/<int:pk>/edit/", closure_views.closure_edit, name="closure_edit"),
    path("closure/<int:pk>/delete/", closure_views.closure_delete, name="closure_delete"),
]