"""URL configuration for the calculator app."""
from django.urls import path
from . import views

app_name = 'calculator'

urlpatterns = [
    path('', views.CalculatorView.as_view(), name='calculator'),
    path('entries/', views.EntryListView.as_view(), name='entry_list'),
    path('entries/<int:pk>/', views.EntryDetailView.as_view(), name='entry_detail'),
    path('entries/<int:pk>/delete/', views.EntryDeleteView.as_view(), name='entry_delete'),
    path('api/subcategories/<str:category>/', views.SubcategoryAPIView.as_view(), name='subcategories_api'),
]
