from django.urls import path
from . import views

urlpatterns = [
    path('list-types/', views.ListTypeListCreateView.as_view(), name='list-type-list-create'),
    path('list-items/', views.ListItemListCreateView.as_view(), name='list-item-list-create'),
    path('list-items/<str:code>/', views.ListItemByTypeView.as_view(), name='list-items-by-type'),
]
