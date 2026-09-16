"""Propose a new reference from source-image observations, never from old slots.

Only class-unique slot mappings can be registered automatically. The operator
still owns physical placement, visibility and final approval of the proposal.
"""

import hashlib
import json
import math

from src.decision.slots import assign_slots, normalized_box
from src.decision.bench import iou, xyxy


class ReferenceError(ValueError):
    def __init__(self, code, reason, slots=()):
        super().__init__(reason)
        self.code = code
        self.slots = list(slots)


def station_fingerprint(station):
    encoded = json.dumps(station, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def reference_proposal(observations, package):
    recipe = package.recipe
    slots = recipe['slots']
    slot_ids = [slot['id'] for slot in slots]
    if len(observations) != recipe['observation_count'] or not observations:
        raise ReferenceError('REFERENCE_FRAMES', '기준 촬영의 연속 관측 수가 부족합니다.', slot_ids)
    frames = [item['frame_id'] for item in observations]
    points = [item['freshness']['source_pts_ns'] for item in observations]
    if len(set(frames)) != len(frames) or any(b <= a for a, b in zip(points, points[1:])):
        raise ReferenceError('REFERENCE_FRAMES', '중복되거나 순서가 잘못된 기준 사진입니다.', slot_ids)
    width, height = observations[-1]['width'], observations[-1]['height']
    assignments_by_frame = []
    references = []
    for number, observation in enumerate(observations, 1):
        if (observation['width'], observation['height']) != (width, height) or width <= 0 or height <= 0:
            raise ReferenceError('REFERENCE_DIMENSIONS', '기준 사진의 원본 크기가 일치하지 않습니다.', slot_ids)
        if not observation['quality']['valid']:
            raise ReferenceError('REFERENCE_QUALITY', f'{number}번째 사진의 선명도 또는 밝기가 기준에 못 미칩니다.', slot_ids)
        assigned = {slot['id']: [] for slot in slots}
        for detection in observation['detections']:
            box = xyxy(detection)
            confidence = detection['confidence']
            if not all(math.isfinite(v) for v in [*box, confidence]) or not (
                0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height
            ):
                raise ReferenceError('REFERENCE_COORDINATES', '검출 원본 좌표가 유효하지 않습니다.', slot_ids)
            matches = [slot for slot in slots if detection['class_name'] in slot['allowed_classes']]
            if len(matches) > 1:
                ids = [slot['id'] for slot in matches]
                raise ReferenceError('REFERENCE_SLOT_MAPPING',
                    f"{', '.join(ids)} 자리: 같은 클래스가 여러 자리에 대응합니다. 사용자 자리 지정이 필요합니다.", ids)
            if matches:
                slot = matches[0]
                if confidence < recipe['presence_confidence']:
                    raise ReferenceError('REFERENCE_CONFIDENCE',
                        f"{slot['display']}: 검출 신뢰도가 기준보다 낮습니다 ({confidence:.3f}).", [slot['id']])
                assigned[slot['id']].append(box)
        for slot in slots:
            count = len(assigned[slot['id']])
            if count != slot['expected_count']:
                raise ReferenceError('REFERENCE_COUNT',
                    f"{slot['display']}: {number}번째 사진에서 {count}개 검출, 정상 기준에는 {slot['expected_count']}개가 필요합니다. 정상 제품을 준비해 주세요.", [slot['id']])
        assignments_by_frame.append(assigned)
        if recipe['reference_class']:
            found = [d for d in observation['detections'] if d['class_name'] == recipe['reference_class']]
            if len(found) != 1 or found[0]['confidence'] < recipe['reference_confidence']:
                raise ReferenceError('REFERENCE_OBJECT', '기준 물체의 검출 수량 또는 신뢰도가 불확실합니다.', slot_ids)
            references.append(xyxy(found[0]))

    # A slot may require several objects; its region encloses that slot's objects.
    # Shared classes across slots were rejected above, so none can be counted twice.
    regions = {}
    for slot in slots:
        boxes = assignments_by_frame[-1][slot['id']]
        bounds = [min(b[0] for b in boxes), min(b[1] for b in boxes),
                  max(b[2] for b in boxes), max(b[3] for b in boxes)]
        regions[slot['id']] = normalized_box(bounds, width, height)
    for number, observation in enumerate(observations, 1):
        assigned, uncertain = assign_slots(observation['detections'], recipe, width, height, regions)
        unstable = [s['id'] for s in slots if s['id'] in uncertain or len(assigned[s['id']]) != s['expected_count']]
        if unstable:
            raise ReferenceError('REFERENCE_UNSTABLE',
                f"{', '.join(unstable)} 자리: {number}번째 사진과 후보 위치가 일치하지 않습니다. 물체와 카메라를 고정해 주세요.", unstable)
    if references and any(iou(box, references[-1]) < recipe['reference_iou'] for box in references):
        raise ReferenceError('REFERENCE_UNSTABLE', '연속 사진에서 기준 물체가 움직였습니다. 다시 촬영해 주세요.', slot_ids)
    return {'slots': regions, 'reference_box': normalized_box(references[-1], width, height) if references else None,
            'coordinate_space': 'normalized_image', 'source_dimensions': {'width': width, 'height': height},
            'source_frame_ids': frames, 'product_id': package.manifest['product_id'],
            'manifest_sha256': package.manifest_hash,
            'capture_sha256': package.manifest['files']['capture']['sha256'],
            'recipe_sha256': package.manifest['files']['recipe']['sha256'], 'confirmed': False}
