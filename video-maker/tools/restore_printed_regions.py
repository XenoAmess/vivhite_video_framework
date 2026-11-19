"""Restore several existing merchandise prints in one native UHD encoding pass.

Track each unmodified prop independently. Original media and failed candidates
are retained; technical success does not grant semantic approval. GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np

from restore_printed_eyes import eye_registration, reference_eye_layers, tracked_reference_layers
from stabilize_printed_patch import PrintedPatch, fingerprint


def bound_mask_bottom(mask, bottom, feather):
    if (not np.isfinite([bottom, feather]).all() or not 0 < bottom <= mask.shape[0]
            or not 0 < feather < bottom):
        raise ValueError('Finite mask bottom and positive feather inside the artwork required')
    weight = np.clip((bottom-np.arange(mask.shape[0], dtype=np.float32))/feather, 0, 1)
    weight = weight*weight*(3-2*weight)
    return mask*weight[:, None]


def prepare_regions(first, definitions):
    if not definitions or len({row['id'] for row in definitions}) != len(definitions):
        raise ValueError('Nonempty, uniquely identified printed regions required')
    prepared = []
    for definition in definitions:
        reference_file = Path(definition['reference'])
        digest = fingerprint(reference_file)
        if digest != definition['referenceSha256']:
            raise ValueError('Original reference does not match the bound artwork')
        reference = cv2.imread(str(reference_file), cv2.IMREAD_UNCHANGED)
        texture, mask = reference_eye_layers(reference, definition['referenceEyes'],
            definition['gainRgb'], definition['maskScale'])
        if 'referenceMaskBottom' in definition:
            mask = bound_mask_bottom(mask, definition['referenceMaskBottom'],
                definition['referenceMaskBottomFeather'])
        registration = eye_registration(definition['referenceEyes'], definition['targetEyes'])
        tracker = PrintedPatch(cv2.resize(first, (1344, 768)),
            tuple(definition['trackingCenter']), definition['trackingRadius'])
        prepared.append({'definition': definition, 'texture': texture, 'mask': mask,
            'registration': registration, 'tracker': tracker, 'tracking': []})
    return prepared


def blend_layers(image, layers):
    """Use one unmodified frame as the base for all independently tracked prints."""
    corrected = image.astype(np.float32)
    occupied = np.zeros(image.shape[:2], dtype=bool)
    for texture, mask in layers:
        if (texture.shape != image.shape or mask.shape != image.shape[:2]
                or not np.isfinite(texture).all() or not np.isfinite(mask).all()
                or np.any(mask < 0) or np.any(mask > 1.00001)):
            raise ValueError('Finite matching texture and alpha layers required')
        meaningful = mask > .01
        if np.any(occupied & meaningful):
            raise ValueError('Separate prop masks overlap; inspect registration before encoding')
        occupied |= meaningful
        alpha = np.clip(mask, 0, 1)[:, :, None]
        corrected = texture * alpha + corrected * (1-alpha)
    return corrected.clip(0, 255).astype(np.uint8)


def restore(source, destination, configuration_file):
    source, destination, configuration_file = map(Path, (source, destination, configuration_file))
    partial = destination.with_suffix('.partial.mp4')
    receipt_file = destination.with_suffix('.json')
    log_file = destination.with_suffix('.encoder.log')
    if any(path.exists() for path in (destination, partial, receipt_file, log_file)):
        raise ValueError('Use a new correction version; preserve all existing candidates')
    config_digest = fingerprint(configuration_file)
    config = json.loads(configuration_file.read_text(encoding='utf-8'))
    frames = config['frames']
    source_digest = fingerprint(source)
    if frames not in (120, 240, 336) or source_digest != config['sourceSha256']:
        raise ValueError('Bound complete native source and legal frame count required')
    capture = cv2.VideoCapture(str(source))
    encoder = None
    try:
        actual = tuple(round(capture.get(key)) for key in (cv2.CAP_PROP_FRAME_WIDTH,
            cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT))
        if actual != (3840, 2160, 24, frames):
            raise ValueError('Require the complete native UHD source at 24 fps')
        ok, first = capture.read()
        if not ok:
            raise ValueError('Cannot decode source frame zero')
        regions = prepare_regions(first, config['regions'])
        scaling = np.diag([1344/3840, 768/2160, 1])
        inverse = np.linalg.inv(scaling)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open('xb') as log:
            encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo',
                '-pix_fmt', 'bgr24', '-s', '3840x2160', '-r', '24', '-i', 'pipe:0',
                '-i', str(source), '-map', '0:v:0', '-map', '1:a:0?', '-c:v', 'libx264',
                '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'copy',
                str(partial)], stdin=subprocess.PIPE, stderr=log)
            image = first
            for index in range(frames):
                if index:
                    ok, image = capture.read()
                    if not ok:
                        raise ValueError('Unexpected truncated source')
                proxy = cv2.resize(image, (1344, 768))
                layers = []
                for region in regions:
                    if index:
                        _, metric = region['tracker'].frame(proxy)
                        region['tracking'].append({'frame': index, **metric})
                    transform = inverse @ region['tracker'].transform @ scaling
                    layers.append(tracked_reference_layers(region['texture'], region['mask'],
                        region['registration'], transform, (3840, 2160)))
                encoder.stdin.write(blend_layers(image, layers).tobytes())
            if capture.read()[0]:
                raise ValueError('Unexpected extra source frames')
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Printed-region encoding failed; partial and log retained')
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(partial), '-f',
            'null', '-'], check=True, timeout=180)
        if (fingerprint(source) != source_digest or fingerprint(configuration_file) != config_digest
                or any(fingerprint(row['definition']['reference']) != row['definition']['referenceSha256']
                    for row in regions)):
            raise ValueError('A bound input changed during restoration')
        partial.replace(destination)
        receipt = {'schemaVersion': 'vivhite-printed-regions-restoration-1',
            'sourceSha256': source_digest, 'correctedSha256': fingerprint(destination),
            'configurationSha256': config_digest, 'workerSha256': fingerprint(__file__),
            'eyeProjectionWorkerSha256': fingerprint(Path(__file__).with_name('restore_printed_eyes.py')),
            'trackingWorkerSha256': fingerprint(Path(__file__).with_name('stabilize_printed_patch.py')),
            'frames': frames, 'fps': 24, 'nativeSize': [3840, 2160], 'encodingPasses': 1,
            'referenceProjection': 'original-artwork-to-current-frame',
            'regions': [{**row['definition'], 'registration': row['registration'].tolist(),
                'tracking': row['tracking']} for row in regions],
            'method': 'Independent original-prop tracking, original RGBA artwork projected directly into each current frame, feathered masks, one CRF16 encode from the unchanged raw source.',
            'scope': 'Masks may include fringe, cheeks, nose, mouth or chin as specified by the actual registration and mask scale; whole-frame lossy re-encoding. No person covered or removed.',
            'status': 'technical-correction-completed-review-required', 'humanFullPlayback': False}
        receipt_file.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        print(frames, 'native frames,', len(regions), 'prints, one encode; complete review required.', flush=True)
        return receipt
    finally:
        capture.release()
        if encoder is not None:
            try:
                if encoder.stdin and not encoder.stdin.closed:
                    encoder.stdin.close()
            except BrokenPipeError:
                pass
            finally:
                if encoder.poll() is None:
                    encoder.kill()
                    encoder.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--configuration', required=True, type=Path)
    args = parser.parse_args()
    restore(args.source, args.destination, args.configuration)
