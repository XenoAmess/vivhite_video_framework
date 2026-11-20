"""Rebuild dimmed original prints from raw video, with explicit local lighting.

Preserves historical restorers and candidates. Never adjusts a human face.
GPL-3.0-only.
"""
import argparse
import importlib.util
from pathlib import Path

import cv2
import numpy as np

from local_video_pipeline import read, save
from restore_printed_eyes import eye_registration, reference_eye_layers, tracked_reference_layers
from restore_printed_regions import bound_mask_bottom, inert_native_template
from stabilize_printed_patch import PrintedPatch, fingerprint


def gain_at_frame(definition, index):
    points = definition.get('gainRgbKeyframes')
    if points is None:
        return np.asarray(definition['gainRgb'], dtype=np.float64)
    positions = [row['frame'] for row in points]
    gains = np.asarray([row['gainRgb'] for row in points], dtype=np.float64)
    if (len(points) < 2 or positions[0] != 0
            or any(type(value) is not int or value < 0 for value in positions)
            or any(left >= right for left, right in zip(positions, positions[1:]))
            or gains.shape != (len(points), 3) or not np.isfinite(gains).all()
            or np.any(gains <= 0) or np.any(gains > 1.5)
            or not np.allclose(gains[0], definition['gainRgb'], atol=1e-8)):
        raise ValueError('Ordered finite lighting keyframes must start at the bound frame-zero gain')
    if index <= 0:
        return gains[0]
    if index >= positions[-1]:
        return gains[-1]
    right = next(number for number, frame in enumerate(positions) if frame >= index)
    fraction = (index - positions[right - 1]) / (positions[right] - positions[right - 1])
    weight = fraction * fraction * (3 - 2 * fraction)
    return gains[right - 1] * (1 - weight) + gains[right] * weight


def texture_at_frame(region, index):
    definition = region['definition']
    if 'gainRgbKeyframes' not in definition:
        return region['texture']
    ratio_bgr = (gain_at_frame(definition, index) / np.asarray(definition['gainRgb']))[::-1]
    if 'nativeFaceContribution' in region:
        # A complete inert template also includes its original prop/background.
        # Change only the projected face contribution inside that template.
        return region['texture'] + region['nativeFaceContribution'] * (ratio_bgr - 1)
    return region['texture'] * ratio_bgr


def prepare_regions(first, definitions):
    if not definitions or len({row['id'] for row in definitions}) != len(definitions):
        raise ValueError('Uniquely identified original print regions required')
    prepared = []
    for definition in definitions:
        gain_at_frame(definition, 0)
        reference_file = Path(definition['reference'])
        if fingerprint(reference_file) != definition['referenceSha256']:
            raise ValueError('Original artwork changed')
        reference = cv2.imread(str(reference_file), cv2.IMREAD_UNCHANGED)
        texture, mask = reference_eye_layers(reference, definition['referenceEyes'],
            definition['gainRgb'], definition['maskScale'])
        sigma = definition.get('referenceSofteningSigma', 0)
        if not np.isfinite(sigma) or not 0 <= sigma <= 5:
            raise ValueError('Explicit reference-space softening from zero to five pixels required')
        if sigma:
            texture = cv2.GaussianBlur(texture, (0, 0), sigma)
        if 'referenceMaskBottom' in definition:
            mask = bound_mask_bottom(mask, definition['referenceMaskBottom'],
                definition['referenceMaskBottomFeather'])
        mode = definition.get('registrationMode', 'two-eye-similarity')
        if mode == 'three-point-affine-face':
            reference_points = np.asarray(definition['referenceLandmarks'], np.float32)
            target_points = np.asarray(definition['targetLandmarks'], np.float32)
            if (reference_points.shape != (3, 2) or target_points.shape != (3, 2)
                    or not np.isfinite(reference_points).all() or not np.isfinite(target_points).all()):
                raise ValueError('Three finite bound face landmarks required')
            registration = cv2.getAffineTransform(reference_points, target_points)
            if abs(np.linalg.det(registration[:, :2])) < 1e-8:
                raise ValueError('Degenerate three-point print registration')
        elif mode == 'two-eye-similarity':
            registration = eye_registration(definition['referenceEyes'], definition['targetEyes'])
        else:
            raise ValueError('Unsupported print registration mode')
        native_face = None
        if 'inertSourcePolygon' in definition:
            if 'gainRgbKeyframes' in definition:
                face, alpha = tracked_reference_layers(texture, mask, registration,
                    np.eye(3), (first.shape[1], first.shape[0]))
                native_face = face * alpha[:, :, None]
            texture, mask, registration = inert_native_template(first, texture, mask, registration,
                definition['inertSourcePolygon'], definition['inertSourceFeatherPixels'])
        tracker = PrintedPatch(cv2.resize(first, (1344, 768)),
            tuple(definition['trackingCenter']), definition['trackingRadius'])
        prepared.append({'definition': definition, 'texture': texture, 'mask': mask,
            'registration': registration, 'tracker': tracker, 'tracking': []})
        if native_face is not None:
            prepared[-1]['nativeFaceContribution'] = native_face
    return prepared


def restore(source, destination, configuration):
    # Load an isolated module so the historical restorer's preparation function
    # cannot be modified for another caller in this process.
    settings = read(configuration)
    for definition in settings['regions']:
        gain_at_frame(definition, 0)
        if 'gainRgbKeyframes' in definition and definition['gainRgbKeyframes'][-1]['frame'] != settings['frames'] - 1:
            raise ValueError('Lighting curve must cover the complete bound source')
    original = Path(__file__).with_name('restore_printed_regions.py')
    spec = importlib.util.spec_from_file_location('lighting_scoped_region_encoder', original)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    regions_by_texture = {}
    counters = {}

    def prepare_for_encoder(first, definitions):
        regions = prepare_regions(first, definitions)
        for region in regions:
            key = id(region['texture'])
            regions_by_texture[key], counters[key] = region, 0
        return regions

    def project_for_encoder(texture, mask, registration, transform, size):
        key = id(texture)
        if key not in regions_by_texture:
            raise ValueError('Unbound lighting projection')
        index = counters[key]
        counters[key] += 1
        return tracked_reference_layers(texture_at_frame(regions_by_texture[key], index),
            mask, registration, transform, size)

    module.prepare_regions = prepare_for_encoder
    module.tracked_reference_layers = project_for_encoder
    result = module.restore(source, destination, configuration)
    result.update(lightingWorkerSha256=fingerprint(__file__),
        originalRegionWorkerSha256=fingerprint(original),
        lightingScope='Explicit scene-calibrated RGB gains, optional smooth source-bound lighting keyframes, '
            'and bounded reference-space softening. '
            'Raw video remains the base; no global grade, human anatomy patch or duration change.',
        semanticAcceptance=False)
    save(Path(destination).with_suffix('.json'), result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--configuration', required=True, type=Path)
    args = parser.parse_args()
    restore(args.source, args.destination, args.configuration)
