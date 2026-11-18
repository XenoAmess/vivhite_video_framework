"""Export every detector box from a bound, complete native UHD source report.

Read-only inspection: candidates are not people or semantic decisions.
GPL-3.0-only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def preserve(path, content):
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f'Existing inspection evidence differs: {path.name}')
    else:
        path.write_bytes(content)


def export(source, report_file, destination):
    report = json.loads(report_file.read_text(encoding='utf-8'))
    digest = sha(source)
    if report['identity']['sourceSha256'] != digest or report['status'] != 'decoded':
        raise ValueError('Report does not describe the exact actual source')
    count = report['usedFramesAnalysed']
    if count not in (120, 240, 336) or report['decodedFrames'] != count:
        raise ValueError('Complete source report required')
    identity = report['shotId']
    if len(identity) != 3 or identity[0] != 'S' or not identity[1:].isdigit():
        raise ValueError('Invalid shot identity')
    rows = report['faceCandidateFrames']
    if any(not row['used'] or not 0 <= row['frame'] < count for row in rows):
        raise ValueError('Candidate lies outside the complete source')
    if len({row['frame'] for row in rows}) != len(rows):
        raise ValueError('Duplicate candidate frame')
    by_frame = {row['frame']: row['boxes'] for row in rows}
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError('Cannot open source')
    destination.mkdir(parents=True, exist_ok=True)
    stem = f'{identity}-{digest[:10]}-all-candidates'
    pictures, records, pages = [], [], []
    decoded = 0
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    try:
        if tuple(round(capture.get(key)) for key in (
                cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT)) != (3840, 2160, 24, count):
            raise ValueError('Expected complete native 3840x2160 24fps source')
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            for index, box in enumerate(by_frame.get(decoded, [])):
                x, y, width, height = (box[key] for key in ('x', 'y', 'width', 'height'))
                if width <= 0 or height <= 0:
                    raise ValueError('Invalid candidate dimensions')
                margin = round(width * .4)
                area = [max(0, x-margin), max(0, y-margin),
                        min(3840, x+width+margin), min(2160, y+height+margin)]
                if area[2] <= area[0] or area[3] <= area[1]:
                    raise ValueError('Candidate does not intersect the actual frame')
                picture = Image.fromarray(cv2.cvtColor(
                    frame[area[1]:area[3], area[0]:area[2]], cv2.COLOR_BGR2RGB))
                path = destination/f'{stem}-f{decoded:03}-b{index:02}.png'
                buffer = io.BytesIO()
                picture.save(buffer, format='PNG')
                preserve(path, buffer.getvalue())
                label = f'{identity} f{decoded:03} b{index:02} {box["score"]:.3f}'
                pictures.append((picture, label))
                records.append({'frame':decoded, 'boxIndex':index, 'detectorBox':box,
                                'nativeCrop':area, 'path':path.name, 'sha256':sha(path)})
            decoded += 1
    finally:
        capture.release()
    if decoded != count or len(records) != sum(len(row['boxes']) for row in rows):
        raise ValueError('Incomplete actual decoding or candidate export')
    for offset in range(0, len(pictures), 16):
        items = pictures[offset:offset+16]
        canvas = Image.new('RGB', (1536, ((len(items)+3)//4)*364), '#242424')
        draw = ImageDraw.Draw(canvas)
        for index, (picture, label) in enumerate(items):
            x, y = index%4*384, index//4*364
            small = picture.copy()
            small.thumbnail((384, 336))
            canvas.paste(small, (x+(384-small.width)//2, y+28))
            draw.text((x+4, y+4), label, font=font, fill='white')
        path = destination/f'{stem}-p{offset//16+1:02}.jpg'
        buffer = io.BytesIO()
        canvas.save(buffer, format='JPEG', quality=94, subsampling=0)
        preserve(path, buffer.getvalue())
        pages.append({'path':path.name, 'sha256':sha(path), 'items':len(items)})
    receipt = {'schemaVersion':'vivhite-all-native-candidate-crops-1', 'shotId':identity,
               'sourceSha256':digest, 'inspectionReportSha256':sha(report_file),
               'workerSha256':sha(__file__), 'nativeSize':[3840,2160], 'fps':24,
               'decodedFrames':decoded, 'candidateFrames':len(rows), 'candidateBoxes':len(records),
               'nativeCrops':records, 'viewingPages':pages,
               'scope':'All detector boxes exported. Exported does not mean viewed or semantically approved.',
               'humanFullPlayback':False, 'semanticDecision':'not-automatically-decided'}
    preserve(destination/f'{stem}.json',
             (json.dumps(receipt, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    print(f'{identity}: {decoded} frames decoded, {len(records)} native crops, {len(pages)} viewing pages')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    arguments = parser.parse_args()
    export(arguments.source, arguments.report, arguments.destination)
