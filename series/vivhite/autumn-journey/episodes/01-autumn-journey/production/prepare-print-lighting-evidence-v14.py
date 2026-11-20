"""Decode and extract lighting candidates; actual visual review stays separate."""
import argparse
import math
import os
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, now
from reference_finisher import sha
from review_reference_clips import inspect

OUTSIDE = {
    'S42': {'upper-scene': [0, 0, 3840, 550], 'right-hand-and-sleeves': [2530, 400, 3840, 1750]},
    'S43': {'left-landscape': [0, 0, 1800, 2160], 'right-lantern-and-cup': [2300, 0, 3840, 2160]}}


def prepare(run, shot_id, source):
    receipt = read(source.with_suffix('.json'))
    digest = sha(source)
    if digest != receipt['correctedSha256']:
        raise ValueError('Candidate bytes differ from rendering receipt')
    plan = EP / 'production-plan-v11-native-4k.json'
    if sha(plan) != '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa':
        raise ValueError('Submitted source plan changed')
    shot = next(row for row in read(plan)['shots'] if row['id'] == shot_id).copy()
    shot['seconds'] = shot['sourceSeconds']
    review = EP / 'assets/generated/production-v11-native-4k-001/review'
    reports = run / f'corrections/{source.stem}-inspection'
    if reports.exists():
        raise ValueError('Preserve existing evidence; do not overwrite inspection')
    inspect(source, shot, review / source.stem / 'inspection', reports,
        Path('D:/workspace/vivhite-analysis-output/models/opencv-yunet-2023mar/face_detection_yunet_2023mar.onnx'))
    report = reports / f'{shot_id}.json'
    result = {'startedAt': now(), 'sourceSha256': digest, 'workerSha256': sha(__file__),
        'inspectionReportSha256': sha(report), 'semanticAcceptance': False, 'commands': []}
    commands = [('prepare-review-viewing-copies-v11.py', ['--directory', str(run), '--shot', shot_id,
        '--source', str(source), '--report', str(report)])]
    for number, region in enumerate(receipt['regions'], 1):
        commands.append(('inspect-print-details-v11.py', ['--source', str(source), '--identity',
            f'{source.stem}-r{number:02}', '--center', *map(str, region['trackingCenter']),
            '--radius', str(region['trackingRadius']), '--frames', str(receipt['frames']), '--max-scale', '2.5']))
    commands.append(('extract-native-candidates-v11.py', ['--source', str(source), '--report', str(report),
        '--destination', str(review / source.stem / 'all-candidates')]))
    for index, (name, arguments) in enumerate(commands, 1):
        worker = EP / 'production' / name
        before = sha(worker)
        with (run / f'logs/{source.stem}-evidence-{index:02}.log').open('xb') as log:
            subprocess.run([sys.executable, '-X', 'utf8', str(worker), *arguments], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT, check=True, timeout=1800)
        if sha(worker) != before:
            raise ValueError('Evidence worker changed')
        result['commands'].append({'worker': name, 'workerSha256': before, 'arguments': arguments, 'exitCode': 0})
        save(run / f'metadata/{source.stem}-evidence.json', result)
    if shot_id in OUTSIDE:
        raw = run / f'sources/{shot_id}.mp4'
        if sha(raw) != receipt['sourceSha256']:
            raise ValueError('Raw source changed')
        destination = review / source.stem / 'outside'
        destination.mkdir(exist_ok=False)
        scores = {name: [] for name in OUTSIDE[shot_id]}
        captures = [cv2.VideoCapture(str(path)) for path in (raw, source)]
        try:
            for index in range(receipt['frames']):
                frames = []
                for capture in captures:
                    ok, frame = capture.read()
                    if not ok or frame.shape != (2160, 3840, 3):
                        raise ValueError('Incomplete native frame-pair comparison')
                    frames.append(frame)
                for name, (x0, y0, x1, y1) in OUTSIDE[shot_id].items():
                    crops = [frame[y0:y1, x0:x1] for frame in frames]
                    mse = float(np.mean((crops[0].astype(np.float32) - crops[1].astype(np.float32)) ** 2))
                    scores[name].append(100.0 if mse == 0 else 10 * math.log10(255 * 255 / mse))
                    if index in (0, receipt['frames'] - 1):
                        for label, crop in zip(('raw', 'corrected'), crops):
                            Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).save(
                                destination / f'{label}-{name}-f{index:03}.png')
            if any(capture.read()[0] for capture in captures):
                raise ValueError('Unexpected extra frame')
        finally:
            for capture in captures:
                capture.release()
        comparison = {'rawSha256': sha(raw), 'correctedSha256': digest,
            'decodedFramePairs': receipt['frames'], 'regions': {name: {'box': OUTSIDE[shot_id][name],
                'minimumPsnrDb': min(values), 'meanPsnrDb': sum(values) / len(values),
                'perFramePsnrDb': values} for name, values in scores.items()},
            'meaning': 'Lossy encode comparison outside print; not pixel identity or automatic semantic approval.'}
        comparison_file = EP / f'production/{source.stem}-outside-comparison.json'
        save(comparison_file, comparison)
        save(destination / 'manifest.json', {'rawSha256': sha(raw), 'correctedSha256': digest,
            'images': [{'path': path.relative_to(EP).as_posix(), 'bytes': path.stat().st_size,
                'sha256': sha(path)} for path in sorted(destination.iterdir())]})
        result['outsideComparisonSha256'] = sha(comparison_file)
    result['finishedAt'] = now()
    save(run / f'metadata/{source.stem}-evidence.json', result)
    print(source.stem, 'complete evidence prepared; actual review pending', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--shot', required=True)
    parser.add_argument('--source', required=True, type=Path)
    args = parser.parse_args()
    os.environ['PATH'] = os.pathsep.join(read(args.run / 'metadata/durable-controller-config.json')
        ['toolDirectories']) + os.pathsep + os.environ['PATH']
    prepare(args.run.resolve(), args.shot, args.source.resolve())
