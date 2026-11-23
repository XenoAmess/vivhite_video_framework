"""Native source inspection and ordered scene/detail sheets; never approve. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
from review_reference_clips import inspect


def prepare(directory, ids, tag, regions):
    if not tag or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in tag):
        raise ValueError('Stable local tag required')
    evidence = EPISODE/'assets/generated/production-v3-firstframes-001/review'/tag
    evidence.mkdir(parents=True, exist_ok=True)
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    rows = []
    for sid in ids:
        source = directory/'sources'/f'{sid}.mp4'
        report = directory/'clip-inspection'/f'{sid}.json'
        if not report.exists():
            inspect(source, {'id': sid, 'seconds': 5}, evidence/'native-machine-proof',
                    directory/'clip-inspection', ROOT.parent/'vivhite-analysis-output/models/opencv-yunet-2023mar/face_detection_yunet_2023mar.onnx')
        report_data = json.loads(report.read_text(encoding='utf-8'))
        if report_data['identity']['sourceSha256'] != sha(source):
            raise ValueError('Actual source changed')
        cap, frames = cv2.VideoCapture(str(source)), []
        try:
            while True:
                ok, pixels = cap.read()
                if not ok:
                    break
                frames.append(Image.fromarray(cv2.cvtColor(pixels, cv2.COLOR_BGR2RGB)))
        finally:
            cap.release()
        if len(frames) != report_data['decodedFrames']:
            raise ValueError('Incomplete native source decoding')
        artifacts = []
        for page in range((len(frames)+31)//32):
            part = frames[page*32:(page+1)*32]
            sheet = Image.new('RGB', (1024, 8*169), '#222')
            draw = ImageDraw.Draw(sheet)
            for n, picture in enumerate(part):
                x, y = n % 4*256, n//4*169
                sheet.paste(picture.resize((256, 146)), (x, y+23))
                draw.text((x+3, y+4), f'f{page*32+n}', fill='white')
            target = evidence/f'{sid}-all-{page+1}.jpg'
            sheet.save(target, quality=95)
            artifacts.append({'path': target.relative_to(EPISODE).as_posix(), 'sha256': sha(target), 'items': len(part)})
        for region_id, box in regions.get(sid, {}).items():
            sheet = Image.new('RGB', (1200, 177*((len(frames)+11)//12)), '#222')
            draw = ImageDraw.Draw(sheet)
            for i, picture in enumerate(frames):
                crop = picture.crop(box)
                crop.thumbnail((100, 151))
                x, y = i % 12*100, i//12*177
                sheet.paste(crop, (x, y+22))
                draw.text((x+2, y+3), str(i), fill='white')
            target = evidence/f'{sid}-{region_id}-all{len(frames)}.jpg'
            sheet.save(target, quality=97)
            artifacts.append({'path': target.relative_to(EPISODE).as_posix(), 'sha256': sha(target), 'items': len(frames), 'nativeBox': box})
        for index in sorted(set([0, 24, 48, 60, 72, 96, len(frames)-1])):
            target = evidence/f'{sid}-f{index:03d}-native.png'
            frames[index].save(target)
            artifacts.append({'path': target.relative_to(EPISODE).as_posix(), 'sha256': sha(target), 'frame': index})
        rows.append({'id': sid, 'sourceSha256': sha(source), 'frames': len(frames), 'artifacts': artifacts})
    (evidence/'manifest.json').write_text(json.dumps({'schemaVersion': 'deepseek-source-proof-3',
        'sources': rows, 'workerSha256': sha(__file__), 'actualAssistantViewing': False,
        'scope': 'Unmodified decoded source pixels, in order. Sheet production never supplies semantic approval.'}, indent=2)+'\n', encoding='utf-8')
    print(evidence, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--ids', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--regions', type=Path)
    args = parser.parse_args()
    prepare(args.directory.resolve(), args.ids.split(','), args.tag,
            json.loads(args.regions.read_text(encoding='utf-8')) if args.regions else {})
