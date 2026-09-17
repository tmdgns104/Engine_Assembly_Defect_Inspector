"""Config-driven BENCH decisions. Absence requires declared visibility and fresh observations."""


def xyxy(detection):
    box = detection["bounding_box"]
    return [box[key] for key in ("x1", "y1", "x2", "y2")]


def intersection(a, b):
    return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))


def area(box):
    return max(0, box[2] - box[0]) * max(0, box[3] - box[1])


def iou(a, b):
    overlap = intersection(a, b)
    return overlap / max(area(a) + area(b) - overlap, 1e-9)


def calibrate(detections, config):
    """Propose slot boxes from a live NORMAL reference; user must confirm the overlay."""
    refs = [d for d in detections if d["class_name"] == config["reference_class"]
            and d["confidence"] >= config["reference_min_confidence"]]
    if len(refs) != 1:
        raise ValueError("기준 객체 하나가 명확히 보여야 합니다.")
    reference = xyxy(refs[0])
    slots = {}
    for slot in config["slots"]:
        found = [d for d in detections if d["class_name"] == slot["class_name"]
                 and d["confidence"] >= config["presence_confidence"]]
        if len(found) != slot["expected_count"] or len(found) != 1:
            raise ValueError(f"{slot['display']} 기준 검출이 불확실합니다.")
        box = xyxy(found[0])
        if intersection(box, reference) / max(area(box), 1) < .95:
            raise ValueError("기준 부품이 케이스 내부에 있어야 합니다.")
        slots[slot["id"]] = box
    return {"reference_box": reference, "slots": slots, "confirmed": False}


def decide(observations, calibration, config, visibility_confirmed):
    def result(status, reason, states=None):
        return {"status": status, "reason": reason, "slot_states": states or {},
                "visibility_basis": "human_declaration" if visibility_confirmed else "not_confirmed",
                "limitations": config["limitations"]}
    if not visibility_confirmed:
        return result("REVIEW", "열린 케이스·두 자리 가시성·손 제거 확인이 필요합니다.")
    if not calibration or not calibration.get("confirmed"):
        return result("REVIEW", "정상 기준 자리 확인이 필요합니다.")
    if len(observations) != config["frames_per_inspection"]:
        return result("ERROR", "연속 관측 수가 부족합니다.")
    ids = [item["frame_id"] for item in observations]
    pts = [item["freshness"]["source_pts_ns"] for item in observations]
    if len(set(ids)) != len(ids) or any(b <= a for a, b in zip(pts, pts[1:])):
        return result("ERROR", "중복되거나 순서가 잘못된 프레임입니다.")
    states = {slot["id"]: [] for slot in config["slots"]}
    for obs in observations:
        if not obs["quality"]["valid"]:
            return result("REVIEW", "밝기 또는 선명도가 검사 기준을 벗어났습니다.")
        detections = obs["detections"]
        reference = [d for d in detections if d["class_name"] == config["reference_class"]]
        if (len(reference) != 1 or reference[0]["confidence"] < config["reference_min_confidence"]
                or iou(xyxy(reference[0]), calibration["reference_box"]) < config["min_reference_iou"]):
            return result("REVIEW", "기준 객체가 없거나 구도가 달라 검사 자리를 확인할 수 없습니다.")
        for slot in config["slots"]:
            region = calibration["slots"][slot["id"]]
            found = [d for d in detections if d["class_name"] == slot["class_name"]]
            if not found:
                states[slot["id"]].append("ABSENT_CONFIRMED")
            elif (len(found) == slot["expected_count"] == 1
                  and found[0]["confidence"] >= config["presence_confidence"]
                  and intersection(xyxy(found[0]), region) / max(area(xyxy(found[0])), 1) >= config["min_box_slot_overlap"]):
                states[slot["id"]].append("PRESENT")
            else:
                states[slot["id"]].append("UNCERTAIN")
    final = {key: values[0] if len(set(values)) == 1 else "UNCERTAIN" for key, values in states.items()}
    missing = [slot["display"] for slot in config["slots"] if final[slot["id"]] == "ABSENT_CONFIRMED"]
    if missing:
        return result("FAIL", " / ".join(missing) + " 누락 (사용자 가시성 확인 및 서로 다른 연속 프레임 기준)", final)
    if "UNCERTAIN" in final.values():
        return result("REVIEW", "부품 점수·자리 또는 연속 관측이 불확실합니다.", final)
    return result("PASS", "모든 필수 부품이 확인된 검사 자리에 있습니다.", final)
