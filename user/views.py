from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import UserRoleModel
from response import Response as ResponseData

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
