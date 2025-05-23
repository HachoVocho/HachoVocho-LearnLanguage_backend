# views.py  ────────────────────────────────────────────────────────────
import math
from django.http import JsonResponse
from django.db.models import Prefetch
from django.shortcuts import render
from landlord.models import (
    LandlordPropertyDetailsModel,
    LandlordRoomWiseBedModel,
)
from django.db.models import Q
from localization.models import CityModel

def home(request):
    context = {
        'features': [
            "AI-powered tenant-landlord matching",
            "Personality compatibility quizzes",
            "Secure in-app messaging",
            "Automated appointment scheduling",
            "Verified user profiles"
        ]
    }
    return render(request, 'core/home.html', context)

def city_autocomplete(request):
    query = request.GET.get('query', '')
    cities = CityModel.objects.filter(
        Q(name__icontains=query) | 
        Q(state__name__icontains=query)
    ).select_related('state')[:10]  # Limit to 10 results
    
    results = [{
        'id': city.id,
        'name': f"{city.name}, {city.state.name}",
        'state': city.state.name
    } for city in cities]
    
    return JsonResponse({'results': results})

# small Haversine helper (km)
def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371.0  # km
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(a))


def properties_by_city(request, city_id):
    """Lite listing for public landing page (no full address)."""
    try:
        city = CityModel.objects.select_related('state__country').get(id=city_id)
    except CityModel.DoesNotExist:
        return JsonResponse({'properties': []})

    props = (
        LandlordPropertyDetailsModel.objects
        .filter(property_city=city, is_active=True, is_deleted=False)
        .select_related('property_type')
        .prefetch_related(
            'property_media',
            'amenities',
            Prefetch(
                'rooms__beds',
                queryset=LandlordRoomWiseBedModel.objects.filter(is_active=True, is_deleted=False)
                            .prefetch_related('bed_media'),
            ),
        )
    )

    data = []
    for prop in props:
        # ------------ hero images -------------
        imgs = [m.file.url for m in prop.property_media.filter(is_active=True, media_type='image')[:5]]

        # ------------ beds --------------------
        beds_block = []
        for room in prop.rooms.all():
            private = room.number_of_beds == 1
            for bed in room.beds.all():
                pic = bed.bed_media.filter(is_active=True).first()
                beds_block.append({
                    'id'     : bed.id,
                    'room'   : room.room_name or (room.room_type and room.room_type.type_name) or 'Room',
                    'private': 'Private' if private else 'Shared',
                    'rent'   : f"{bed.rent_amount:.0f} {city.state.country.currency_symbol}",
                    'period' : '/month' if bed.is_rent_monthly else '/day',   # ← NEW
                    'image'  : pic.file.url if pic else None                  # may be None
                })

        # ------------ distance ----------------
        try:
            p_lat = float(prop.latitude)
            p_lon = float(prop.longitude)
            c_lat = float(city.latitude)
            c_lon = float(city.longitude)
            dist_km = round(haversine_distance(p_lat, p_lon, c_lat, c_lon), 1)
        except (TypeError, ValueError):
            dist_km = None  # coordinates missing

        data.append({
            'id'         : prop.id,
            'name'       : prop.property_name,
            'type'       : prop.property_type.type_name,
            'images'     : imgs,
            'beds'       : beds_block,
            'amenities'  : [a.name for a in prop.amenities.filter(is_active=True)][:6],
            'distance_km': dist_km,   # ← NEW
        })

    return JsonResponse({'properties': data})
