"""Prepare raw/current print-lighting comparisons without granting approval.

All frames and crops stay in the episode. No HTTP calls or source mutation.
GPL-3.0-only.
"""
import argparse
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


def prepare(run, destination):
    selections = read(run / 'source-selections.json')['selections']
    sources = [(shot, run / item['path'], run / item['receipt'])
        for shot, item in selections.items()]
    sources += [(shot, run / f'corrections/{shot}-reference-print-v1.mp4',
        run / f'corrections/{shot}-reference-print-v1.json') for shot in ('S42', 'S43')]
    if destination.exists():
        raise ValueError('Preserve every prior lighting audit; choose a new destination')
    destination.mkdir(parents=True)
    results = []
    for shot, current, receipt_file in sources:
        receipt = read(receipt_file)
        raw = run / f'sources/{shot}.mp4'
        if sha(raw) != receipt['sourceSha256'] or sha(current) != receipt['correctedSha256']:
            raise ValueError(f'{shot}: actual source binding changed')
        definitions = receipt.get('regions') or [receipt]
        captures = [cv2.VideoCapture(str(path)) for path in (raw, current)]
        try:
            frames = receipt['frames']
            indexes = sorted(set((0, frames // 2, frames - 1)))
            samples = []
            for index in indexes:
                pair = []
                for capture in captures:
                    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
                    ok, image = capture.read()
                    if not ok or image.shape[:2] != (2160, 3840):
                        raise ValueError(f'{shot}: cannot decode native sample {index}')
                    pair.append(image)
                samples.append((index, pair))
            for number, definition in enumerate(definitions, 1):
                if 'targetEyes' in definition:
                    eyes = np.asarray(definition['targetEyes']).reshape(2, 2)
                    center = eyes.mean(axis=0)
                    distance = float(np.linalg.norm(eyes[1] - eyes[0]))
                    half_width, half_height = max(90, distance * 2.5), max(90, distance * 2.0)
                    center[1] += distance * .15
                    origin = np.asarray(definition['trackingCenter'], dtype=float)
                    proxy_to_native = np.array([3840 / 1344, 2160 / 768])
                else:
                    center = np.asarray(definition['center'], dtype=float)
                    half_width = half_height = definition['radius'] * 1.35
                    origin = center.copy()
                    proxy_to_native = np.ones(2)
                tracking = {row['frame']: row for row in definition.get('tracking', [])}
                crops, bindings = [], []
                for index, pair in samples:
                    metric = tracking.get(index, {'center': origin.tolist(), 'scale': 1})
                    scale = metric['scale']
                    position = np.asarray(metric['center']) * proxy_to_native
                    position += (center - origin * proxy_to_native) * scale
                    box = [max(0, round(position[0] - half_width * scale)),
                        max(0, round(position[1] - half_height * scale)),
                        min(3840, round(position[0] + half_width * scale)),
                        min(2160, round(position[1] + half_height * scale))]
                    for label, frame in zip(('raw', 'current'), pair):
                        image = Image.fromarray(cv2.cvtColor(frame[box[1]:box[3], box[0]:box[2]],
                            cv2.COLOR_BGR2RGB))
                        path = destination / f'{shot}-r{number:02}-{label}-f{index:03}-native.png'
                        image.save(path)
                        bindings.append({'frame': index, 'version': label, 'nativeBox': box,
                            'path': path.relative_to(EP).as_posix(), 'sha256': sha(path)})
                        crops.append((f'{label} f{index}', image))
                # This is a viewing copy. Original native crops are retained separately.
                width = min(640, max(image.width for _, image in crops))
                height = min(520, max(image.height for _, image in crops))
                page = Image.new('RGB', (width * 2, (height + 28) * len(indexes)), '#242424')
                draw = ImageDraw.Draw(page)
                for tile, (label, image) in enumerate(crops):
                    image = image.copy()
                    image.thumbnail((width, height))
                    x, y = (tile % 2) * width, (tile // 2) * (height + 28)
                    draw.text((x + 4, y + 4), f'{shot} r{number:02} {label}', fill='white')
                    page.paste(image, (x, y + 28))
                page_file = destination / f'{shot}-r{number:02}-raw-current.jpg'
                page.save(page_file, quality=95, subsampling=0)
                results.append({'shotId': shot, 'region': definition.get('id', f'region-{number}'),
                    'rawSha256': sha(raw), 'currentSha256': sha(current),
                    'receiptSha256': sha(receipt_file), 'gainRgb': definition.get('gainRgb'),
                    'historicalOnly': shot == 'S20', 'evidence': bindings,
                    'viewingPage': page_file.relative_to(EP).as_posix(),
                    'viewingPageSha256': sha(page_file), 'actualReview': 'pending'})
        finally:
            for capture in captures:
                capture.release()
        save(destination / 'manifest.json', {'schemaVersion': 'vivhite-print-lighting-audit-1',
            'createdAt': now(), 'workerSha256': sha(__file__), 'regions': results,
            'semanticAcceptance': False, 'scope': 'Three native samples per region; no full-clip approval.'})
        print(shot, 'lighting comparisons prepared', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.run.resolve(), args.destination.resolve())
