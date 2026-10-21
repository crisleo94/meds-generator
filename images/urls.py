from django.urls import path
from . import views

app_name = 'images'

urlpatterns = [
    path('ocr/', views.ocr_extract, name='ocr_extract'),
    path('convert/', views.convert_image, name='convert_image'),
]
