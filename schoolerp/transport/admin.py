from django.contrib import admin
from transport.models import Vehicle, VehicleRoute

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('vehicle_number', 'vehicle_type', 'capacity', 'driver_name', 'driver_phone', 'registration_number', 'is_active')
    list_filter = ('vehicle_type', 'is_active')
    search_fields = ('vehicle_number', 'registration_number', 'driver_name')
    ordering = ('vehicle_number',)

@admin.register(VehicleRoute)
class VehicleRouteAdmin(admin.ModelAdmin):
    list_display = ('route_code', 'route_name', 'start_point', 'end_point', 'distance_km', 'fare_amount', 'vehicle', 'is_active')
    list_filter = ('is_active', 'vehicle')
    search_fields = ('route_name', 'route_code', 'start_point', 'end_point')
    ordering = ('route_name',)
