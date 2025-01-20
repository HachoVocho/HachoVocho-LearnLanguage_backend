from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import UserRoleModel
from response import Response as ResponseData
from .serializers import EmailVerificationSerializer

@api_view(["GET"])
def get_user_roles(request):
    """API to fetch user role choices"""
    try:
        roles = [
            {"role_name": choice[0], "description": choice[1]}
            for choice in UserRoleModel.ROLE_CHOICES
        ]
        return Response(
            ResponseData.success(data=roles, message="User roles fetched successfully"),
            status=status.HTTP_200_OK,
        )
    except Exception as exception:
        return Response(
            ResponseData.error(str(exception)),
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    


@api_view(["POST"])
def email_verification(request):
    """API to handle email verification for both tenant and landlord."""
    try:
        serializer = EmailVerificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                ResponseData.success_without_data("Email verified successfully."),
                status=status.HTTP_200_OK
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
    