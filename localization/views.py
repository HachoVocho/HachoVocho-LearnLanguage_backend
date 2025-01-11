from rest_framework.response import Response
from language_data.models import LanguageModel
from localization.models import AllStaticStringsModel
from response import Response as ResponseData
from rest_framework.views import APIView
from django.core.exceptions import ObjectDoesNotExist

class StaticStringsAPIView(APIView):
    def post(self, request):
        lang_code = request.data.get('lang')

        try:
            language = LanguageModel.objects.get(translation_code=lang_code, is_active=True)
            # Fetch the static strings entry for the given page and language
            try:
                static_string_entry = AllStaticStringsModel.objects.get(
                    language=language, 
                    is_active=True
                )
            except ObjectDoesNotExist:
                return Response(
                    ResponseData.success_without_data("No Data Found"),
                    status=200
                )
            # Extract the strings JSON
            response_data = static_string_entry.strings

            return Response(
                ResponseData.success(response_data, "Static strings fetched successfully"),
                status=200
            )

        except (LanguageModel.DoesNotExist):
            return Response(
                ResponseData.error("Invalid language code"),
            )