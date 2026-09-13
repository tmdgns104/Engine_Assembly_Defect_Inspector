"""Pure multi-slot/count decision logic, with exclusive detection assignment and explicit coverage."""

from src.decision.bench import area, intersection, iou, xyxy


def pixel_box(normalized, width, height):
    return [normalized[0] * width, normalized[1] * height, normalized[2] * width, normalized[3] * height]


def normalized_box(pixels, width, height):
    return [pixels[0] / width, pixels[1] / height, pixels[2] / width, pixels[3] / height]


def assign_slots(detections, recipe, width, height, regions=None):
    """An ambiguous detection fills no slot. No single observation counts twice."""
    slots = recipe["slots"]
    regions = regions or {slot["id"]: slot["region"] for slot in slots}
    assignments = {slot["id"]: [] for slot in slots}
    uncertain = set()
    for index, detection in enumerate(detections):
        candidate_slots = []
        bbox = xyxy(detection)
        for slot in slots:
            if detection["class_name"] not in slot["allowed_classes"]:
                continue
            region = pixel_box(regions[slot["id"]], width, height)
            if intersection(bbox, region) / max(area(bbox), 1e-9) >= recipe["slot_overlap"]:
                candidate_slots.append(slot["id"])
        if len(candidate_slots) != 1 or detection["confidence"] < recipe["presence_confidence"]:
            uncertain.update(candidate_slots)
            if not candidate_slots:
                uncertain.update(slot["id"] for slot in slots if detection["class_name"] in slot["allowed_classes"])
            continue
        assignments[candidate_slots[0]].append(index)
    return assignments, uncertain


def assess(observations, recipe, view_assessment, calibration=None):
    """No device/files/ground truth access. A visibility declaration is evidence, not automation."""
    defects, unassessed, states = [], [], {}
    def result(decision, reason):
        return {"decision": decision, "reason": reason, "defects": defects, "unassessed": unassessed,
                "slot_states": states, "coverage": view_assessment}
    if not recipe.get("slots") or recipe.get("rule") != "presence_count":
        return result("ERROR", "비어 있거나 지원하지 않는 검사 규칙")
    if view_assessment.get("system_error"):
        return result("ERROR", view_assessment["system_error"])
    if view_assessment.get("product_identity") == "confirmed_wrong":
        defects.append({"code": "D11", "rule": "product_identity", "slot": None})
        return result("FAIL", "확인된 제품 불일치")
    if view_assessment.get("no_product_confirmed"):
        return result("ERROR", "NO_PRODUCT")
    if len(observations) != recipe["observation_count"]:
        return result("ERROR", "관측 수 불일치")
    if not observations or len({x["frame_id"] for x in observations}) != len(observations):
        return result("ERROR", "중복 또는 빈 프레임")
    points = [x["freshness"]["source_pts_ns"] for x in observations]
    if any(b <= a for a, b in zip(points, points[1:])):
        return result("ERROR", "프레임 순서 오류")
    regions = calibration.get("slots") if calibration else None
    align_ok = view_assessment.get("alignment_confirmed") is True
    if recipe.get('alignment_mode') == 'human_fixed_reference':
        align_ok = align_ok and bool(calibration and calibration.get('confirmed') is True)
    identity_ok = view_assessment.get("product_identity") == "human_confirmed"
    for slot in recipe["slots"]:
        slot_id = slot["id"]
        per_frame = []
        for observation in observations:
            visible = view_assessment.get("visible_slots", {}).get(slot_id) is True
            quality = observation["quality"]["valid"]
            reference_ok = True
            if recipe["reference_class"]:
                references = [d for d in observation["detections"] if d["class_name"] == recipe["reference_class"]]
                reference_ok = len(references) == 1 and references[0]["confidence"] >= recipe["reference_confidence"]
                if calibration and reference_ok:
                    reference_ok = iou(xyxy(references[0]), pixel_box(calibration["reference_box"], observation["width"], observation["height"])) >= recipe["reference_iou"]
            if not visible or not quality or not align_ok or not reference_ok or not identity_ok:
                per_frame.append("UNOBSERVABLE")
                continue
            assignments, ambiguous = assign_slots(observation["detections"], recipe, observation["width"], observation["height"], regions)
            count = len(assignments[slot_id])
            if slot_id in ambiguous or count > slot["expected_count"]:
                per_frame.append("UNCERTAIN")
            elif count == slot["expected_count"]:
                per_frame.append("PRESENT")
            else:
                per_frame.append("ABSENT_CONFIRMED")
        state = per_frame[0] if len(set(per_frame)) == 1 else "UNCERTAIN"
        states[slot_id] = state
        if state == "ABSENT_CONFIRMED":
            defects.append({"code": "MISSING_REQUIRED_OBJECT", "slot": slot_id, "rule": "presence_count",
                            "display": slot["display"], "expected_count": slot["expected_count"],
                            "expected_region": (regions or {}).get(slot_id, slot["region"])})
        elif state != "PRESENT":
            unassessed.append(slot_id)
    if defects:
        return result("FAIL", "필수 수량 부족: " + ", ".join(item["display"] for item in defects))
    if unassessed:
        return result("REVIEW", "관찰·정렬·식별 또는 검출이 불확실한 자리: " + ", ".join(unassessed))
    return result("PASS", "모든 필수 자리와 수량 확인")
