"""Read-only tracked native-video crops, including detector-missed print frames.

The tracking helper's composited return is discarded: proof always shows actual
unmodified input pixels. No source approval is granted. GPL-3.0-only.
"""
import argparse
import hashlib
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


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def prepare(directory, definitions, tag):
    if not tag or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in tag):
        raise ValueError('Use a stable episode-local review tag')
    directory = directory.resolve()
    definitions = json.loads(definitions.read_text(encoding='utf-8'))
    output = EPISODE/'assets/generated/production-v1-firstframes-001/review/viewing-copies'/tag
    output.mkdir(parents=True, exist_ok=True)
    helper = runpy.run_path(str(EPISODE/'production/prepare-source-proof-v1.py'))
    cv2.setNumThreads(2)
    rows = []
    for sid, definition in definitions.items():
        source = directory/'sources'/f'{sid}.mp4'
        report = json.loads((directory/'clip-inspection'/f'{sid}.json').read_text(encoding='utf-8'))
        digest = sha(source)
        if digest != report['identity']['sourceSha256']:
            raise ValueError('Actual source differs from inspected source')
        capture = cv2.VideoCapture(str(source))
        entries, metrics = [], []
        try:
            ok, first = capture.read()
            if not ok:
                raise ValueError('Cannot read actual source')
            tracker = PrintedPatch(first, tuple(definition['center']), definition['trackingRadius'])
            index, frame = 0, first
            while True:
                if index == 0:
                    metric = {'center': definition['center'], 'scale': 1.0}
                else:
                    _, metric = tracker.frame(frame)
                x, y = metric['center']
                radius = definition['cropRadius']*metric['scale']
                left, top = max(0,round(x-radius)), max(0,round(y-radius))
                right, bottom = min(frame.shape[1],round(x+radius)), min(frame.shape[0],round(y+radius))
                area = frame[top:bottom, left:right]
                entries.append((Image.fromarray(cv2.cvtColor(area,cv2.COLOR_BGR2RGB)), f'f{index}'))
                metrics.append({'frame':index, **metric, 'actualNativeBounds':[left,top,right,bottom]})
                index += 1
                ok, frame = capture.read()
                if not ok:
                    break
        finally:
            capture.release()
        if index != report['decodedFrames']:
            raise ValueError('Complete actual-source frame count changed')
        pages = []
        for offset in range(0,len(entries),30):
            part = entries[offset:offset+30]
            file = output/f'{sid}-{digest[:10]}-native-tracked-print-{offset//30+1:02}.png'
            helper['sheet'](part,file,cell=(180,204),columns=6)
            pages.append(helper['describe'](file,len(part)))
        rows.append({'id':sid,'sourceSha256':digest,'decodedNativeFrames':index,
                     'definition':definition,'actualSourceCropPages':pages,'tracking':metrics})
    result = {'schemaVersion':'deepseek-tracked-native-proof-1','sources':rows,
              'workerSha256':sha(__file__),'trackerWorkerSha256':sha(ROOT/'video-maker/tools/stabilize_printed_patch.py'),
              'scope':'Actual unmodified video pixels at tracked print location, all decoded frames including detector misses. Proof generation only; actual viewing and acceptance are separate.'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(output/'manifest.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--definitions',required=True,type=Path)
    parser.add_argument('--tag',required=True)
    args = parser.parse_args()
    prepare(args.directory,args.definitions,args.tag)
