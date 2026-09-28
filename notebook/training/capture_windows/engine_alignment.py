"""Human alignment marks in the preview, never measured angles or annotations."""
import math

from .wizard_plan import target_polygon, validate_roi


def validate_alignment(roi, envelope, size):
    """Keep every orientation of the selected rectangle inside the fixed region.

    Work in pixels: normalized x/y have different scales on a wide camera frame.
    The corner radius covers intermediate angles as well as the plan's targets.
    """
    validate_roi(roi)
    validate_roi(envelope)
    width, height = size
    x, y, w, h = roi
    cx, cy = (x+w/2)*width, (y+h/2)*height
    radius = math.hypot(w*width, h*height)/2
    left, top, ew, eh = envelope
    if (cx-radius < left*width or cx+radius > (left+ew)*width
            or cy-radius < top*height or cy+radius > (top+eh)*height):
        raise ValueError('엔진 외곽을 회전하면 노란 고정 영역을 벗어납니다. 고정 영역·회전 중심을 다시 확인하세요.')


def alignment_marks(roi, angle_deg, size):
    """Return a clockwise rectangle, center and top/exhaust marker in pixels."""
    polygon = target_polygon(roi, {'dx': 0, 'dy': 0, 'angle_deg': angle_deg}, size)
    center = tuple(sum(p[i] for p in polygon)/4 for i in (0, 1))
    exhaust = tuple((polygon[0][i]+polygon[1][i])/2 for i in (0, 1))
    # A short chevron on the exhaust end removes the rectangle's 180° ambiguity.
    base = tuple(exhaust[i]*.75+center[i]*.25 for i in (0, 1))
    side = tuple((polygon[1][i]-polygon[0][i])*.13 for i in (0, 1))
    chevron = [tuple(base[i]-side[i] for i in (0, 1)), exhaust,
               tuple(base[i]+side[i] for i in (0, 1))]
    return polygon, center, exhaust, chevron


def draw_alignment(draw, roi, angle_deg, size):
    polygon, center, exhaust, chevron = alignment_marks(roi, angle_deg, size)
    cyan = (35, 235, 255, 245)
    draw.line(polygon+[polygon[0]], fill=cyan, width=4)
    draw.line([center, exhaust], fill=cyan, width=3)
    draw.line(chevron, fill=cyan, width=5)
    cx, cy = center
    draw.line([(cx-10, cy), (cx+10, cy)], fill=cyan, width=3)
    draw.line([(cx, cy-10), (cx, cy+10)], fill=cyan, width=3)
