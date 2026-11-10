from django.urls import path
from . import views

app_name = 'market'
urlpatterns = [
    path('stores/', views.store_list, name='store_list'),
    path('stores/new/', views.store_edit, name='store_new'),
    path('stores/<int:pk>/', views.store_detail, name='store_detail'),
    path('stores/<int:pk>/edit/', views.store_edit, name='store_edit'),
    path('populations/<int:pk>/delete/', views.population_delete, name='population_delete'),
    path('transfer/', views.transfer_list, name='transfer_list'),
    path('transfer/new/', views.transfer_edit, name='transfer_new'),
    path('transfer/mine/', views.transfer_mine, name='transfer_mine'),
    path('transfer/<int:pk>/', views.transfer_detail, name='transfer_detail'),
    path('transfer/<int:pk>/edit/', views.transfer_edit, name='transfer_edit'),
]
