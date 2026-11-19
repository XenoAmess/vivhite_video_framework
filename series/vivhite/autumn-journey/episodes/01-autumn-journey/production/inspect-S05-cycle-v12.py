"""Extract complete native768P cycle mechanics evidence; never edit or approve video.

GPL-3.0-only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def preserve(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve prior evidence; use another versioned destination')
    if not path.exists():
        path.write_bytes(data)


def picture(path, image):
    content = io.BytesIO()
    if path.suffix == '.jpg':
        image.save(content, format='JPEG', quality=95, subsampling=0)
    else:
        image.save(content, format='PNG')
    preserve(path, content.getvalue())
    return {'path': path.relative_to(EP).as_posix(), 'sha256': sha(path)}


def inspect(source, report_file, destination, regions):
    digest = sha(source)
    report = json.loads(report_file.read_text(encoding='utf-8'))
    if (report['identity']['sourceSha256'] != digest or report['shotId'] != 'S05'
            or report['decodedFrames'] != 120 or report['usedFramesAnalysed'] != 120):
        raise ValueError('Exact complete120-frame S05 report required')
    destination = destination.resolve()
    if not destination.is_relative_to(EP / 'assets/generated/production-v12-saddle-768p-001/review'):
        raise ValueError('Keep inspection images in the requested project run')
    for name, box in regions.items():
        if (not name.replace('-', '').isalnum() or len(box) != 4
                or not 0 <= box[0] < box[2] <= 1344 or not 0 <= box[1] < box[3] <= 768):
            raise ValueError('Named native boxes within1344x768 required')
    records = {'wholeScenePages': [], 'nativeWholeCheckpoints': [], 'regions': {},
               'candidateCrops': [], 'candidatePages': []}
    for index, entry in enumerate(report['allUsedFrameEvidence'], 1):
        original = Path(entry['path'])
        if sha(original) != entry['sha256']:
            raise ValueError('Whole-frame evidence changed')
        with Image.open(original) as image:
            target = destination / f'whole-p{index:02}.jpg'
            records['wholeScenePages'].append({**picture(target, image.convert('RGB')), 'items': entry['items']})
    if sum(row['items'] for row in records['wholeScenePages']) != 120:
        raise ValueError('Whole-scene pages do not cover all120frames')
    by_frame = {row['frame']: row['boxes'] for row in report['faceCandidateFrames']}
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
    crop_frames = {name: [] for name in regions}
    candidates = []
    capture = cv2.VideoCapture(str(source))
    count = 0
    try:
        if tuple(round(capture.get(key)) for key in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT)) != (1344, 768, 24, 120):
            raise ValueError('Actual native1344x768/24fps/120frames required')
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if count in (0, 24, 48, 72, 95, 119):
                records['nativeWholeCheckpoints'].append({**picture(destination / f'native-f{count:03}.png', rgb), 'frame': count})
            for name, box in regions.items():
                crop_frames[name].append(rgb.crop(box))
            for index, box in enumerate(by_frame.get(count, [])):
                margin = round(box['width'] * .4)
                area = [max(0, box['x']-margin), max(0, box['y']-margin),
                    min(1344, box['x']+box['width']+margin), min(768, box['y']+box['height']+margin)]
                if area[0] >= area[2] or area[1] >= area[3]:
                    raise ValueError('Candidate outside native frame')
                crop = rgb.crop(area)
                file = destination / 'candidates' / f'f{count:03}-b{index:02}.png'
                records['candidateCrops'].append({**picture(file, crop), 'frame': count,
                    'boxIndex': index, 'nativeBox': area, 'detectorBox': box})
                candidates.append((crop, f'f{count:03} b{index:02} {box["score"]:.3f}'))
            count += 1
    finally:
        capture.release()
    if count != 120 or sha(source) != digest:
        raise ValueError('Incomplete decoding or changed source')
    for name, crops in crop_frames.items():
        width, height = crops[0].size
        pages = []
        for offset in range(0, len(crops), 8):
            canvas = Image.new('RGB', (2*width, 4*(height+24)), '#242424')
            draw = ImageDraw.Draw(canvas)
            for index, crop in enumerate(crops[offset:offset+8]):
                x, y = index % 2 * width, index // 2 * (height+24)
                canvas.paste(crop, (x, y+24))
                draw.text((x+4, y+4), f'f{offset+index:03} | {(offset+index)/24:.3f}s', font=font, fill='white')
            native = destination / name / f'p{offset//8+1:02}.png'
            row = {**picture(native, canvas), 'firstFrame': offset,
                   'lastFrame': min(offset+7, 119), 'items': len(crops[offset:offset+8])}
            display = canvas.copy()
            display.thumbnail((1920, 2400), Image.Resampling.LANCZOS)
            row['viewingCopy'] = picture(native.with_suffix('.jpg'), display)
            pages.append(row)
        records['regions'][name] = {'nativeBox': regions[name], 'nativeFrames': 120,
            'framesPerPage': 8, 'originalPixelsOnly': True, 'pages': pages}
    for offset in range(0, len(candidates), 16):
        items = candidates[offset:offset+16]
        canvas = Image.new('RGB', (1536, ((len(items)+3)//4)*364), '#242424')
        draw = ImageDraw.Draw(canvas)
        for index, (crop, label) in enumerate(items):
            small = crop.copy()
            small.thumbnail((384, 336))
            x, y = index % 4 * 384, index // 4 * 364
            canvas.paste(small, (x, y+28))
            draw.text((x+4, y+4), label, font=font, fill='white')
        records['candidatePages'].append({**picture(destination / 'candidates' / f'p{offset//16+1:02}.jpg', canvas), 'items': len(items)})
    if len(records['candidateCrops']) != sum(len(row['boxes']) for row in report['faceCandidateFrames']):
        raise ValueError('Incomplete candidate crop export')
    result = {'schemaVersion': 'vivhite-cycle-native-region-inspection-1', 'sourceSha256': digest,
        'inspectionReportSha256': sha(report_file), 'workerSha256': sha(Path(__file__)),
        'nativeSize': [1344, 768], 'decodedFrames': count, **records,
        'scope': 'Extraction only; actual image viewing and semantic acceptance are separate.',
        'semanticAcceptance': False, 'humanContinuousPlayback': False}
    preserve(destination / 'manifest.json', (json.dumps(result, indent=2)+'\n').encode('utf-8'))
    print('All120 native frames/regions and all candidate boxes exported; no acceptance.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--region', required=True, action='append', nargs=5,
                        metavar=('NAME', 'X0', 'Y0', 'X1', 'Y1'))
    args = parser.parse_args()
    regions = {row[0]: [int(value) for value in row[1:]] for row in args.region}
    if len(regions) != len(args.region):
        raise ValueError('Unique region names required')
    inspect(args.source.resolve(), args.report.resolve(), args.destination.resolve(), regions)
