"""Retain measured whole-badge lighting still trials for the legacy S03 projection."""
import argparse
import copy
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, now
from reference_finisher import sha
from print_lighting_calibration import estimate_skin_gain
from restore_printed_eyes import reference_eye_layers
from restore_printed_regions import bound_mask_bottom
from restore_printed_badge_lighting import prepare


def trials(run, destination):
    selection = read(run / 'source-selections.json')['selections']['S03']
    previous = run / selection['path']
    receipt = read(run / selection['receipt'])
    raw = run / 'sources/S03.mp4'
    reference_file = EP / 'assets/generated/production-v2-fasth3-001/masters/M05-badge-v1.png'
    if (sha(raw) != receipt['sourceSha256'] or sha(previous) != selection['sha256']
            or sha(reference_file) != receipt['referenceTextureSha256']):
        raise ValueError('Actual source or original reference changed')
    if destination.exists():
        raise ValueError('Keep previous trials and use a new destination')
    destination.mkdir(parents=True)
    cap, previous_cap = cv2.VideoCapture(str(raw)), cv2.VideoCapture(str(previous))
    try:
        ok, first = cap.read()
        if not ok:
            raise ValueError('Unreadable source')
        reference = cv2.imread(str(reference_file), cv2.IMREAD_UNCHANGED)
        _, mask = reference_eye_layers(reference, [530, 714, 775, 690], [1, 1, 1], 1.9)
        mask = bound_mask_bottom(mask, 900, 35)
        x0, y0, x1, y1 = receipt['referenceBox']
        u0, v0, u1, v1 = receipt['targetBox']
        matrix = np.asarray([[(u1-u0)/(x1-x0), 0, u0-x0*(u1-u0)/(x1-x0)],
            [0, (v1-v0)/(y1-y0), v0-y0*(v1-v0)/(y1-y0)]], dtype=np.float64)
        measurement = estimate_skin_gain(reference, first, matrix, [530, 714, 775, 690], mask)
        native_scale = float(np.linalg.svd(matrix[:, :2], compute_uv=False).min())
        base = {'frames': receipt['frames'], 'sourceSha256': sha(raw), 'reference': str(reference_file),
            'referenceSha256': sha(reference_file), 'referenceBox': receipt['referenceBox'],
            'targetBox': receipt['targetBox'], 'center': receipt['center'], 'radius': receipt['radius'],
            'maximumTrackedScale': receipt['maximumTrackedScale'],
            'referenceSofteningSigma': .5/native_scale, 'lightingMeasurement': measurement,
            'sourceReceiptSha256': sha(run / selection['receipt'])}
        variants = []
        for number, factor in enumerate((.94, 1, 1.06), 1):
            configuration = copy.deepcopy(base)
            configuration['gainRgb'] = np.minimum(np.asarray(measurement['proposedGainRgb'])*factor, 1).tolist()
            configuration['factor'] = factor
            file = destination / f'S03-trial-{number:02}-configuration.json'
            save(file, configuration)
            tracker, frame = prepare(first, reference, configuration)
            variants.append((number, tracker, frame))
        samples = {0, receipt['frames']//2, receipt['frames']-1}
        evidence = []
        for index in range(receipt['frames']):
            image = first
            if index:
                ok, image = cap.read()
                if not ok:
                    raise ValueError('Truncated source')
                variants = [(number, tracker, tracker.frame(image)[0]) for number, tracker, _ in variants]
            if index not in samples:
                continue
            previous_cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, old = previous_cap.read()
            if not ok:
                raise ValueError('Unreadable historical comparison')
            tracker = variants[0][1]
            point = cv2.perspectiveTransform(np.float32([[receipt['center']]]), tracker.transform)[0, 0]
            scale = np.sqrt(abs(np.linalg.det(tracker.transform[:2, :2])))
            half = receipt['radius'] * scale * 1.3
            box = [max(0, round(point[0]-half)), max(0, round(point[1]-half)),
                min(3840, round(point[0]+half)), min(2160, round(point[1]+half))]
            width, height = box[2]-box[0], box[3]-box[1]
            page = Image.new('RGB', (width*5, height+28), '#242424')
            for column, (label, frame) in enumerate([('raw', image), ('previous-bright', old),
                    *[(f'trial-{number:02}', frame) for number, _, frame in variants]]):
                tile = Image.fromarray(cv2.cvtColor(frame[box[1]:box[3], box[0]:box[2]], cv2.COLOR_BGR2RGB))
                file = destination / f'S03-{label}-f{index:03}-native.png'
                tile.save(file)
                evidence.append({'path': file.relative_to(EP).as_posix(), 'sha256': sha(file), 'frame': index})
                page.paste(tile, (column*width, 28))
                ImageDraw.Draw(page).text((column*width+4, 5), f'{label} f{index}', fill='white')
            page.save(destination / f'S03-lighting-trials-f{index:03}.jpg', quality=95, subsampling=0)
        if cap.read()[0]:
            raise ValueError('Unexpected extra source frame')
        save(destination / 'manifest.json', {'createdAt': now(), 'workerSha256': sha(__file__),
            'sourceSha256': sha(raw), 'previousCorrectedSha256': sha(previous),
            'measurement': measurement, 'evidence': evidence, 'semanticAcceptance': False,
            'scope': 'Three still samples per trial; no complete-source approval.'})
    finally:
        cap.release()
        previous_cap.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    trials(args.run.resolve(), args.destination.resolve())
