from django.urls import path
from . import views

app_name = 'cards'

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload_excel, name='upload_excel'),
    path('preview/', views.preview_cards, name='preview_cards'),
    path('download/', views.download_pdf, name='download_pdf'),
]
