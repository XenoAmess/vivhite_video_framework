"""Produce lighting proposals and retained still trials, never source approval."""
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
from restore_printed_eyes import eye_registration, reference_eye_layers, tracked_reference_layers
from restore_printed_regions import blend_layers, bound_mask_bottom
from restore_printed_regions_lighting import prepare_regions, texture_at_frame
from stabilize_printed_patch import PrintedPatch


def limited_gain(measured, previous, factor=1.0):
    gain = np.asarray(measured['proposedGainRgb']) * factor
    weights = np.asarray(measured['referenceMedianRgb']) * [.2126, .7152, .0722]
    # Permit the real light to become warmer while limiting overall encoded
    # skin luminance to the previous patch. Per-channel clipping loses sunsets.
    gain *= min(1.0, float(weights @ previous) / float(weights @ gain))
    return gain.tolist()


def measure_curve(cap, first, definitions, frames):
    prepared, measurements = [], [[] for _ in definitions]
    scale = np.diag([1344 / 3840, 768 / 2160, 1])
    inverse = np.linalg.inv(scale)
    for definition in definitions:
        reference = cv2.imread(str(ROOT / definition['reference']), cv2.IMREAD_UNCHANGED)
        _, mask = reference_eye_layers(reference, definition['referenceEyes'], [1, 1, 1],
            definition['maskScale'])
        if 'referenceMaskBottom' in definition:
            mask = bound_mask_bottom(mask, definition['referenceMaskBottom'], definition['referenceMaskBottomFeather'])
        if definition.get('registrationMode') == 'three-point-affine-face':
            matrix = cv2.getAffineTransform(np.float32(definition['referenceLandmarks']),
                np.float32(definition['targetLandmarks']))
        else:
            matrix = eye_registration(definition['referenceEyes'], definition['targetEyes'])
        tracker = PrintedPatch(cv2.resize(first, (1344, 768)), tuple(definition['trackingCenter']),
            definition['trackingRadius'])
        prepared.append((reference, mask, matrix, tracker))
    for index in range(frames):
        image = first
        if index:
            ok, image = cap.read()
            if not ok:
                raise ValueError('Truncated source during lighting measurement')
        proxy = cv2.resize(image, (1344, 768))
        for number, (reference, mask, registration, tracker) in enumerate(prepared):
            if index:
                tracker.frame(proxy)
            if index not in (0, frames // 2, frames - 1):
                continue
            matrix = inverse @ tracker.transform @ scale @ np.vstack((registration, [0, 0, 1]))
            value = estimate_skin_gain(reference, image, matrix[:2], definitions[number]['referenceEyes'], mask)
            value['frame'] = index
            measurements[number].append(value)
    if cap.read()[0]:
        raise ValueError('Unexpected extra source during lighting measurement')
    if not cap.set(cv2.CAP_PROP_POS_FRAMES, 1):
        raise ValueError('Cannot return to the first rendering frame')
    return measurements


def prepare(run, shot, destination, lighting_curve=False):
    selections = read(run / 'source-selections.json')['selections']
    if shot in selections:
        receipt_file = run / selections[shot]['receipt']
    else:
        receipt_file = run / f'corrections/{shot}-reference-print-v1.json'
    receipt = read(receipt_file)
    raw = run / f'sources/{shot}.mp4'
    if sha(raw) != receipt['sourceSha256']:
        raise ValueError('Wrong raw source')
    if destination.exists():
        raise ValueError('Choose a new trial directory; retain existing trials')
    destination.mkdir(parents=True)
    definitions = copy.deepcopy(receipt.get('regions') or [receipt])
    masters = EP / 'assets/generated/production-v2-fasth3-001/masters'
    master_index = {sha(path): path for path in masters.glob('*.png')}
    cap = cv2.VideoCapture(str(raw))
    try:
        ok, first = cap.read()
        if not ok:
            raise ValueError('Cannot decode frame zero')
        measures = []
        for number, definition in enumerate(definitions, 1):
            if 'referenceEyes' not in definition:
                raise ValueError('Box-based historical print needs explicit manual lighting calibration')
            if 'reference' not in definition:
                path = master_index[definition['referenceTextureSha256']]
                definition.update(id=f'{shot}-print-{number}', reference=str(path),
                    referenceSha256=sha(path), maskScale=definition.get('referenceMaskScale', 1))
            reference = cv2.imread(str(ROOT / definition['reference']), cv2.IMREAD_UNCHANGED)
            if sha(ROOT / definition['reference']) != definition['referenceSha256']:
                raise ValueError('Reference changed')
            texture, mask = reference_eye_layers(reference, definition['referenceEyes'], [1, 1, 1],
                definition['maskScale'])
            if 'referenceMaskBottom' in definition:
                mask = bound_mask_bottom(mask, definition['referenceMaskBottom'],
                    definition['referenceMaskBottomFeather'])
            if definition.get('registrationMode') == 'three-point-affine-face':
                registration = cv2.getAffineTransform(np.float32(definition['referenceLandmarks']),
                    np.float32(definition['targetLandmarks']))
            else:
                registration = eye_registration(definition['referenceEyes'], definition['targetEyes'])
            measured = estimate_skin_gain(reference, first, registration, definition['referenceEyes'], mask)
            measured.update(id=definition['id'], previousGainRgb=definition['gainRgb'])
            measures.append(measured)
            # A proposal cannot brighten the user's rejected reference patch.
            definition['gainRgb'] = np.minimum(measured['proposedGainRgb'], definition['gainRgb']).tolist()
            # Match a subpixel softness in the native video. Reference masters
            # have different scales; a fixed two-pixel reference blur can smear
            # an almost one-to-one acrylic print while barely affecting a mug.
            native_scale = float(np.linalg.svd(registration[:, :2], compute_uv=False).min())
            if native_scale < .01:
                raise ValueError('Unusable print projection scale')
            definition['referenceSofteningSigma'] = min(2.0, .5 / native_scale)
            definition.pop('tracking', None)
            definition.pop('registration', None)
        curves = measure_curve(cap, first, definitions, receipt['frames']) if lighting_curve else None
        if curves:
            for definition, measured, curve in zip(definitions, measures, curves):
                definition['gainRgbKeyframes'] = [{'frame': value['frame'],
                    'gainRgb': limited_gain(value, measured['previousGainRgb'])} for value in curve]
                definition['gainRgb'] = definition['gainRgbKeyframes'][0]['gainRgb']
                measured['lightingKeyframeMeasurements'] = curve
        variants = []
        for number, factor in enumerate((.94, 1.0, 1.06), 1):
            config = {'frames': receipt['frames'], 'sourceSha256': sha(raw),
                'lightingCalibration': {'sourceReceiptSha256': sha(receipt_file),
                    'measurementWorkerSha256': sha(ROOT / 'video-maker/tools/print_lighting_calibration.py'),
                    'samples': measures, 'factor': factor, 'actualReview': 'pending'},
                'regions': copy.deepcopy(definitions)}
            for row, previous in zip(config['regions'], measures):
                if curves:
                    for keyframe, measurement in zip(row['gainRgbKeyframes'], previous['lightingKeyframeMeasurements']):
                        keyframe['gainRgb'] = limited_gain(measurement, previous['previousGainRgb'], factor)
                    row['gainRgb'] = row['gainRgbKeyframes'][0]['gainRgb']
                else:
                    row['gainRgb'] = np.minimum(np.asarray(row['gainRgb']) * factor,
                        previous['previousGainRgb']).tolist()
            config_file = destination / f'{shot}-trial-{number:02}-configuration.json'
            save(config_file, config)
            variants.append((number, prepare_regions(first, config['regions'])))
        scale = np.diag([1344 / 3840, 768 / 2160, 1])
        inverse = np.linalg.inv(scale)
        samples = {0, receipt['frames'] // 2, receipt['frames'] - 1}
        evidence = []
        for index in range(receipt['frames']):
            frame = first
            if index:
                ok, frame = cap.read()
                if not ok:
                    raise ValueError('Truncated source')
            proxy = cv2.resize(frame, (1344, 768))
            for _, regions in variants:
                if index:
                    for row in regions:
                        row['tracker'].frame(proxy)
            if index not in samples:
                continue
            images = [('raw', frame)]
            for number, regions in variants:
                layers = [tracked_reference_layers(texture_at_frame(row, index), row['mask'], row['registration'],
                    inverse @ row['tracker'].transform @ scale, (3840, 2160)) for row in regions]
                images.append((f'trial-{number:02}', blend_layers(frame, layers)))
            for region_number, definition in enumerate(definitions, 1):
                eyes = np.asarray(definition['targetEyes']).reshape(2, 2)
                distance = float(np.linalg.norm(eyes[1] - eyes[0]))
                points = np.column_stack((eyes, np.ones(2)))
                matrix = inverse @ variants[0][1][region_number - 1]['tracker'].transform @ scale
                moved = (matrix @ points.T).T[:, :2]
                center = moved.mean(axis=0)
                current_scale = np.sqrt(abs(np.linalg.det(matrix[:2, :2])))
                half_width, half_height = max(100, distance * 2.5) * current_scale, max(85, distance * 2) * current_scale
                box = (max(0, round(center[0] - half_width)), max(0, round(center[1] - half_height)),
                    min(3840, round(center[0] + half_width)), min(2160, round(center[1] + half_height)))
                width, height = box[2] - box[0], box[3] - box[1]
                page = Image.new('RGB', (width * 4, height + 28), '#242424')
                for column, (label, image) in enumerate(images):
                    tile = Image.fromarray(cv2.cvtColor(image[box[1]:box[3], box[0]:box[2]], cv2.COLOR_BGR2RGB))
                    name = f'{shot}-r{region_number:02}-{label}-f{index:03}-native.png'
                    tile.save(destination / name)
                    evidence.append({'path': (destination / name).relative_to(EP).as_posix(),
                        'sha256': sha(destination / name), 'frame': index, 'region': definition['id']})
                    page.paste(tile, (column * width, 28))
                    ImageDraw.Draw(page).text((column * width + 4, 5), f'{label} f{index}', fill='white')
                page.save(destination / f'{shot}-r{region_number:02}-lighting-trials-f{index:03}.jpg',
                    quality=95, subsampling=0)
        if cap.read()[0]:
            raise ValueError('Unexpected extra source frames')
        save(destination / 'manifest.json', {'schemaVersion': 'vivhite-print-lighting-trials-1',
            'createdAt': now(), 'shotId': shot, 'sourceSha256': sha(raw),
            'workerSha256': sha(__file__), 'measurements': measures, 'evidence': evidence,
            'lightingWorkerSha256': sha(ROOT / 'video-maker/tools/restore_printed_regions_lighting.py'),
            'lightingCurve': lighting_curve,
            'semanticAcceptance': False, 'scope': 'Three still samples per trial, no full-video approval.'})
        print(shot, 'three measured lighting trials prepared', flush=True)
    finally:
        cap.release()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--shots', nargs='+', required=True)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--lighting-curve', action='store_true')
    args = parser.parse_args()
    for shot_id in args.shots:
        prepare(args.run.resolve(), shot_id, args.destination.resolve() / shot_id, args.lighting_curve)
