from django.urls import path
from . import views

app_name = 'cards'

urlpatterns = [
    # General
    path('', views.index, name='index'),

    # Herramienta 1: Impresión de Tarjetas
    path('upload/', views.upload_excel, name='upload_excel'),
    path('preview/', views.preview_cards, name='preview_cards'),
    path('download/', views.download_pdf, name='download_pdf'),

    # Herramienta 2: Ordenador de Listas (n8n)
    path('sort-list/', views.sort_list, name='sort_list'),
    path('download-sorted-txt/', views.download_sorted_txt, name='download_sorted_txt'),

    # Herramienta 3: Normalizador de Excel
    path('upload-normalizer/', views.upload_normalizer_excel, name='upload_normalizer_excel'),
    path('process-normalizer/', views.process_normalizer_excel, name='process_normalizer_excel'),
    path('download-normalized/<str:file_id>/', views.download_normalized_excel, name='download_normalized_excel'),
]
