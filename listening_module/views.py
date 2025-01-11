import ast
from rest_framework import status

from listening_module.models import ListeningSentencesDataModel

from rest_framework.views import APIView
from response import Response as ResponseData
from users.models import UserListeningSentenceProgressModel
from rest_framework.response import Response

# Create your views here.
class GetListeningDataByTopicView(APIView):
    def post(self, request):
        try:
            # Extract data from the request
            topic_id = request.data.get("topic_id")
            user_id = request.data.get("user_id")
            
            # Validate input
            if not topic_id or not user_id:
                return Response(
                    ResponseData.error("topic_id and user_id are required."),
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Fetch all sentences for the topic
            sentences = ListeningSentencesDataModel.objects.filter(
                topic_id=topic_id,
                is_active=True,
                is_deleted=False
            ).prefetch_related('base_language', 'learning_language')
            
            if not sentences.exists():
                return Response(
                    ResponseData.error("No sentences found for the given topic or they are inactive/deleted."),
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Fetch user progress data for these sentences
            user_progress = UserListeningSentenceProgressModel.objects.filter(
                user_id=user_id,
                sentence_data__in=sentences
            )
            
            # Organize user progress data by sentence ID
            user_progress_dict = {progress.sentence_data_id: progress.is_listened for progress in user_progress}
            
            # Prepare response data
            listened_sentences = []
            not_listened_sentences = []
            
            for sentence in sentences:
                is_listened = user_progress_dict.get(sentence.id, False)
                sentence_data = {
                    "id": sentence.id,
                    "sentence": " | ".join([f"{key}: {value}" for key, value in ast.literal_eval(sentence.sentence).items()]),
                    #"sentence": ast.literal_eval(sentence.sentence),
                    "base_language": {
                        "name": sentence.base_language.name,
                        "translation_code": sentence.base_language.translation_code,
                    },
                    "learning_language": {
                        "name": sentence.learning_language.name,
                        "translation_code": sentence.learning_language.translation_code,
                    },
                    "is_listened": is_listened,
                }
                if is_listened:
                    listened_sentences.append(sentence_data)
                else:
                    not_listened_sentences.append(sentence_data)
            
            # Combine both listened and not listened sentences
            combined_sentences = listened_sentences + not_listened_sentences
            
            return Response(
                ResponseData.success(data=combined_sentences, message="Sentences fetched successfully."),
                status=status.HTTP_200_OK
            )
        
        except Exception as e:
            return Response(
                ResponseData.error(error=str(e))
                )