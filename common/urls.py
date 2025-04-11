from django.urls import path
from . import views

urlpatterns = [
    path('list-types/', views.ListTypeListCreateView.as_view(), name='list-type-list-create'),
    path('list-types/<int:pk>/', views.ListTypeUpdateView.as_view(), name='list-type-update'),
    path('list-types/<int:pk>/delete/', views.ListTypeDeleteView.as_view(), name='list-type-delete'),

    path('list-items/', views.ListItemListCreateView.as_view(), name='list-item-list-create'),
    path('list-items/<int:pk>/', views.ListItemUpdateView.as_view(), name='list-item-update'),
    path('list-items/<int:pk>/delete/', views.ListItemDeleteView.as_view(), name='list-item-delete'),

    path('list-items/<str:code>/', views.ListItemByTypeView.as_view(), name='list-items-by-type'),
]
