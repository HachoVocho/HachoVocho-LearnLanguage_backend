from django.contrib.contenttypes.models import ContentType

def compute_personality_match(
    tenant_persona,
    landlord_answers_qs,
    personality_fields=None,
    max_marks=10
):
    """
    Returns (overall_pct, details_dict) where:
      - overall_pct: float [0.0–100.0]
      - details_dict: dict mapping field → {
          'tenant_choice': {'id','label'} or None,
          'landlord_ranked': [ {'id','label'}, … ],
          'match_pct': float
        }
      inserted in descending order of match_pct.
    """
    if not personality_fields:
        personality_fields = [
            "occupation", "country", "religion", "income_range",
            "smoking_habit", "drinking_habit", "socializing_habit",
            "relationship_status", "food_habit", "pet_lover"
        ]

    total_possible = len(personality_fields) * max_marks
    total_score = 0.0
    raw = {}

    print(f"[DEBUG] Fields: {personality_fields}")
    print(f"[DEBUG] Max marks per question: {max_marks}")

    for field in personality_fields:
        print(f"\n[DEBUG] Processing field: {field}")
        entry = {"tenant_choice": None, "landlord_ranked": [], "match_pct": 0.0}

        # 1) tenant’s choice
        ans_id = getattr(tenant_persona, f"{field}_id", None)
        print(f"[DEBUG]   Tenant answer ID: {ans_id}")

        # 2) resolve the related model for this field
        try:
            field_obj = tenant_persona._meta.get_field(field)
            rel_model = field_obj.remote_field.model
            print(f"[DEBUG]   Related model for '{field}': {rel_model.__name__}")
        except Exception as e:
            print(f"[ERROR]   Could not resolve remote_field for '{field}': {e}")
            raw[field] = entry
            continue

        # 3) get tenant’s chosen option label
        if ans_id:
            try:
                opt = rel_model.objects.get(pk=ans_id)
                label = getattr(opt, "name", str(opt))
                print(f"[DEBUG]   Tenant choice label: {label}")
            except Exception as e:
                label = ""
                print(f"[ERROR]   Could not fetch tenant option for ID {ans_id}: {e}")
            entry["tenant_choice"] = {"id": ans_id, "label": label}

        # 4) collect and sort landlord’s preferences
        ct = ContentType.objects.get_for_model(rel_model)
        las = [la for la in landlord_answers_qs if la.question.content_type_id == ct.id]
        print(f"[DEBUG]   Found {len(las)} landlord answers for '{field}'")
        las_sorted = sorted(las, key=lambda la: la.preference or 0)
        for la in las_sorted:
            oid = la.object_id
            try:
                opt = rel_model.objects.get(pk=oid)
                lbl = getattr(opt, "name", str(opt))
            except Exception as e:
                lbl = ""
                print(f"[ERROR]    Could not fetch landlord option for ID {oid}: {e}")
            entry["landlord_ranked"].append({"id": oid, "label": lbl})
        print(f"[DEBUG]   Ranked landlord options: {entry['landlord_ranked']}")

        # 5) compute match_pct for this field
        if ans_id and entry["landlord_ranked"]:
            idx = next((i for i, o in enumerate(entry["landlord_ranked"]) if o["id"] == ans_id), None)
            if idx is not None:
                raw_score = ((len(entry["landlord_ranked"]) - idx) /
                             len(entry["landlord_ranked"])) * max_marks
                pct = round((raw_score / max_marks) * 100, 2)
                entry["match_pct"] = pct
                total_score += raw_score
                print(f"[DEBUG]   Raw score: {raw_score}, Match %: {pct}")
            else:
                print(f"[WARN]   Tenant answer ID {ans_id} not found in landlord_ranked list")

        raw[field] = entry

    overall_pct = round((total_score / total_possible) * 100, 2) if total_possible else 0.0
    print(f"\n[DEBUG] Total raw score: {total_score}, Overall %: {overall_pct}")

    # 6) sort by match_pct descending
    sorted_items = sorted(raw.items(), key=lambda kv: kv[1]["match_pct"], reverse=True)
    details_dict = {field: info for field, info in sorted_items}
    print(f"[DEBUG] Sorted details order: {details_dict}")

    return overall_pct, details_dict

