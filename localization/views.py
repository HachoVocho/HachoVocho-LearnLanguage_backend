from rest_framework.decorators import (
    api_view, 
    authentication_classes, 
    permission_classes
)
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache

from .models import CityModel, CountryModel
from .serializers import CitySerializer, CountrySerializer
from response import Response as ResponseData
from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_cities(request):
    """
    API to filter cities by search string.
    Accepts an optional JWT; request.user will be set if valid.
    """
    try:
        search_text = request.data.get('search', '').strip()
        if not search_text:
            return Response(
                ResponseData.error("Search text is required"),
                status=status.HTTP_400_BAD_REQUEST
            )

        exact = CityModel.objects.filter(name__iexact=search_text).first()
        if exact:
            qs = [exact]
        else:
            qs = CityModel.objects.filter(name__icontains=search_text)[:10]

        serializer = CitySerializer(qs, many=True)
        return Response(
            ResponseData.success(data=serializer.data, message="Cities fetched successfully"),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_countries(request):
    """
    API to filter countries by search string.
    Accepts an optional JWT; request.user will be set if valid.
    """
    try:
        search_text = request.data.get('search', '').strip()
        if not search_text:
            return Response(
                ResponseData.error("Search text is required"),
                status=status.HTTP_400_BAD_REQUEST
            )

        exact = CountryModel.objects.filter(name__iexact=search_text).first()
        if exact:
            qs = [exact]
        else:
            qs = CountryModel.objects.filter(name__icontains=search_text)[:10]

        serializer = CountrySerializer(qs, many=True)
        return Response(
            ResponseData.success(data=serializer.data, message="Countries fetched successfully"),
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
