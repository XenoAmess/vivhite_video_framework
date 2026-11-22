"""Compact all-frame native detail proofs; no retouching or semantic approval.

GPL-3.0-only. Tracker output pixels are discarded; crops show the input video.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys

import cv2
from PIL import Image

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
from stabilize_printed_patch import PrintedPatch


def prepare(directory, definitions_file, tag):
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in tag):
        raise ValueError('Use an episode-local stable proof tag')
    helper = runpy.run_path(str(EPISODE/'production/prepare-source-proof-v1.py'))
    definitions = json.loads(definitions_file.read_text(encoding='utf-8'))
    output = EPISODE/'assets/generated/production-v1-firstframes-001/review/viewing-copies'/tag
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    cv2.setNumThreads(2)
    for sid, definition in definitions.items():
        source = directory/'sources'/f'{sid}.mp4'
        report = json.loads((directory/'clip-inspection'/f'{sid}.json').read_text(encoding='utf-8'))
        digest = helper['sha'](source)
        if digest != report['identity']['sourceSha256']:
            raise ValueError('Source and full inspection differ')
        entries, metrics = [], []
        capture = cv2.VideoCapture(str(source))
        try:
            ok, frame = capture.read()
            if not ok:
                raise ValueError('Cannot decode source')
            tracker = PrintedPatch(frame, tuple(definition['center']), definition['trackingRadius'])
            index = 0
            while ok:
                if index == 0:
                    metric = {'center': definition['center'], 'scale': 1.0}
                else:
                    _, metric = tracker.frame(frame)
                x, y = metric['center']
                if definition.get('detailCenter'):
                    import numpy as np
                    point = np.float32([[definition['detailCenter']]])
                    x, y = cv2.perspectiveTransform(point, tracker.transform)[0, 0]
                radius = definition['cropRadius']*metric['scale']
                box = [max(0, round(x-radius)), max(0, round(y-radius)),
                       min(frame.shape[1], round(x+radius)), min(frame.shape[0], round(y+radius))]
                area = frame[box[1]:box[3], box[0]:box[2]]
                entries.append((Image.fromarray(cv2.cvtColor(area, cv2.COLOR_BGR2RGB)), f'f{index}'))
                metrics.append({'frame': index, 'actualNativeBounds': box, **metric})
                index += 1
                ok, frame = capture.read()
        finally:
            capture.release()
        if index != report['decodedFrames']:
            raise ValueError('Incomplete actual-source decode')
        pages = []
        for offset in range(0, len(entries), 120):
            part = entries[offset:offset+120]
            target = output/f'{sid}-{digest[:10]}-native-details-{offset//120+1:02}.png'
            helper['sheet'](part, target, cell=(100, 124), columns=12)
            pages.append(helper['describe'](target, len(part)))
        rows.append({'id': sid, 'sourceSha256': digest, 'decodedNativeFrames': index,
                     'definition': definition, 'actualSourceDetailPages': pages, 'tracking': metrics})
    result = {'schemaVersion': 'deepseek-native-detail-proof-1', 'sources': rows,
              'workerSha256': helper['sha'](__file__), 'definitionsSha256': helper['sha'](definitions_file),
              'scope': 'All-frame unmodified source crops, including detector misses. No acceptance or actual-viewing claim.'}
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(output/'manifest.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--definitions', required=True, type=Path)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    prepare(args.directory, args.definitions, args.tag)
