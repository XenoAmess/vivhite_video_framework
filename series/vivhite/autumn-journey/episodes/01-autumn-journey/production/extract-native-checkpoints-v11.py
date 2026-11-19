"""Extract explicit native UHD frame checkpoints without altering the source.

Bound complete-source inspection is required. This never approves a clip.
GPL-3.0-only.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path
import re
import sys

import cv2
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from reference_finisher import sha


def preserve(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve existing evidence; use another destination')
    if not path.exists():
        path.write_bytes(data)


def extract(source, report_file, destination, identity, frames):
    source, report_file, destination = Path(source).resolve(), Path(report_file).resolve(), Path(destination).resolve()
    review_root = EP / 'assets/generated/production-v11-native-4k-001/review'
    if not re.fullmatch(r'S\d{2}', identity) or not destination.is_relative_to(review_root.resolve()):
        raise ValueError('Use a shot ID and retain images inside this project review directory')
    digest = sha(source)
    report = json.loads(report_file.read_text(encoding='utf-8'))
    expected = report['decodedFrames']
    if (report.get('status') != 'decoded' or expected not in (120, 240, 336)
            or report['usedFramesAnalysed'] != expected
            or report['identity']['sourceSha256'] != digest):
        raise ValueError('Complete native-source inspection bound to these exact source bytes required')
    if not frames or len(frames) > 64 or len(set(frames)) != len(frames) or any(frame < 0 or frame >= expected for frame in frames):
        raise ValueError('Choose one to sixty-four unique frame indices inside the complete source')
    wanted = set(frames)
    capture = cv2.VideoCapture(str(source))
    items = []
    index = 0
    try:
        if (round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                round(capture.get(cv2.CAP_PROP_FPS))) != (3840, 2160, 24):
            raise ValueError('Require actual native3840x2160 at24fps')
        while True:
            ok, picture = capture.read()
            if not ok:
                break
            if index in wanted:
                image = Image.fromarray(cv2.cvtColor(picture, cv2.COLOR_BGR2RGB))
                buffer = BytesIO()
                image.save(buffer, format='JPEG', quality=94)
                path = destination / f'{identity}-{digest[:10]}-native-f{index:03}.jpg'
                preserve(path, buffer.getvalue())
                items.append({'frame': index, 'seconds': index / 24,
                    'path': path.relative_to(EP).as_posix(), 'sha256': sha(path)})
            index += 1
    finally:
        capture.release()
    if index != expected or len(items) != len(wanted) or sha(source) != digest:
        raise ValueError('Source changed or complete decoding differs; retain partial evidence for investigation')
    receipt = {'schemaVersion': 'vivhite-native-frame-checkpoint-extraction-1',
        'shotId': identity, 'sourceSha256': digest, 'inspectionReportSha256': sha(report_file),
        'workerSha256': sha(__file__), 'decodedFrames': index, 'nativeSize': [3840, 2160],
        'fps': 24, 'frames': items, 'imageEncoding': 'native-size-JPEG94-viewing-copy',
        'resized': False, 'sourceVideoChanged': False, 'semanticAcceptanceGranted': False,
        'humanContinuousPlayback': False}
    preserve(destination / f'{identity}-{digest[:10]}-native-checkpoints.json',
        (json.dumps(receipt, indent=2) + '\n').encode('utf-8'))
    print(identity, len(items), 'explicit native checkpoints extracted; no semantic pass.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--shot', required=True)
    parser.add_argument('--frames', type=int, nargs='+', required=True)
    args = parser.parse_args()
    extract(args.source, args.report, args.destination, args.shot, args.frames)
