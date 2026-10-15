"""Saved-image registration coordinates. No camera, PLC or runtime side effects."""
from pathlib import Path
import hashlib
import json

import cv2
import numpy as np


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2,
        default=lambda v: v.tolist() if isinstance(v, np.ndarray) else v.item()) + "\n", encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def image(path):
    im = cv2.imdecode(np.frombuffer(Path(path).read_bytes(), np.uint8), cv2.IMREAD_COLOR)
    if im is None:
        raise ValueError(f"Cannot decode {path}")
    return im


def transform(points, matrix):
    points = np.asarray(points, np.float64).reshape(-1, 2)
    homogeneous = np.c_[points, np.ones(len(points))] @ np.asarray(matrix).T
    return homogeneous[:, :2] / homogeneous[:, 2:] if homogeneous.shape[1] == 3 else homogeneous


def hom(matrix):
    return np.vstack([matrix, [0., 0., 1.]]) if np.asarray(matrix).shape == (2, 3) else np.asarray(matrix)


def quarter_turn(im, count):
    """Return clockwise-rotated pixels and exact original->rotated pixel map."""
    h, w = im.shape[:2]
    mats = [np.eye(3), np.array([[0,-1,h-1],[1,0,0],[0,0,1.]]),
            np.array([[-1,0,w-1],[0,-1,h-1],[0,0,1.]]),
            np.array([[0,1,0],[-1,0,w-1],[0,0,1.]])]
    return np.ascontiguousarray(np.rot90(im, -count)), mats[count % 4]


def body_regions(shape, profile):
    """Physical surfaces only; aperture interiors are explicitly excluded."""
    labels = np.zeros(shape[:2], np.uint8)
    for n, region in enumerate(profile["body_regions"], 1):
        mask = np.zeros_like(labels)
        if "polygon" in region:
            cv2.fillPoly(mask, [np.asarray(region["polygon"], np.int32)], 1)
        else:
            x, y, outer, inner = region["annulus"]
            cv2.circle(mask, (x,y), outer, 1, -1)
            cv2.circle(mask, (x,y), inner, 0, -1)
        labels[mask != 0] = n
    return labels


def regions_at(points, labels):
    xy = np.rint(points).astype(int)
    valid = (xy[:,0] >= 0) & (xy[:,0] < labels.shape[1]) & (xy[:,1] >= 0) & (xy[:,1] < labels.shape[0])
    result = np.zeros(len(points), int)
    result[valid] = labels[xy[valid,1], xy[valid,0]]
    return result


def fit_body(points0, points1, confidence, labels, count):
    """One global similarity. Preserve support/alternatives, never class scores."""
    region = regions_at(points0, labels)
    keep = np.flatnonzero(region > 0)
    # Coarse-map neighbours are correlated; one highest confidence pair per
    # 8-original-pixel reference cell and target cell, not a count of all pixels.
    used0, used1, unique = set(), set(), []
    for i in sorted(keep, key=lambda j: -confidence[j]):
        cell0 = tuple(np.floor(points0[i] / 8).astype(int))
        cell1 = tuple(np.floor(points1[i] / 8).astype(int))
        if cell0 not in used0 and cell1 not in used1:
            used0.add(cell0); used1.add(cell1); unique.append(i)
    record = dict(matches=len(points0), body_matches=len(keep), unique_matches=len(unique),
                  matrix=None, reason="INSUFFICIENT_BODY_SUPPORT", support=[0]*count,
                  correspondences=[dict(reference=points0[i], current=points1[i], confidence=float(confidence[i]),
                                        region=int(region[i])) for i in keep])
    if len(unique) < 4:
        return record
    p, q = points0[unique], points1[unique]
    cv2.setRNGSeed(22025)
    matrix, _ = cv2.estimateAffinePartial2D(p, q, method=cv2.RANSAC,
        ransacReprojThreshold=3., maxIters=2000, confidence=.999, refineIters=10)
    if matrix is None:
        return record
    residual = np.linalg.norm(transform(p, matrix)-q, axis=1)
    inside = residual <= 3.
    support = [int(np.sum(inside & (region[unique] == r))) for r in range(1,count+1)]
    record.update(matrix=matrix, support=support, median_residual_px=float(np.median(residual[inside])) if inside.any() else None,
                  inlier_unique=int(inside.sum()), residuals_px=residual,
                  reason="BODY_GEOMETRY_CANDIDATE" if sum(s >= 3 for s in support) >= 2 else "INSUFFICIENT_BODY_SUPPORT")
    return record
