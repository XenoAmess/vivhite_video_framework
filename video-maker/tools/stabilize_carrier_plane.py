"""Project a complete original print using its physical carrier, never its face.

Source artwork is an existing imagegen reference. This is video compositing;
it does not invent image content or approve the resulting sequence. GPL-3.0-only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def polygon_mask(shape, polygons):
    mask = np.zeros(shape[:2], np.uint8)
    for points in polygons:
        points = np.asarray(points, dtype=np.float32)
        if points.ndim != 2 or points.shape[1] != 2 or len(points) < 3 or not np.isfinite(points).all():
            raise ValueError('A mask needs a finite polygon')
        if (points[:, 0].min() < 0 or points[:, 1].min() < 0
                or points[:, 0].max() >= shape[1] or points[:, 1].max() >= shape[0]):
            raise ValueError('Mask escaped the native frame')
        cv2.fillPoly(mask, [np.round(points).astype(np.int32)], 255)
    return mask


class CarrierTracker:
    """Track frame-zero material features, excluding the entire animated graphic."""
    def __init__(self, first, polygons, excluded_polygons=(), max_shift=40, max_scale_change=.12):
        self.first_gray = cv2.cvtColor(first, cv2.COLOR_BGR2GRAY)
        mask = polygon_mask(first.shape, polygons)
        if excluded_polygons:
            mask[polygon_mask(first.shape, excluded_polygons) > 0] = 0
        self.points = cv2.goodFeaturesToTrack(self.first_gray, 500, .005, 5, mask=mask)
        if self.points is None or len(self.points) < 10:
            raise ValueError('Carrier has insufficient independent features')
        self.maximum_shift = max_shift
        self.maximum_scale_change = max_scale_change

    def transform(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        found, valid, _ = cv2.calcOpticalFlowPyrLK(self.first_gray, gray, self.points, None,
                                                winSize=(31, 31), maxLevel=4)
        if found is None:
            raise ValueError('Carrier lost')
        back, back_valid, _ = cv2.calcOpticalFlowPyrLK(gray, self.first_gray, found, None,
                                                    winSize=(31, 31), maxLevel=4)
        if back is None:
            raise ValueError('Carrier reverse tracking lost')
        good = (valid.ravel() > 0) & (back_valid.ravel() > 0)
        good &= np.linalg.norm(back-self.points, axis=2).ravel() < 1.0
        if good.sum() < 10:
            raise ValueError('Carrier has too few consistent correspondences')
        matrix, inliers = cv2.estimateAffinePartial2D(self.points[good], found[good],
            method=cv2.RANSAC, ransacReprojThreshold=1.2, maxIters=3000, confidence=.995)
        if matrix is None or inliers.sum() < 8:
            raise ValueError('Carrier transform ambiguous')
        projected = cv2.transform(self.points[good], matrix)
        residual = np.linalg.norm(projected-found[good], axis=2).ravel()[inliers.ravel() > 0]
        scale = float(np.sqrt(abs(np.linalg.det(matrix[:, :2]))))
        if (np.linalg.norm(matrix[:, 2]) > self.maximum_shift
                or abs(scale-1) > self.maximum_scale_change or np.median(residual) > 1):
            raise ValueError('Carrier motion exceeded reviewed bounds')
        return np.vstack((matrix, [0, 0, 1])), {'inliers': int(inliers.sum()),
            'medianResidual': float(np.median(residual)), 'scale': scale}


def composite(source, reference, destination, definition):
    source, reference, destination = map(Path, (source, reference, destination))
    if destination.exists():
        raise ValueError('Retain candidate and choose a new destination')
    cap = cv2.VideoCapture(str(source))
    ok, first = cap.read()
    if not ok:
        raise ValueError('Cannot read source')
    texture = cv2.imread(str(reference))
    if texture is None or texture.shape != first.shape:
        raise ValueError('Artwork must have the same native frame dimensions')
    fps = cap.get(cv2.CAP_PROP_FPS)
    native_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    mask = polygon_mask(first.shape, definition['patchPolygons'])
    feather = definition.get('feather', 3)
    if feather < 0 or feather > 12:
        raise ValueError('Invalid edge feather')
    if feather:
        # Inward feather keeps all covered pixels inside the reviewed polygon.
        mask = np.minimum(cv2.distanceTransform(mask, cv2.DIST_L2, 5)/feather, 1)
    else:
        mask = mask.astype(np.float32)/255
    tracker = CarrierTracker(first, definition['carrierPolygons'],
        definition.get('excludedPolygons', definition['patchPolygons']),
        definition.get('maxShift', 40), definition.get('maxScaleChange', .12))
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix('.partial.mp4')
    metrics, frame_index = [], 0
    with destination.with_suffix('.encoder.log').open('wb') as errors:
        encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
            '-s', f'{first.shape[1]}x{first.shape[0]}', '-r', str(fps), '-i', 'pipe:0', '-an',
            '-c:v', 'libx264', '-crf', '15', '-preset', 'fast', '-pix_fmt', 'yuv420p', str(partial)],
            stdin=subprocess.PIPE, stderr=errors)
        try:
            current = first
            while True:
                if frame_index:
                    matrix, metric = tracker.transform(current)
                else:
                    matrix, metric = np.eye(3), {'inliers': len(tracker.points), 'medianResidual': 0, 'scale': 1}
                patch = cv2.warpPerspective(texture, matrix, (first.shape[1], first.shape[0]))
                alpha = cv2.warpPerspective(mask, matrix, (first.shape[1], first.shape[0]))[..., None]
                result = np.clip(patch.astype(np.float32)*alpha+current*(1-alpha), 0, 255).astype(np.uint8)
                encoder.stdin.write(result.tobytes())
                metrics.append({'frame': frame_index, 'matrix': matrix.tolist(), **metric})
                frame_index += 1
                ok, current = cap.read()
                if not ok:
                    break
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Encoder failed; original retained')
        finally:
            cap.release()
            if encoder.poll() is None:
                encoder.kill()
                encoder.wait()
    if frame_index != native_frames:
        raise ValueError('Partial decoding is not acceptable')
    subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(partial), '-f', 'null', '-'],
                   check=True, timeout=180)
    partial.replace(destination)
    receipt = {'schemaVersion': 'vivhite-carrier-plane-1', 'sourceSha256': sha(source),
        'referenceSha256': sha(reference), 'workerSha256': sha(__file__), 'definition': definition,
        'sha256': sha(destination), 'fps': fps, 'frames': frame_index, 'tracking': metrics,
        'method': 'Full original printed texture projected with frame-zero carrier-only forward/backward LK; entire artwork excluded from tracking.',
        'fullDecode': 'passed', 'semanticAcceptance': 'pending-actual-sequence-review',
        'humanFullPlayback': False}
    destination.with_suffix('.carrier.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--definition', type=Path, required=True)
    args = parser.parse_args()
    composite(args.source, args.reference, args.destination, json.loads(args.definition.read_text(encoding='utf-8')))
