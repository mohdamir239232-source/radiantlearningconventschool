from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from schoolerp.access import require_module_access
from transport.models import Vehicle, VehicleRoute
from datetime import date


def _parse_village_fares(raw_text):
    """Parse lines as Village|Fare or Village:Fare into [{'village','fare'}]."""
    rows = []
    for line in (raw_text or '').splitlines():
        token = line.strip()
        if not token:
            continue

        if '|' in token:
            village, fare = token.split('|', 1)
        elif ':' in token:
            village, fare = token.split(':', 1)
        else:
            village, fare = token, ''

        village = village.strip()
        fare = fare.strip()
        if not village:
            continue
        rows.append({'village': village, 'fare': fare})
    return rows


def _parse_village_fares_from_request(request):
    """Parse village/fare pairs from dynamic form rows and keep multiline fallback."""
    default_village = request.POST.get('end_point', '').strip()
    default_fare = request.POST.get('fare_amount', '').strip()

    villages = request.POST.getlist('additional_village[]') or request.POST.getlist('additional_village')
    fares = request.POST.getlist('additional_fare[]') or request.POST.getlist('additional_fare')

    rows = []
    if default_village:
        rows.append({'village': default_village, 'fare': default_fare})

    for idx, village in enumerate(villages):
        village = (village or '').strip()
        fare = (fares[idx] if idx < len(fares) else '')
        fare = (fare or '').strip()
        if village:
            rows.append({'village': village, 'fare': fare})

    if rows:
        return rows

    # Backward compatibility with old multiline field if present.
    village_fares_raw = request.POST.get('village_fares', '').strip()
    return _parse_village_fares(village_fares_raw)

# ===== VEHICLE MANAGEMENT =====
def vehicle_list(request):
    vehicles = Vehicle.objects.all()
    return render(request, 'transport/vehicle.html', {'vehicles': vehicles})

