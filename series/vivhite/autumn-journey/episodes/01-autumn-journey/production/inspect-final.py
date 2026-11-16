"""Inspect the 202-second episode against its already-reviewed selected picture.

GPL-3.0-only. This script reports evidence and never grants semantic approval.
"""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plan', required=True, type=Path)
parser.add_argument('--directory', required=True, type=Path)
parser.add_argument('--evidence', required=True, type=Path)
parser.add_argument('--face-model', required=True, type=Path)
args = parser.parse_args()
EP = args.plan.resolve().parent
PUBLIC = EP.parents[4]
RUN = args.directory.resolve()
EVIDENCE = args.evidence.resolve()
if not EVIDENCE.is_relative_to(EP):
    raise ValueError('This task saves all inspection pictures inside its episode')
EVIDENCE.mkdir(parents=True, exist_ok=True)
plan = json.loads(args.plan.read_text(encoding='utf-8'))
if plan['totalFrames'] != 6060 or plan['fps'] != 30:
    raise ValueError('This episode-specific inspection uses the reviewed 202-second title/fade timing')
film = RUN / 'film.mp4'
model = args.face_model.resolve()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def evidence_sheet(items, filename, columns=4, cell=(416,258)):
    if not items:
        return None
    destination = EVIDENCE / filename
    canvas = Image.new('RGB', (columns*cell[0], math.ceil(len(items)/columns)*cell[1]), '#242424')
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 16)
    for index, (picture, label) in enumerate(items):
        picture = picture.copy()
        picture.thumbnail((cell[0], cell[1]-24))
        x, y = index % columns*cell[0], index//columns*cell[1]
        canvas.paste(picture, (x+(cell[0]-picture.width)//2, y+24))
        draw.text((x+4, y+3), label, font=font, fill='white')
    canvas.save(destination)
    return {'path': str(destination.relative_to(PUBLIC)), 'sha256': sha(destination), 'items': len(items)}


caps = [cv2.VideoCapture(str(path)) for path in (film, RUN / plan['pictureFile'])]
assert all(cap.isOpened() for cap in caps)
cv2.setNumThreads(2)
detector = cv2.FaceDetectorYN.create(str(model), '', (832,468), .6, .3, 5000)
midpoints = {shot['startFrame']+shot['seconds']*15: shot['id'] for shot in plan['shots']}
special = {600:'title-before', 621:'title-in', 650:'title-visible', 710:'title-out',
           5880:'closing-before', 5901:'closing-in', 5940:'closing-visible',
           6027:'closing-before-fade', 6042:'closing-fade', 6059:'last-frame'}
samples, candidates, metrics, details = [], {}, [], []
count = 0
started = time.monotonic()
try:
    while True:
        ok, frame = caps[0].read()
        original_ok, original = caps[1].read()
        if not ok:
            if original_ok:
                raise ValueError('Encoded film lost selected picture frames')
            break
        if not original_ok:
            raise ValueError('Encoded film gained picture frames')
        sid = next(shot['id'] for shot in reversed(plan['shots']) if count >= shot['startFrame'])
        small = cv2.resize(frame, (832,468))
        original_small = cv2.resize(original, (832,468))
        # Mask only known typographic bounds; no scene imagery is replaced there.
        mask = np.ones((468,832), dtype=bool)
        if 612 <= count <= 709 or 5892 <= count <= 6049:
            mask[36:132, 38:810] = False
        if count >= 6036:
            factor = max(0, (6060-count)/24)
            original_small = np.clip(original_small.astype(np.float32)*factor, 0,255).astype(np.uint8)
        diff = small.astype(np.float32)-original_small.astype(np.float32)
        mse = float(np.mean(diff[mask]**2))
        psnr = 99 if mse == 0 else 10*math.log10(255**2/mse)
        _, faces = detector.detect(small)
        boxes = []
        if faces is not None:
            for face in faces:
                x,y,w,h = [int(value) for value in face[:4]]
                boxes.append({'x':x,'y':y,'width':w,'height':h,'score':round(float(face[-1]),5)})
            if count >= candidates.get(sid, {'nextFrame':0})['nextFrame']:
                row = candidates.setdefault(sid, {'nextFrame':0,'crops':[]})
                for box in boxes:
                    x,y,w,h = [box[key] for key in ('x','y','width','height')]
                    margin = round(w*.4)
                    crop = small[max(0,y-margin):min(468,y+h+margin), max(0,x-margin):min(832,x+w+margin)]
                    if crop.size:
                        row['crops'].append((Image.fromarray(cv2.cvtColor(crop,cv2.COLOR_BGR2RGB)),f'{sid} f{count}'))
                row['nextFrame'] = count+15
        if count in midpoints:
            samples.append((Image.fromarray(cv2.cvtColor(small,cv2.COLOR_BGR2RGB)),f'{midpoints[count]} | {count/30:.2f}s'))
        if count in special:
            out = EVIDENCE / f'{count:04}-{special[count]}.png'
            cv2.imwrite(str(out), frame)
            details.append({'frame':count,'path':str(out.relative_to(PUBLIC)),'sha256':sha(out)})
        metrics.append({'frame':count,'shotId':sid,'outsideTitlePsnrDb':round(psnr,3),'faceCandidates':boxes})
        count += 1
        if count % 600 == 0:
            print(f'Encoded-frame inspection {count}/{plan["totalFrames"]} ({100*count/plan["totalFrames"]:.1f}%)',flush=True)
finally:
    for cap in caps:
        cap.release()
assert count == plan['totalFrames']
(RUN / 'final-frame-metrics-v2.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in metrics), encoding='utf-8')
sheets = [evidence_sheet(samples[offset:offset+8],f'shots-{offset+1:02}-{min(offset+8,48):02}.png') for offset in range(0,48,8)]
candidate_sheets = [evidence_sheet(row['crops'], f'{sid}-final-candidates.png',columns=5,cell=(208,220)) for sid,row in sorted(candidates.items())]
report = {'schemaVersion':'vivhite-encoded-film-inspection-1','filmSha256':sha(film),
    'selectedPictureSha256':sha(RUN / plan['pictureFile']), 'workerSha256':sha(__file__),
    'decodedAndComparedFrames':count,'faceDetectorFrames':count,'faceModelSha256':sha(model),
    'faceScoreThreshold':.6,'candidateFrames':sum(bool(row['faceCandidates']) for row in metrics),
    'minimumOutsideTitlePsnrDb':min(row['outsideTitlePsnrDb'] for row in metrics),
    'lowSimilarityFrames':[row for row in metrics if row['outsideTitlePsnrDb']<30],
    'shotEvidence':sheets,'titleFadeEvidence':details,'candidateEvidence':candidate_sheets,
    'machineCoverage':'All final frames decoded, compared with the selected picture and passed through YuNet; candidate evidence uses 0.5-second spacing.',
    'semanticReview':'Separate assistant interpretation required; not automatically approved.',
    'humanFullPlayback':False,'elapsedSeconds':round(time.monotonic()-started,3)}
(RUN / 'encoded-film-inspection-v2.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({key:report[key] for key in ('decodedAndComparedFrames','candidateFrames','minimumOutsideTitlePsnrDb','elapsedSeconds')}),flush=True)
