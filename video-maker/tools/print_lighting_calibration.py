"""Measure existing print illumination using registered non-eye skin samples.

Measurements propose lighting gains only; they never approve video quality.
GPL-3.0-only.
"""
import cv2
import numpy as np


def estimate_skin_gain(reference, source, registration, reference_eyes, mask):
    eyes = np.asarray(reference_eyes, dtype=np.float64).reshape(2, 2)
    distance = float(np.linalg.norm(eyes[1] - eyes[0]))
    matrix = np.asarray(registration, dtype=np.float64)
    if (reference.ndim != 3 or reference.shape[2] != 4 or source.ndim != 3
            or source.shape[2] != 3 or mask.shape != reference.shape[:2]
            or matrix.shape != (2, 3) or not np.isfinite(matrix).all() or distance < 2):
        raise ValueError('Bound RGBA reference, BGR frame, mask and finite landmarks required')
    b, g, r, alpha = cv2.split(reference.astype(np.float32))
    yy, xx = np.mgrid[:reference.shape[0], :reference.shape[1]]
    skin = ((alpha > 250) & (mask > .2) & (r > 140) & (g > 110) & (b > 60)
        & (r - g > 2) & (g - b > 2) & (r - b > 8)
        & (yy > eyes[:, 1].mean() - distance * .2)
        & (yy < eyes[:, 1].mean() + distance * .8)
        & (xx > eyes[:, 0].min() - distance * .45)
        & (xx < eyes[:, 0].max() + distance * .45))
    # Exclude the iris, spectacle rim and lash regions; their generated shape is
    # precisely what restoration repairs and is unsuitable as a light meter.
    for x, y in eyes:
        skin &= ((xx - x) ** 2 + (yy - y) ** 2 > (distance * .27) ** 2)
    sy, sx = np.nonzero(skin)
    points = np.column_stack((sx, sy, np.ones(len(sx)))) @ matrix.T
    inside = ((points[:, 0] >= 1) & (points[:, 0] < source.shape[1] - 1)
        & (points[:, 1] >= 1) & (points[:, 1] < source.shape[0] - 1))
    points, sx, sy = points[inside], sx[inside], sy[inside]
    if len(sx) < 30:
        raise ValueError('Insufficient visible non-eye skin samples; manual calibration required')
    # OpenCV remap requires each destination dimension below SHRT_MAX. A large
    # plush master can provide far more than32767 valid skin pixels.
    source_float = source.astype(np.float32)
    sampled = np.concatenate([cv2.remap(source_float,
        batch[:, 0].astype(np.float32)[None], batch[:, 1].astype(np.float32)[None],
        cv2.INTER_LINEAR)[0] for start in range(0, len(points), 16000)
        for batch in (points[start:start + 16000],)], axis=0)
    original = reference[sy, sx, :3].astype(np.float32)
    # Median channel ratios resist dark outline errors without importing their
    # shape into the reference. A single fixed gain avoids frame-to-frame pumping.
    ratios = sampled / np.maximum(original, 1)
    gain = np.median(ratios, axis=0)[::-1]
    if not np.isfinite(gain).all() or np.any(gain < .15) or np.any(gain > 1.5):
        raise ValueError('Implausible measured illumination; manual calibration required')
    return {'proposedGainRgb': gain.tolist(), 'samplePixels': len(sx),
        'sourceMedianRgb': np.median(sampled, axis=0)[::-1].tolist(),
        'referenceMedianRgb': np.median(original, axis=0)[::-1].tolist(),
        'scope': 'Frame-zero registered skin illumination estimate, not a semantic approval.'}
