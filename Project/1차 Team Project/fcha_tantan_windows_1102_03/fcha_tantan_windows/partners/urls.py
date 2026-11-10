from django.urls import path
from . import views

app_name = 'partners'
urlpatterns = [
    path('', views.pricing, name='pricing'),
    path('apply/', views.apply, name='apply'),
    path('leads/', views.leads, name='leads'),
    path('leads/<int:profile_id>/propose/', views.send_proposal, name='send_proposal'),
    path('proposals/', views.inbox, name='inbox'),
    path('proposals/<int:pk>/respond/', views.respond, name='respond'),
]
