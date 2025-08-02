# your_app/management/commands/test_get_active_tenants.py

from django.core.management.base import BaseCommand
from asgiref.sync import async_to_sync, sync_to_async
from django.contrib.contenttypes.models import ContentType

from appointments.models import AppointmentBookingModel
from interest_requests.models import InterestRequestStatusModel, LandlordInterestRequestModel, TenantInterestRequestModel
from landlord.models import LandlordRoomWiseBedModel
from tenant.models import TenantDetailsModel, TenantPersonalityDetailsModel


class Command(BaseCommand):
    help = "Test get_active_tenants function for a given bed id."

    def add_arguments(self, parser):
        parser.add_argument(
            'bed_id',
            type=int,
            help='ID of the LandlordRoomWiseBedModel to test against.'
        )
    @sync_to_async
    # Helper functions to wrap ORM calls
    def get_tenant_req(self, tenant, bed):
        return TenantInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()

    @sync_to_async
    def get_tenant_req_closed(self, tenant, bed):
        status = InterestRequestStatusModel.objects.get(code='closed')
        return TenantInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=False,
            status=status
        ).first()

    @sync_to_async
    def get_landlord_req(self, tenant, bed):
        return LandlordInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=True
        ).first()

    @sync_to_async
    def get_landlord_req_closed(self, tenant, bed):
        return LandlordInterestRequestModel.objects.filter(
            tenant=tenant,
            bed=bed,
            is_deleted=False,
            is_active=False,
            status="closed"
        ).first()

    @sync_to_async
    def get_appointment(self, tenant, bed, landlord):
        return AppointmentBookingModel.objects.filter(
            tenant=tenant,
            landlord=landlord,
            bed=bed,
            is_deleted=False
        ).first()

    async def get_active_tenants(self, bed_id):
        result = []
        try:
            bed = await sync_to_async(LandlordRoomWiseBedModel.objects.get)(id=bed_id)
        except LandlordRoomWiseBedModel.DoesNotExist:
            return result

        # Fetch all active tenants.
        tenants = await sync_to_async(list)(
            TenantDetailsModel.objects.filter(is_active=True, is_deleted=False)
        )

        # Define the personality fields we want to match.
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]
        max_marks_per_question = 10

        # Pre-fetch the landlord answers attached to this bed.
        landlord_answers_qs = await sync_to_async(list)(bed.tenant_preference_answers.all())

        for tenant in tenants:
            # ----- Existing interest request logic -----
            tenant_req = await sync_to_async(self.get_tenant_req)(tenant, bed)
            if not tenant_req:
                tenant_req = await sync_to_async(self.get_tenant_req_closed)(tenant, bed)
            landlord_req = await sync_to_async(self.get_landlord_req)(tenant, bed)
            if not landlord_req:
                landlord_req = await sync_to_async(self.get_landlord_req_closed)(tenant, bed)

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
                appointment = await sync_to_async(self.get_appointment)(
                    tenant, bed, bed.room.property.landlord
                )
                if appointment:
                    appointment_details = {
                        "appointment_id": appointment.id,
                        "start_time": appointment.time_slot.start_time.strftime('%H:%M'),
                        "end_time": appointment.time_slot.end_time.strftime('%H:%M'),
                        "status": appointment.status,
                    }
            # ----- End of existing logic -----

            # --- Begin personality matching logic ---
            total_score = 0
            breakdown = {}  # Breakdown of score per personality field

            try:
                tenant_personality = await sync_to_async(
                    TenantPersonalityDetailsModel.objects.get
                )(tenant=tenant, is_active=True, is_deleted=False)
            except TenantPersonalityDetailsModel.DoesNotExist:
                tenant_personality = None

            landlord_answered_questions = 0
            for field in personality_fields:
                field_score = 0  # default score for this field is 0
                tenant_answer = None

                if tenant_personality:
                    tenant_answer = getattr(tenant_personality, field, None)

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
                            reverse=True
                        )
                        matched_index = None
                        # landlord selected_option - 3,5,7 (1,2,3)
                        # tenant option - 5
                        # preference - 2
                        for idx, la in enumerate(sorted_answers):
                            if la.selected_option == tenant_answer:
                                matched_index = idx
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

                breakdown[field] = round(field_score, 2)
                total_score += field_score

            total_possible = len(landlord_answered_questions) * max_marks_per_question
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
            }

            if appointment_details:
                tenant_data["appointment_details"] = appointment_details

            result.append(tenant_data)

        return result

    def handle(self, *args, **options):
        bed_id = options['bed_id']
        self.stdout.write(f"Testing get_active_tenants for bed id: {bed_id}")

        result = async_to_sync(self.get_active_tenants)(bed_id)
        self.stdout.write(self.style.SUCCESS("Result:"))
        self.stdout.write(str(result))
