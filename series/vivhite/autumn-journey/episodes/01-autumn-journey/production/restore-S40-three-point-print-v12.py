"""Technical S40 print restoration using two eyes and the existing chin.

No other shot, original source, queue or final-film approval is changed.
GPL-3.0-only.
"""
from pathlib import Path
import argparse
import os
import shutil
import sys

import cv2
import numpy as np

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save
from reference_finisher import sha
import restore_printed_regions as core

PLAN_SHA = '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa'
SOURCE_SHA = '938a770964809294847d63237447a1ff2dec3b738e5e40d48c510ef856d55238'


def face_registration(definition):
    before = np.asarray(definition['referenceLandmarks'], dtype=np.float64)
    after = np.asarray(definition['targetLandmarks'], dtype=np.float64)
    if (definition.get('registrationMode') != 'three-point-affine-face'
            or before.shape != (3, 2) or after.shape != (3, 2)
            or not np.isfinite(before).all() or not np.isfinite(after).all()
            or not np.array_equal(before[:2].reshape(-1), definition['referenceEyes'])
            or not np.array_equal(after[:2].reshape(-1), definition['targetEyes'])
            or 'inertSourcePolygon' in definition):
        raise ValueError('Explicit finite eye/eye/chin landmarks and current-frame base required')
    first_area = np.linalg.det(np.column_stack((before[1] - before[0], before[2] - before[0])))
    second_area = np.linalg.det(np.column_stack((after[1] - after[0], after[2] - after[0])))
    if abs(first_area) < 100 or abs(second_area) < 100 or first_area * second_area <= 0:
        raise ValueError('Noncollinear landmarks with the same orientation required')
    matrix = cv2.getAffineTransform(before.astype(np.float32), after.astype(np.float32))
    scales = np.linalg.svd(matrix[:, :2], compute_uv=False)
    projected = before @ matrix[:, :2].T + matrix[:, 2]
    if (np.linalg.det(matrix[:, :2]) <= 0 or min(scales) < .35 or max(scales) > .8
            or max(scales) / min(scales) > 1.5 or not np.allclose(projected, after, atol=.01)):
        raise ValueError('Bounded nonreflecting face registration required')
    return matrix


def restore(directory):
    plan = EP / 'production-plan-v11-native-4k.json'
    configuration = EP / 'production/S40-reference-restoration-configuration-v11.json'
    source = directory / 'sources/S40.mp4'
    destination = directory / 'corrections/S40-reference-sticker-v1.mp4'
    assert sha(plan) == PLAN_SHA and sha(source) == SOURCE_SHA
    config = read(configuration)
    assert config['sourceSha256'] == SOURCE_SHA and config['frames'] == 120
    assert len(config['regions']) == 1 and config['regions'][0]['id'] == 'M09-train-window'
    matrices = [face_registration(row) for row in config['regions']]
    assert not any(path.exists() for path in (destination, destination.with_suffix('.partial.mp4'),
        destination.with_suffix('.json'), destination.with_suffix('.encoder.log')))
    checkpoint = directory / 'checkpoints/S40-reference-restore-v1'
    checkpoint.mkdir(exist_ok=False)
    workers = {}
    for name in ['restore_printed_regions.py', 'restore_printed_eyes.py', 'stabilize_printed_patch.py']:
        worker = ROOT / 'video-maker/tools' / name
        shutil.copyfile(worker, checkpoint / name)
        workers[name] = sha(worker)
    shutil.copyfile(configuration, checkpoint / 'configuration.json')
    shutil.copyfile(__file__, checkpoint / 'actual-restoration-worker.py')
    save(checkpoint / 'bindings.json', {'configurationSha256': sha(configuration),
        'actualWrapperSha256': sha(__file__), 'workers': workers, 'semanticAcceptance': False})
    original_prepare = core.prepare_regions

    def prepare_with_chin(first, definitions):
        rows = original_prepare(first, definitions)
        for row, matrix in zip(rows, matrices, strict=True):
            row['registration'] = matrix
        return rows

    os.environ['PATH'] = os.pathsep.join(read(directory / 'metadata/durable-controller-config.json')
        ['toolDirectories']) + os.pathsep + os.environ.get('PATH', '')
    try:
        core.prepare_regions = prepare_with_chin
        receipt = core.restore(source, destination, configuration)
    finally:
        core.prepare_regions = original_prepare
    assert all(sha(ROOT / 'video-maker/tools' / name) == digest for name, digest in workers.items())
    assert sha(source) == SOURCE_SHA
    shutil.copyfile(destination.with_suffix('.json'), checkpoint / 'original-core-receipt.json')
    receipt.update(registrationOverrideWorkerSha256=sha(__file__),
        registrationOverrideMode='Explicit nonreflecting three-point eye/eye/chin affine face projection',
        currentFrameOutsidePrintPreservedBeforeLossyEncoding=True,
        formalFilmApproval=False, semanticAcceptance=False)
    save(destination.with_suffix('.json'), receipt)
    print('S40 technical affine print correction completed; actual complete-frame review required.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    restore(parser.parse_args().directory.resolve())
