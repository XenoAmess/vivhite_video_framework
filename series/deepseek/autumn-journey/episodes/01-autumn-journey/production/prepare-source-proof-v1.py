"""Prepare small viewing copies and every detected-face crop; never approve clips.

These are inspection artifacts, not generated replacement artwork. GPL-3.0-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageFont

EPISODE = Path(__file__).resolve().parent.parent


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def describe(file, count):
    return {'pathRelativeToEpisode': file.relative_to(EPISODE).as_posix(),
            'sha256': sha(file), 'items': count}


def sheet(entries, destination, cell=(150, 174), columns=8):
    picture = Image.new('RGB', (cell[0]*columns, cell[1]*math.ceil(len(entries)/columns)), '#242424')
    draw = ImageDraw.Draw(picture)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 14)
    for index, (image, label) in enumerate(entries):
        x, y = index % columns*cell[0], index//columns*cell[1]
        image.thumbnail((cell[0], cell[1]-24))
        picture.paste(image, (x, y+24))
        draw.text((x+3, y+3), label, font=font, fill='white')
    picture.save(destination)


def prepare(directory, ids, tag, regions_file):
    if not tag or any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in tag):
        raise ValueError('Use an episode-local stable tag')
    directory = directory.resolve()
    output = EPISODE/'assets/generated/production-v1-firstframes-001/review/viewing-copies'/tag
    output.mkdir(parents=True, exist_ok=True)
    definitions = json.loads(regions_file.read_text(encoding='utf-8')) if regions_file else {}
    rows = []
    cv2.setNumThreads(2)
    for sid in ids:
        report = json.loads((directory/'clip-inspection'/f'{sid}.json').read_text(encoding='utf-8'))
        source = directory/'sources'/f'{sid}.mp4'
        digest = sha(source)
        if digest != report['identity']['sourceSha256']:
            raise ValueError('Inspection report is stale for actual source')
        prefix = f'{sid}-{digest[:10]}'
        pages = []
        for item in report['allUsedFrameEvidence']:
            original = Path(item['path'])
            if sha(original) != item['sha256']:
                raise ValueError('Native thumbnail proof changed')
            target = output/original.name
            picture = Image.open(original)
            picture.thumbnail((1024, 1600))
            picture.save(target)
            pages.append({**describe(target, item['items']), 'parentSha256': item['sha256']})
        detected = {row['frame']: row['boxes'] for row in report['faceCandidateFrames']}
        candidates = []
        region_images = {definition['id']: [] for definition in definitions.get(sid, [])}
        capture = cv2.VideoCapture(str(source))
        index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                for box in detected.get(index, []):
                    x, y, width, height = [box[key] for key in ('x', 'y', 'width', 'height')]
                    margin = max(12, round(width*.5))
                    area = frame[max(0,y-margin):min(frame.shape[0],y+height+margin),
                                 max(0,x-margin):min(frame.shape[1],x+width+margin)]
                    candidates.append((Image.fromarray(cv2.cvtColor(area, cv2.COLOR_BGR2RGB)), f'f{index}'))
                for definition in definitions.get(sid, []):
                    left, top, right, bottom = definition['box']
                    if not (0 <= left < right <= frame.shape[1] and 0 <= top < bottom <= frame.shape[0]):
                        raise ValueError('Inspection region escaped actual source')
                    area = frame[top:bottom, left:right]
                    region_images[definition['id']].append((Image.fromarray(cv2.cvtColor(area, cv2.COLOR_BGR2RGB)), f'f{index}'))
                index += 1
        finally:
            capture.release()
        if index != report['decodedFrames']:
            raise ValueError('Full-source decode count changed')
        candidate_pages, region_pages = [], []
        for offset in range(0,len(candidates),48):
            entries = candidates[offset:offset+48]
            target = output/f'{prefix}-every-face-candidate-{offset//48+1:02}.png'
            sheet(entries, target)
            candidate_pages.append(describe(target, len(entries)))
        for region_id, entries in region_images.items():
            if any(character not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for character in region_id):
                raise ValueError('Use a stable region ID')
            for offset in range(0,len(entries),30):
                part = entries[offset:offset+30]
                target = output/f'{prefix}-{region_id}-all-{offset//30+1:02}.png'
                sheet(part, target, cell=(180,214), columns=6)
                region_pages.append({**describe(target,len(part)), 'regionId': region_id})
        rows.append({'id':sid, 'sourceSha256':digest, 'decodedNativeFrames':index,
                     'allFrameViewingCopies':pages, 'everyFaceCandidateSheets':candidate_pages,
                     'nativeRegionSheets':region_pages})
    manifest = {'schemaVersion':'deepseek-source-viewing-proof-1', 'sources':rows,
                'scope':'Inspection artifacts only. Every detector box is expanded; false positives and missed faces still require scene review. No actual-viewing or semantic acceptance claim.'}
    destination = output/'manifest.json'
    destination.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(destination)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--ids', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--regions', type=Path)
    args = parser.parse_args()
    prepare(args.directory, args.ids.split(','), args.tag, args.regions)
