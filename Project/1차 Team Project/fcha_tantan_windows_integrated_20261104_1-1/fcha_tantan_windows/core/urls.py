from django.urls import path
from . import views
app_name='core'
urlpatterns=[path('',views.help_center,name='help'),path('new/',views.ticket_new,name='ticket_new'),path('tickets/',views.tickets,name='tickets'),
 path('tickets/<int:pk>/',views.ticket_detail,name='ticket_detail'),path('language/',views.language,name='language'),path('chat/',views.chatbot,name='chat'),
 path('evidence/<str:kind>/<int:pk>/<str:document>/',views.evidence,name='evidence')]
