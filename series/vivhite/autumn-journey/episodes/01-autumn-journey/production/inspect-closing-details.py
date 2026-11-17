"""Export every native S48 wing-region frame without editing or approving video.

GPL-3.0-only.
"""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

EPISODE = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as content:
        return hashlib.file_digest(content, 'sha256').hexdigest()


def preserve(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f'Preserve existing evidence: {path}')
    if not path.exists():
        path.write_bytes(data)


def picture(path, value, quality=None):
    output = BytesIO()
    value.save(output, format='JPEG' if quality else 'PNG', **({'quality': quality} if quality else {}))
    preserve(path, output.getvalue())


def inspect(directory, box, expected_frames, source=None):
    directory = Path(directory).resolve()
    source = Path(source).resolve() if source is not None else directory / 'sources/S48.mp4'
    if not source.is_relative_to(directory):
        raise ValueError('Inspect an actual source or candidate inside its own run')
    digest = sha(source)
    prefix = f'S48-{digest[:10]}'
    evidence = EPISODE / 'assets/generated' / directory.name / 'review/video-768p'
    cap = cv2.VideoCapture(str(source))
    crops, first, last = [], None, None
    try:
        if not cap.isOpened():
            raise ValueError('An actual completed S48 source is required')
        width, height = (round(cap.get(prop)) for prop in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT))
        x1, y1, x2, y2 = box
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height) or expected_frames <= 0:
            raise ValueError('Inspection box or expected frame count is invalid')
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if first is None:
                first = rgb.copy()
            last = rgb
            crops.append(rgb.crop(box))
    finally:
        cap.release()
    if len(crops) != expected_frames:
        raise ValueError(f'Full source frame count mismatch: {len(crops)} != {expected_frames}')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 13)
    pages = []
    for start in range(0, len(crops), 120):
        part = crops[start:start + 120]
        cell_width, cell_height = x2 - x1, y2 - y1 + 20
        canvas = Image.new('RGB', (cell_width * 10, cell_height * math.ceil(len(part) / 10)), '#242424')
        draw = ImageDraw.Draw(canvas)
        for index, crop in enumerate(part):
            x, y = index % 10 * cell_width, index // 10 * cell_height
            draw.text((x + 3, y + 2), f'f{start + index:03}', font=font, fill='white')
            canvas.paste(crop, (x, y + 20))
        target = evidence / f'{prefix}-all-butterfly-frames-{start // 120 + 1:02}.png'
        picture(target, canvas)
        picture(evidence / 'proxies' / (target.stem + '.jpg'), canvas, quality=92)
        pages.append({'path': target.relative_to(EPISODE).as_posix(), 'sha256': sha(target),
                      'firstFrame': start, 'lastFrame': start + len(part) - 1, 'items': len(part)})
    endpoints = []
    for label, frame in [('first', first), ('last', last)]:
        target = evidence / f'{prefix}-native-{label}.png'
        picture(target, frame)
        endpoints.append({'path': target.relative_to(EPISODE).as_posix(), 'sha256': sha(target)})
    receipt = {'schemaVersion': 'vivhite-fixed-region-inspection-1', 'sourceSha256': digest,
               'workerSha256': sha(__file__), 'decodedNativeFrames': len(crops), 'box': list(box),
               'sourceSize': [width, height], 'originalPixelsOnly': True,
               'pages': pages, 'nativeEndpoints': endpoints, 'semanticAcceptance': 'not-granted'}
    preserve(evidence / f'{prefix}-butterfly-inspection.json',
             (json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'frames': len(crops), 'pages': len(pages), 'evidence': str(evidence)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--box', required=True, nargs=4, type=int)
    parser.add_argument('--expected-frames', required=True, type=int)
    parser.add_argument('--source', type=Path, help='Optional selected candidate inside the same run')
    args = parser.parse_args()
    inspect(args.directory, tuple(args.box), args.expected_frames, args.source)
