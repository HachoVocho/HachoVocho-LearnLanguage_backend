from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import CityModel
from .serializers import CitySerializer
from response import Response as ResponseData

@api_view(['POST'])
def get_cities(request):
    """
    API to filter cities based on a search string.
    - If an exact match is found (case-insensitive), return only that city.
    - Otherwise, return cities containing the search string (limited to 10).
    """
    try:
        search_text = request.data.get('search', '').strip()
        print(f'search_text {search_text}')
        
        if not search_text:
            return Response(
                ResponseData.error("Search text is required"),
                status=status.HTTP_400_BAD_REQUEST
            )

        # Try finding an exact match first (case-insensitive)
        exact_match = CityModel.objects.filter(name__iexact=search_text).first()

        if exact_match:
            serializer = CitySerializer([exact_match], many=True)
        else:
            # Return first 10 cities that contain the search text
            cities = CityModel.objects.filter(name__icontains=search_text)[:10]
            serializer = CitySerializer(cities, many=True)

        return Response(
            ResponseData.success(data=serializer.data, message="Cities fetched successfully"),
            status=status.HTTP_200_OK
        )

    except Exception as exception:
        return Response(
            ResponseData.error(str(exception)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
