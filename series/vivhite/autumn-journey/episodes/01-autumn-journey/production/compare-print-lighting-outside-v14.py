"""Compare every raw/revised frame outside a print using a retained prior ROI definition."""
import argparse
import math
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, now
from reference_finisher import sha


def compare(run, source, baseline):
    receipt, prior = read(source.with_suffix('.json')), read(baseline)
    shot = source.stem[:3]
    raw = run / f'sources/{shot}.mp4'
    if sha(raw) != receipt['sourceSha256'] or prior['rawSha256'] != sha(raw):
        raise ValueError('Both ROI definition and correction must bind the same raw source')
    if sha(source) != receipt['correctedSha256']:
        raise ValueError('Revised source changed')
    destination = EP / f'assets/generated/production-v11-native-4k-001/review/{source.stem}/outside'
    destination.mkdir(exist_ok=False)
    regions = {name: row['box'] for name, row in prior['regions'].items()}
    scores = {name: [] for name in regions}
    captures = [cv2.VideoCapture(str(path)) for path in (raw, source)]
    try:
        for index in range(receipt['frames']):
            frames = []
            for capture in captures:
                ok, frame = capture.read()
                if not ok or frame.shape != (2160, 3840, 3):
                    raise ValueError('Incomplete native frame comparison')
                frames.append(frame)
            for name, (x0, y0, x1, y1) in regions.items():
                crops = [frame[y0:y1, x0:x1] for frame in frames]
                mse = float(np.mean((crops[0].astype(np.float32)-crops[1].astype(np.float32))**2))
                scores[name].append(100 if mse == 0 else 10*math.log10(255*255/mse))
                if index in (0, receipt['frames']-1):
                    for label, crop in zip(('raw', 'revised'), crops):
                        Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)).save(
                            destination / f'{label}-{name}-f{index:03}.png')
        if any(capture.read()[0] for capture in captures):
            raise ValueError('Unexpected extra source frame')
    finally:
        for capture in captures:
            capture.release()
    save(EP / f'production/{source.stem}-outside-comparison.json', {
        'createdAt': now(), 'workerSha256': sha(__file__), 'rawSha256': sha(raw),
        'correctedSha256': sha(source), 'decodedFramePairs': receipt['frames'],
        'priorRegionDefinitionSha256': sha(baseline),
        'regions': {name: {'box': regions[name], 'minimumPsnrDb': min(values),
            'meanPsnrDb': sum(values)/len(values), 'perFramePsnrDb': values} for name, values in scores.items()},
        'scope': 'New all-frame lossy encode comparison; no prior scores or approval reused. Not pixel identity or semantic approval.'})
    save(destination / 'manifest.json', {'rawSha256': sha(raw), 'correctedSha256': sha(source),
        'images': [{'path': path.relative_to(EP).as_posix(), 'sha256': sha(path),
            'bytes': path.stat().st_size} for path in sorted(destination.iterdir())]})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--baseline', required=True, type=Path)
    arguments = parser.parse_args()
    compare(arguments.run.resolve(), arguments.source.resolve(), arguments.baseline.resolve())
