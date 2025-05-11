# your_app/views.py

import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.contenttypes.models import ContentType
from rest_framework.decorators import api_view,parser_classes
from appointments.models import AppointmentBookingModel
from interest_requests.models import LandlordInterestRequestModel, TenantInterestRequestModel
from landlord.models import LandlordRoomWiseBedModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.authentication import EnhancedJWTValidation
from rest_framework.permissions import IsAuthenticated

def get_active_tenants_sync(bed_id):
    """
    This function gathers all active tenants for a given bed (by bed_id)
    and computes a personality matching percentage based on the landlord's preferences.
    """
    result = []
    try:
        bed = LandlordRoomWiseBedModel.objects.get(id=bed_id)
    except LandlordRoomWiseBedModel.DoesNotExist:
        return result

    # Fetch all active tenants.
    tenants = list(TenantDetailsModel.objects.filter(is_active=True, is_deleted=False))

    for tenant in tenants:
        # ----- Existing interest request logic -----
        tenant_req = TenantInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()
        if not tenant_req:
            tenant_req = TenantInterestRequestModel.objects.filter(
                tenant=tenant,
                bed=bed,
                is_deleted=False,
                is_active=False,
                status="closed"
            ).first()
        landlord_req = LandlordInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()
        if not landlord_req:
            landlord_req = LandlordInterestRequestModel.objects.filter(
                tenant=tenant,
                bed=bed,
                is_deleted=False,
                is_active=False,
                status="closed"
            ).first()

        if tenant_req:
            interest_status = tenant_req.status
            message = tenant_req.landlord_message
            interest_shown_by = "tenant"
            request_closed_by = getattr(tenant_req, "request_closed_by", "")
        elif landlord_req:
            interest_status = landlord_req.status
            message = landlord_req.tenant_message
            interest_shown_by = "landlord"
            request_closed_by = getattr(landlord_req, "request_closed_by", "")
        else:
            interest_status = ""
            message = ""
            interest_shown_by = ""
            request_closed_by = ""

        appointment_details = None
        if interest_status.lower() == "accepted":
            appointment = AppointmentBookingModel.objects.filter(
                tenant=tenant,
                landlord=bed.room.property.landlord,
                bed=bed,
                is_deleted=False
            ).first()
            if appointment:
                appointment_details = {
                    "appointment_id": appointment.id,
                    "start_time": appointment.time_slot.start_time.strftime('%H:%M'),
                    "end_time": appointment.time_slot.end_time.strftime('%H:%M'),
                    "status": appointment.status,
                }
        # ----- End of existing logic -----
        # Define the personality fields to be matched.
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]
        max_marks_per_question = 10
        # Pre-fetch the landlord answers attached to this bed.
        landlord_answers_qs = list(bed.tenant_preference_answers.all())

        # --- Begin personality matching logic ---
        total_score = 0
        breakdown = {}  # Breakdown of score per personality field

        try:
            tenant_personality = TenantPersonalityDetailsModel.objects.get(
                tenant=tenant, is_active=True, is_deleted=False
            )
        except TenantPersonalityDetailsModel.DoesNotExist:
            tenant_personality = None

        landlord_answered_questions = 0
        for field in personality_fields:
            field_score = 0  # default score for this field is 0
            tenant_answer = None

            if tenant_personality:
                tenant_answer = getattr(tenant_personality, field + '_id', None)

            print(f'tenant_first_name {tenant.first_name}')
            print(f'tenant_answer {tenant_answer}')
            # Determine the model for this field via the TenantPersonalityDetailsModel meta.
            # If tenant selected Student as occupation
            try:
                field_model = TenantPersonalityDetailsModel._meta.get_field(field).remote_field.model
            except Exception:
                field_model = None

            # Get the ContentType for the field model (if available).
            field_ct = ContentType.objects.get_for_model(field_model) if field_model else None

            # Filter landlord answers for this field based on the question's content type.
            landlord_answers_for_field = [
                la for la in landlord_answers_qs if la.question.content_type == field_ct
            ]

            if not tenant_answer:
                field_score = 0
            else:
                if not landlord_answers_for_field:
                    # If landlord did not answer anything in this question then no score given for that
                    field_score = 0
                else:
                    landlord_answered_questions += 1
                    sorted_answers = sorted(
                        landlord_answers_for_field,
                        key=lambda la: la.preference if la.preference is not None else 0,
                    )
                    matched_index = None
                    # landlord selected_option - 3,5,7 (1,2,3)
                    # tenant option - 5
                    # preference - 2
                    # priority_order = 3,1,4
                    # sorted_answers = [1,2,3]
                    print(f'sorted_answers {sorted_answers}')
                    for idx, la in enumerate(sorted_answers):
                        print(f'la.object_id {la.object_id}')
                        print(f'idx {idx}')
                        if la.object_id == tenant_answer:
                            matched_index = idx + 1
                            break
                    if matched_index is not None:
                        landlord_selected_option = len(sorted_answers)
                        # landlord_selected_option = 3
                        # matched_index = 2
                        # total_options = 6
                        # 5 / 10
                        print(f'landlord_selected_option {landlord_selected_option}')
                        print(f'matched_index {matched_index}')
                        field_score = ((landlord_selected_option - matched_index + 1) / landlord_selected_option) * max_marks_per_question
                    else:
                        field_score = 0

            print(f'field_score {field_score}')
            breakdown[field] = round(field_score, 2)
            total_score += field_score

        total_possible = len(personality_fields) * max_marks_per_question
        personality_match_percentage = (total_score / total_possible) * 100 if total_possible else 0
        personality_match_percentage = round(personality_match_percentage, 2)
        # --- End personality matching logic ---

        tenant_data = {
            "id": tenant.id,
            "first_name": tenant.first_name,
            "last_name": tenant.last_name,
            "date_of_birth": str(tenant.date_of_birth) if tenant.date_of_birth else "",
            "interest_status": interest_status,
            "message": message,
            "bed_id": bed_id,
            "request_closed_by": request_closed_by,
            "is_initiated_by_landlord": True if interest_shown_by == "landlord" else False,
            "personality_breakdown": breakdown,
            "personality_match_percentage": personality_match_percentage,
            "landlord_answers_qs" : landlord_answers_for_field
        }

        if appointment_details:
            tenant_data["appointment_details"] = appointment_details

        result.append(tenant_data)
    return result



@api_view(["POST"])
@authentication_classes([EnhancedJWTValidation, SessionAuthentication])
@permission_classes([IsAuthenticated])
def get_active_tenants_view(request):
    """
    Expects a POST with JSON body containing {"bed_id": <id>}.
    Returns a JSON response with the matching tenants and their personality scores.
    """
    try:
        data = json.loads(request.body)
        bed_id = data.get('bed_id')
        if not bed_id:
            return JsonResponse({"error": "bed_id parameter is required."}, status=400)
        result = get_active_tenants_sync(bed_id)
        return JsonResponse({"result": result})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