@require_http_methods(["POST"])
def vehicle_add(request):
    try:
        vehicle_number = request.POST.get('vehicle_number', '').strip()
        vehicle_type = request.POST.get('vehicle_type', '').strip()
        capacity = request.POST.get('capacity', '').strip()
        driver_name = request.POST.get('driver_name', '').strip()
        driver_phone = request.POST.get('driver_phone', '').strip()
        conductor_name = request.POST.get('conductor_name', '').strip()
        conductor_phone = request.POST.get('conductor_phone', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        insurance_expiry = request.POST.get('insurance_expiry', '').strip()
        permit_expiry = request.POST.get('permit_expiry', '').strip()

        if not all([vehicle_number, vehicle_type, capacity, driver_name, driver_phone, registration_number, insurance_expiry, permit_expiry]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if Vehicle.objects.filter(vehicle_number=vehicle_number).exists():
            return JsonResponse({'success': False, 'error': 'Vehicle number already exists'})

        if Vehicle.objects.filter(registration_number=registration_number).exists():
            return JsonResponse({'success': False, 'error': 'Registration number already exists'})

        Vehicle.objects.create(
            vehicle_number=vehicle_number,
            vehicle_type=vehicle_type,
            capacity=int(capacity),
            driver_name=driver_name,
            driver_phone=driver_phone,
            conductor_name=conductor_name if conductor_name else None,
            conductor_phone=conductor_phone if conductor_phone else None,
            registration_number=registration_number,
            insurance_expiry=insurance_expiry,
            permit_expiry=permit_expiry,
            is_active=True
        )

        return JsonResponse({'success': True, 'message': 'Vehicle added successfully'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def vehicle_get_data(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        return JsonResponse({
            'success': True,
            'vehicle': {
                'id': vehicle.id,
                'vehicle_number': vehicle.vehicle_number,
                'vehicle_type': vehicle.vehicle_type,
                'capacity': vehicle.capacity,
                'driver_name': vehicle.driver_name,
                'driver_phone': vehicle.driver_phone,
                'conductor_name': vehicle.conductor_name or '',
                'conductor_phone': vehicle.conductor_phone or '',
                'registration_number': vehicle.registration_number,
                'insurance_expiry': str(vehicle.insurance_expiry),
                'permit_expiry': str(vehicle.permit_expiry)
            }
        })
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vehicle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def vehicle_edit(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)

        vehicle_number = request.POST.get('vehicle_number', '').strip()
        vehicle_type = request.POST.get('vehicle_type', '').strip()
        capacity = request.POST.get('capacity', '').strip()
        driver_name = request.POST.get('driver_name', '').strip()
        driver_phone = request.POST.get('driver_phone', '').strip()
        conductor_name = request.POST.get('conductor_name', '').strip()
        conductor_phone = request.POST.get('conductor_phone', '').strip()
        registration_number = request.POST.get('registration_number', '').strip()
        insurance_expiry = request.POST.get('insurance_expiry', '').strip()
        permit_expiry = request.POST.get('permit_expiry', '').strip()

        if not all([vehicle_number, vehicle_type, capacity, driver_name, driver_phone, registration_number, insurance_expiry, permit_expiry]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if Vehicle.objects.filter(vehicle_number=vehicle_number).exclude(id=vehicle_id).exists():
            return JsonResponse({'success': False, 'error': 'Vehicle number already exists'})

        if Vehicle.objects.filter(registration_number=registration_number).exclude(id=vehicle_id).exists():
            return JsonResponse({'success': False, 'error': 'Registration number already exists'})

        vehicle.vehicle_number = vehicle_number
        vehicle.vehicle_type = vehicle_type
        vehicle.capacity = int(capacity)
        vehicle.driver_name = driver_name
        vehicle.driver_phone = driver_phone
        vehicle.conductor_name = conductor_name if conductor_name else None
        vehicle.conductor_phone = conductor_phone if conductor_phone else None
        vehicle.registration_number = registration_number
        vehicle.insurance_expiry = insurance_expiry
        vehicle.permit_expiry = permit_expiry
        vehicle.save()

        return JsonResponse({'success': True, 'message': 'Vehicle updated successfully'})
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vehicle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def vehicle_delete(request, vehicle_id):
    try:
        vehicle = Vehicle.objects.get(id=vehicle_id)
        vehicle.delete()
        return JsonResponse({'success': True, 'message': 'Vehicle deleted successfully'})
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Vehicle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

# ===== VEHICLE ROUTE MANAGEMENT =====
def vehicle_route_list(request):
    routes = VehicleRoute.objects.select_related('vehicle').all()
    vehicles = Vehicle.objects.filter(is_active=True)
    return render(request, 'transport/vehicle_route_simple.html', {'routes': routes, 'vehicles': vehicles})

@require_http_methods(["POST"])
def vehicle_route_add(request):
    try:
        route_name = request.POST.get('route_name', '').strip()
        route_code = request.POST.get('route_code', '').strip()
        end_point = request.POST.get('end_point', '').strip()
        fare_amount = request.POST.get('fare_amount', '').strip()
        vehicle_id = request.POST.get('vehicle', '').strip()

        # Set default values for hidden fields
        start_point = request.POST.get('start_point', 'School')
        distance_km = request.POST.get('distance_km', '10.00')
        estimated_time = request.POST.get('estimated_time', '30 minutes')
        stops = request.POST.get('stops', 'School')

        village_fares = _parse_village_fares_from_request(request)
        if village_fares:
            end_point = village_fares[0]['village']
            fare_amount = village_fares[0]['fare'] or fare_amount
            stops = ','.join(
                f"{entry['village']}:{entry['fare']}" if entry['fare'] else entry['village']
                for entry in village_fares
            )

        if not all([route_name, route_code, end_point, fare_amount]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if VehicleRoute.objects.filter(route_name=route_name).exists():
            return JsonResponse({'success': False, 'error': 'Route name already exists'})

        if VehicleRoute.objects.filter(route_code=route_code).exists():
            return JsonResponse({'success': False, 'error': 'Route code already exists'})

        vehicle = None
        if vehicle_id:
            vehicle = Vehicle.objects.get(id=vehicle_id)

        VehicleRoute.objects.create(
            route_name=route_name,
            route_code=route_code,
            start_point=start_point,
            end_point=end_point,
            distance_km=distance_km,
            estimated_time=estimated_time,
            fare_amount=fare_amount,
            vehicle=vehicle,
            stops=stops,
            is_active=True
        )

        return JsonResponse({'success': True, 'message': 'Vehicle route added successfully'})
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Selected vehicle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["GET"])
def vehicle_route_get_data(request, route_id):
    try:
        route = VehicleRoute.objects.get(id=route_id)
        village_fares = route.get_village_fare_list()
        return JsonResponse({
            'success': True,
            'route': {
                'id': route.id,
                'route_name': route.route_name,
                'route_code': route.route_code,
                'end_point': route.end_point,
                'fare_amount': str(route.fare_amount),
                'vehicle': route.vehicle.id if route.vehicle else '',
                'village_fare_items': village_fares,
            }
        })
    except VehicleRoute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Route not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def vehicle_route_edit(request, route_id):
    try:
        route = VehicleRoute.objects.get(id=route_id)

        route_name = request.POST.get('route_name', '').strip()
        route_code = request.POST.get('route_code', '').strip()
        end_point = request.POST.get('end_point', '').strip()
        fare_amount = request.POST.get('fare_amount', '').strip()
        vehicle_id = request.POST.get('vehicle', '').strip()

        # Set default values for hidden fields
        start_point = request.POST.get('start_point', 'School')
        distance_km = request.POST.get('distance_km', '10.00')
        estimated_time = request.POST.get('estimated_time', '30 minutes')
        stops = request.POST.get('stops', 'School')

        village_fares = _parse_village_fares_from_request(request)
        if village_fares:
            end_point = village_fares[0]['village']
            fare_amount = village_fares[0]['fare'] or fare_amount
            stops = ','.join(
                f"{entry['village']}:{entry['fare']}" if entry['fare'] else entry['village']
                for entry in village_fares
            )

        if not all([route_name, route_code, end_point, fare_amount]):
            return JsonResponse({'success': False, 'error': 'All required fields must be filled'})

        if VehicleRoute.objects.filter(route_name=route_name).exclude(id=route_id).exists():
            return JsonResponse({'success': False, 'error': 'Route name already exists'})

        if VehicleRoute.objects.filter(route_code=route_code).exclude(id=route_id).exists():
            return JsonResponse({'success': False, 'error': 'Route code already exists'})

        vehicle = None
        if vehicle_id:
            vehicle = Vehicle.objects.get(id=vehicle_id)

        route.route_name = route_name
        route.route_code = route_code
        route.start_point = start_point
        route.end_point = end_point
        route.distance_km = distance_km
        route.estimated_time = estimated_time
        route.fare_amount = fare_amount
        route.vehicle = vehicle
        route.stops = stops
        route.save()

        return JsonResponse({'success': True, 'message': 'Vehicle route updated successfully'})
    except VehicleRoute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Route not found'})
    except Vehicle.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Selected vehicle not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@require_http_methods(["POST"])
def vehicle_route_delete(request, route_id):
    try:
        route = VehicleRoute.objects.get(id=route_id)
        route.delete()
        return JsonResponse({'success': True, 'message': 'Vehicle route deleted successfully'})
    except VehicleRoute.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Route not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


for _transport_view_name in [
    'vehicle_list',
    'vehicle_add',
    'vehicle_get_data',
    'vehicle_edit',
    'vehicle_delete',
    'vehicle_route_list',
    'vehicle_route_add',
    'vehicle_route_get_data',
    'vehicle_route_edit',
    'vehicle_route_delete',
]:
    globals()[_transport_view_name] = require_module_access('transport')(globals()[_transport_view_name])
