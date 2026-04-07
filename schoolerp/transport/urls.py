from django.urls import path
from transport import views

urlpatterns = [
    # Vehicle URLs
    path('vehicle/', views.vehicle_list, name='vehicle_list'),
    path('vehicle/add/', views.vehicle_add, name='vehicle_add'),
    path('vehicle/<int:vehicle_id>/data/', views.vehicle_get_data, name='vehicle_get_data'),
    path('vehicle/<int:vehicle_id>/edit/', views.vehicle_edit, name='vehicle_edit'),
    path('vehicle/<int:vehicle_id>/delete/', views.vehicle_delete, name='vehicle_delete'),

    # Vehicle Route URLs
    path('route/', views.vehicle_route_list, name='vehicle_route_list'),
    path('route/add/', views.vehicle_route_add, name='vehicle_route_add'),
    path('route/<int:route_id>/data/', views.vehicle_route_get_data, name='vehicle_route_get_data'),
    path('route/<int:route_id>/edit/', views.vehicle_route_edit, name='vehicle_route_edit'),
    path('route/<int:route_id>/delete/', views.vehicle_route_delete, name='vehicle_route_delete'),
]