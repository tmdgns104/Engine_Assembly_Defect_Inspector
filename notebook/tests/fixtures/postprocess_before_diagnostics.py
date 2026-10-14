"""CPU raw Detect decode/NMS. Numeric and tie parity still require artifact testing."""
import numpy as np

from src.contracts import BoundingBox, Detection, DetectorError
from src.recipe.package import PackageError, validate_output_contract


def postprocess(outputs, contract, names, confidence, nms_iou, transform, *, diagnostics=None, candidate_trace=False):
    """Validate named BCN output, then class-aware NMS before inverse letterbox.

    Ties use descending score, ascending class ID, then raw index. Geometry/NMS
    use float64 CPU intermediates; this is deterministic policy, not GPU bit parity.
    Static8400 is below the reference max_nms30000, so no hidden pre-NMS truncation.
    """
    try:
        validate_output_contract(contract, len(names))
    except PackageError as error:
        raise DetectorError("OUTPUT_CONTRACT_MISMATCH: declaration") from error
    tensor = contract["tensor_shape_contract"]
    if not isinstance(outputs, dict) or set(outputs) != {tensor["name"]}:
        raise DetectorError("OUTPUT_CONTRACT_MISMATCH: output names")
    value = outputs[tensor["name"]]
    if (not isinstance(value, np.ndarray) or list(value.shape) != tensor["shape"]
            or value.dtype != np.dtype(tensor["dtype"]) or not np.isfinite(value).all()):
        raise DetectorError("OUTPUT_CONTRACT_MISMATCH: shape/dtype/nonfinite")
    scores = value[0, 4:, :].T
    if ((scores < 0) | (scores > 1)).any():
        raise DetectorError("OUTPUT_CONTRACT_MISMATCH: scores must be probabilities")
    classes = scores.argmax(axis=1)
    best = scores[np.arange(len(scores)), classes]
    # Like a tensor scalar comparison, round the threshold to the declared dtype.
    eligible = np.flatnonzero(best > np.asarray(confidence, dtype=best.dtype))
    boxes = value[0, :4, eligible].astype(np.float64)
    if (boxes[:, 2:] <= 0).any():
        raise DetectorError("OUTPUT_CONTRACT_MISMATCH: nonpositive selected width/height")
    xyxy = np.column_stack((boxes[:, :2] - boxes[:, 2:] / 2,
                            boxes[:, :2] + boxes[:, 2:] / 2))
    order = sorted(range(len(eligible)), key=lambda i: (
        -float(best[eligible[i]]), int(classes[eligible[i]]), int(eligible[i])))
    kept = []
    suppressed = []
    while order and len(kept) < 300:
        index = order.pop(0)
        kept.append(index)
        if not order:
            break
        rest = np.asarray(order)
        lower = np.maximum(xyxy[index, :2], xyxy[rest, :2])
        upper = np.minimum(xyxy[index, 2:], xyxy[rest, 2:])
        intersection = np.maximum(upper - lower, 0).prod(axis=1)
        area = np.prod(xyxy[index, 2:] - xyxy[index, :2])
        other_area = (xyxy[rest, 2:] - xyxy[rest, :2]).prod(axis=1)
        overlap = intersection / (area + other_area - intersection)
        same_class = classes[eligible[rest]] == classes[eligible[index]]
        if candidate_trace:
            suppressed.extend(eligible[rest[same_class & (overlap > nms_iou)]].tolist())
        order = rest[~(same_class & (overlap > nms_iou))].tolist()
    height, width = transform.original_shape
    left, top, _, _ = transform.padding
    detections = []
    for index in kept:
        box = (xyxy[index] - np.array([left, top, left, top])) / transform.gain
        box = np.clip(box, [0, 0, 0, 0], [width, height, width, height])
        if not np.isfinite(box).all() or box[0] >= box[2] or box[1] >= box[3]:
            raise DetectorError("OUTPUT_CONTRACT_MISMATCH: degenerate restored box")
        raw_index = eligible[index]
        class_id = int(classes[raw_index])
        detections.append(Detection(class_id, names[class_id], float(best[raw_index]),
                                    BoundingBox(*(float(v) for v in box))))
    if diagnostics is not None:
        if candidate_trace:
            diagnostics.update(eligible_raw_indices=eligible.tolist(),kept_raw_indices=eligible[kept].tolist(),
                               nms_suppressed_raw_indices=suppressed,max_det_discarded_raw_indices=eligible[order].tolist(),
                               raw_output_saved_separately=True)
        diagnostics.update(raw_candidate_count=len(best),pre_nms_eligible_count=len(eligible),
            post_nms_count=len(detections),detector_confidence_threshold=confidence,
            detector_confidence_comparison='>',nms_iou_threshold=nms_iou,
            raw_max_confidence=float(best.max()) if len(best) else None,
            original_shape=list(transform.original_shape),letterbox_gain=transform.gain,
            letterbox_padding=list(transform.padding))
    return tuple(detections)
