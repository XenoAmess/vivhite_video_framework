"""Preserve every encoded frame in bound viewing pages; never grant approval.

GPL-3.0-only. Read-only video extraction; no interpolation or AI enhancement.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def preserve(path, content):
    if path.exists() and path.read_bytes() != content:
        raise ValueError('Existing evidence differs; choose a new destination')
    if not path.exists():
        path.write_bytes(content)


def extract(film, inspection_file, destination):
    film, inspection_file, destination = map(Path.resolve, (film, inspection_file, destination))
    if not destination.is_relative_to(EP):
        raise ValueError('Preserve inspection images inside this episode')
    report = json.loads(inspection_file.read_text(encoding='utf-8'))
    digest = sha(film)
    expected = report['decodedAndComparedFrames']
    if digest != report['filmSha256'] or report['lowSimilarityFrames'] or expected <= 0:
        raise ValueError('Require a bound, completely decoded and compared film')
    destination.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(film))
    pages = []
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    count = 0
    try:
        if not cap.isOpened() or (
                round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                cap.get(cv2.CAP_PROP_FPS),
                round(cap.get(cv2.CAP_PROP_FRAME_COUNT))) != (3840, 2160, 30.0, expected):
            raise ValueError('Require actual UHD / 30fps and the inspected frame count')
        while count < expected:
            start = count
            items = min(32, expected - count)
            canvas = Image.new('RGB', (1664, ((items + 3) // 4) * 258), '#242424')
            draw = ImageDraw.Draw(canvas)
            for item in range(items):
                ok, frame = cap.read()
                if not ok or frame.shape[:2] != (2160, 3840):
                    raise ValueError('Incomplete native video decode')
                small = cv2.resize(frame, (416, 234), interpolation=cv2.INTER_AREA)
                x, y = (item % 4) * 416, (item // 4) * 258
                canvas.paste(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)), (x, y + 24))
                draw.text((x + 4, y + 3), f'f{count:04} | {count / 30:.3f}s', font=font, fill='white')
                count += 1
            target = destination / f'{digest[:10]}-whole-p{len(pages) + 1:03}.jpg'
            buffer = BytesIO()
            canvas.save(buffer, format='JPEG', quality=94)
            preserve(target, buffer.getvalue())
            pages.append({'path':target.relative_to(EP).as_posix(), 'sha256':sha(target),
                'firstFrame':start, 'lastFrame':count - 1, 'items':items})
        if cap.read()[0]:
            raise ValueError('Additional frames beyond the inspected duration')
    finally:
        cap.release()
    if count != expected or sha(film) != digest or sum(p['items'] for p in pages) != expected:
        raise ValueError('Full unchanged film coverage required')
    manifest = {'schemaVersion':'vivhite-encoded-whole-frame-viewing-pages-1',
        'filmSha256':digest, 'inspectionSha256':sha(inspection_file), 'workerSha256':sha(__file__),
        'nativeSize':[3840,2160], 'fps':30, 'decodedAndRepresentedFrames':count,
        'displayFrameSize':[416,234], 'displayOnlyResampling':'area downsampling, no AI enhancement',
        'pages':pages, 'semanticApproval':'not-granted-by-extraction',
        'humanContinuousPlayback':False, 'scope':'Every frame represented; export alone is not actual review.'}
    preserve(destination / f'{digest[:10]}-whole.json',
        (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
    print(f'{count} encoded frames represented through {len(pages)} pages; no approval granted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--film', required=True, type=Path)
    parser.add_argument('--inspection', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    extract(args.film, args.inspection, args.destination)
