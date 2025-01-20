from django.shortcuts import render

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .serializers import LandlordSignupSerializer
from response import Response as ResponseData

@api_view(["POST"])
def landlord_signup(request):
    """API to handle landlord signup"""
    try:
        serializer = LandlordSignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # Save the data to the database
            return Response(
                ResponseData.success(
                    data=serializer.data,
                    message="Landlord signed up successfully. Please verify your email."
                ),
                status=status.HTTP_201_CREATED
            )
        return Response(
            ResponseData.error(serializer.errors),
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        return Response(
            ResponseData.error(str(e)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
