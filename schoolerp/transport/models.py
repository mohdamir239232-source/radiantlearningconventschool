from django.db import models

class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('bus', 'Bus'),
        ('van', 'Van'),
        ('car', 'Car'),
        ('other', 'Other')
    ]

    vehicle_number = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=10, choices=VEHICLE_TYPE_CHOICES, default='bus')
    capacity = models.PositiveIntegerField()
    driver_name = models.CharField(max_length=100)
    driver_phone = models.CharField(max_length=15)
    conductor_name = models.CharField(max_length=100, blank=True, null=True)
    conductor_phone = models.CharField(max_length=15, blank=True, null=True)
    registration_number = models.CharField(max_length=20, unique=True)
    insurance_expiry = models.DateField()
    permit_expiry = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['vehicle_number']

    def __str__(self):
        return f"{self.vehicle_number} - {self.get_vehicle_type_display()}"

class VehicleRoute(models.Model):
    route_name = models.CharField(max_length=100, unique=True)
    route_code = models.CharField(max_length=20, unique=True)
    start_point = models.CharField(max_length=100)
    end_point = models.CharField(max_length=100)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    estimated_time = models.CharField(max_length=50)  # e.g., "2 hours 30 minutes"
    fare_amount = models.DecimalField(max_digits=8, decimal_places=2)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.SET_NULL, null=True, blank=True)
    stops = models.TextField(help_text="Comma-separated list of stops")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['route_name']

    def __str__(self):
        return f"{self.route_code} - {self.route_name}"

    def get_stops_list(self):
        """Return village names only (supports both plain stop and village:fare formats)."""
        return [item['village'] for item in self.get_village_fare_list() if item.get('village')]

    def get_village_fare_list(self):
        """Return list of {'village': str, 'fare': Decimal|None} parsed from stops."""
        entries = []
        for raw in self.stops.split(','):
            token = raw.strip()
            if not token:
                continue

            if ':' in token:
                village, fare = token.split(':', 1)
                village = village.strip()
                fare = fare.strip()
                entries.append({'village': village, 'fare': fare or None})
            else:
                entries.append({'village': token, 'fare': None})

        # Fallback for old rows where stops were saved as default "School" only.
        only_school = len(entries) == 1 and entries[0].get('village', '').lower() == 'school'
        if not entries or only_school:
            if self.end_point:
                entries = [{'village': self.end_point, 'fare': str(self.fare_amount) if self.fare_amount is not None else None}]

        return entries
