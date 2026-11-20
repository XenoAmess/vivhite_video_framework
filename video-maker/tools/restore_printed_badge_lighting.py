"""Match a legacy whole-badge projection to its scene without changing its geometry.

The original source and prior correction are retained. No semantic approval is
inferred from tracking, decoding or color measurement. GPL-3.0-only.
"""
import argparse
from pathlib import Path
import subprocess

import cv2
import numpy as np

from local_video_pipeline import read, save
from reference_finisher import sha
from stabilize_printed_patch import PrintedPatch, project_reference_texture


def prepare(first, reference, configuration):
    gain = np.asarray(configuration['gainRgb'], dtype=np.float32)
    sigma = float(configuration['referenceSofteningSigma'])
    if gain.shape != (3,) or not np.isfinite(gain).all() or not ((gain > 0) & (gain <= 1)).all():
        raise ValueError('Whole-badge gain must be three finite non-brightening multipliers')
    if not np.isfinite(sigma) or not 0 <= sigma <= 5:
        raise ValueError('Invalid original-reference softness')
    colored = reference[:, :, :3].astype(np.float32) * gain[::-1]
    if sigma:
        colored = cv2.GaussianBlur(colored, (0, 0), sigma)
    tracker = PrintedPatch(first, tuple(configuration['center']), configuration['radius'],
        configuration['maximumTrackedScale'])
    tracker.first = project_reference_texture(first, colored, configuration['referenceBox'],
        configuration['targetBox']).clip(0, 255).astype(np.uint8)
    left, top, right, bottom = configuration['targetBox']
    x, y = configuration['center']
    radius = configuration['radius']
    if not (left <= x-radius and x+radius <= right and top <= y-radius and y+radius <= bottom):
        raise ValueError('Projection does not cover the complete existing badge mask')
    result = (tracker.first.astype(np.float32) * tracker.mask[:, :, None]
        + first * (1-tracker.mask[:, :, None])).clip(0, 255).astype(np.uint8)
    return tracker, result


def restore(source, destination, configuration_file):
    configuration = read(configuration_file)
    reference_file = Path(configuration['reference'])
    if sha(source) != configuration['sourceSha256'] or sha(reference_file) != configuration['referenceSha256']:
        raise ValueError('Source or original artwork changed')
    if destination.exists() or destination.with_suffix('.partial.mp4').exists():
        raise ValueError('Retain old versions and choose a fresh output path')
    capture = cv2.VideoCapture(str(source))
    encoder = None
    try:
        ok, first = capture.read()
        fps = capture.get(cv2.CAP_PROP_FPS)
        if not ok or first.shape != (2160, 3840, 3) or abs(fps-24) > .001:
            raise ValueError('Expected a native4K/24fps source')
        reference = cv2.imread(str(reference_file), cv2.IMREAD_UNCHANGED)
        if reference is None:
            raise ValueError('Unreadable original artwork')
        tracker, frame = prepare(first, reference, configuration)
        partial = destination.with_suffix('.partial.mp4')
        destination.parent.mkdir(parents=True, exist_ok=True)
        tracking = []
        with destination.with_suffix('.encoder.log').open('xb') as errors:
            encoder = subprocess.Popen(['ffmpeg', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24',
                '-s', '3840x2160', '-r', '24', '-i', 'pipe:0', '-i', str(source),
                '-map', '0:v:0', '-map', '1:a:0?', '-c:v', 'libx264', '-preset', 'fast', '-crf', '16',
                '-pix_fmt', 'yuv420p', '-c:a', 'copy', str(partial)], stdin=subprocess.PIPE, stderr=errors)
            try:
                for index in range(configuration['frames']):
                    if index:
                        ok, image = capture.read()
                        if not ok:
                            raise ValueError('Truncated native source')
                        frame, metric = tracker.frame(image)
                        tracking.append({'frame': index, **metric})
                    encoder.stdin.write(frame.tobytes())
                if capture.read()[0]:
                    raise ValueError('Unexpected source frame count')
            finally:
                encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Badge encoder failed; original, partial and log retained')
        subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(partial), '-f', 'null', '-'],
            check=True, timeout=180)
        partial.replace(destination)
        save(destination.with_suffix('.json'), {
            'schemaVersion': 'vivhite-printed-badge-lighting-1', 'sourceSha256': sha(source),
            'correctedSha256': sha(destination), 'configurationSha256': sha(configuration_file),
            'workerSha256': sha(__file__),
            'trackingWorkerSha256': sha(Path(__file__).with_name('stabilize_printed_patch.py')),
            'frames': configuration['frames'], 'fps': 24, 'nativeSize': [3840, 2160], 'encodingPasses': 1,
            **{key: configuration[key] for key in ('reference', 'referenceSha256', 'referenceBox',
                'targetBox', 'center', 'radius', 'maximumTrackedScale', 'gainRgb', 'referenceSofteningSigma')},
            'tracking': tracking, 'semanticAcceptance': False,
            'scope': 'Original full-badge registration and physical rim tracking retained. Scene-matched color and softness only inside the legacy badge mask; no human anatomy or timing change.'})
    finally:
        capture.release()
        if encoder is not None and encoder.poll() is None:
            encoder.kill()
            encoder.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--configuration', required=True, type=Path)
    arguments = parser.parse_args()
    restore(arguments.source.resolve(), arguments.destination.resolve(), arguments.configuration.resolve())
