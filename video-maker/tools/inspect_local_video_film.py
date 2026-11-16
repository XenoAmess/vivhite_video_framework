"""Inspect all encoded frames against selected picture, with explicit evidence bounds.

The detector and picture comparison never grant semantic acceptance. GPL-3.0-only.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image,ImageDraw,ImageFont

from reference_finisher import sha,write_json,output_dimensions


def inspect(plan_file,directory,evidence,face_model):
    plan_file,directory,evidence = Path(plan_file).resolve(),Path(directory).resolve(),Path(evidence).resolve()
    episode = plan_file.parent
    if not evidence.is_relative_to(episode):
        raise ValueError('Save this project inspection imagery inside its episode')
    evidence.mkdir(parents=True,exist_ok=True)
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    width,height = output_dimensions(plan)
    total,fps = plan['totalFrames'],plan['fps']
    if fps != 30 or any(not 2 <= s['seconds'] <= 5 for s in plan['shots']):
        raise ValueError('Expected the reviewed five-second-maximum cut')
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    caps = [cv2.VideoCapture(str(path)) for path in (directory/'film.mp4',directory/plan['pictureFile'])]
    if not all(cap.isOpened() for cap in caps):
        raise ValueError('Both actual final film and selected picture are required')
    for cap in caps:
        if (round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (width,height):
            raise ValueError('Actual encoded dimensions differ from reviewed plan')
    cv2.setNumThreads(2)
    detector = cv2.FaceDetectorYN.create(str(face_model),'',(832,468),.6,.3,5000)
    starts = [s['startFrame'] for s in plan['shots']]
    title_shots = [next(s for s in plan['shots'] if s['id']==o['shotId']) for o in plan['titleOverlays']]
    title_ranges = [(s['startFrame']+12,s['startFrame']+s['seconds']*30-10) for s in title_shots]
    midpoints = {s['startFrame']+s['seconds']*15:s['id'] for s in plan['shots']}
    specials = {total-1:'last-frame',total-12:'closing-fade'}
    for shot in title_shots:
        for offset,label in ((0,'before'),(21,'in'),(60,'visible'),(shot['seconds']*30-16,'out')):
            specials[shot['startFrame']+offset] = shot['id']+'-'+label
    metrics,samples,details,candidates = [],[],[],{}
    next_candidate = {}
    count = 0
    began = time.monotonic()
    fade_frames = round(plan['closingFadeSeconds']*fps)
    try:
        while True:
            ok,frame = caps[0].read()
            original_ok,original = caps[1].read()
            if not ok:
                if original_ok:
                    raise ValueError('Final film lost selected frames')
                break
            if not original_ok:
                raise ValueError('Final film gained frames')
            shot = plan['shots'][bisect.bisect_right(starts,count)-1]
            identity = shot['id']
            small = cv2.resize(frame,(832,468))
            reference = cv2.resize(original,(832,468))
            mask = np.ones((468,832),dtype=bool)
            if any(begin <= count <= end for begin,end in title_ranges):
                mask[35:132,35:810] = False
            if count >= total-fade_frames:
                factor = max(0,(total-count)/fade_frames)
                reference = np.clip(reference.astype(np.float32)*factor,0,255).astype(np.uint8)
            difference = small.astype(np.float32)-reference.astype(np.float32)
            mse = float(np.mean(difference[mask]**2))
            psnr = 99 if mse == 0 else 10*math.log10(255**2/mse)
            _,found = detector.detect(small)
            boxes = []
            if found is not None:
                for face in found:
                    x,y,w,h = [int(value) for value in face[:4]]
                    boxes.append({'x':x,'y':y,'width':w,'height':h,'score':round(float(face[-1]),5)})
                if count >= next_candidate.get(identity,0):
                    for box in boxes:
                        x,y,w,h = [box[key] for key in ('x','y','width','height')]
                        margin = round(w*.4)
                        area = small[max(0,y-margin):min(468,y+h+margin),max(0,x-margin):min(832,x+w+margin)]
                        if area.size:
                            candidates.setdefault(identity,[]).append((Image.fromarray(cv2.cvtColor(area,cv2.COLOR_BGR2RGB)),f'{identity} f{count}'))
                    next_candidate[identity] = count+15
            if count in midpoints:
                samples.append((Image.fromarray(cv2.cvtColor(small,cv2.COLOR_BGR2RGB)),f'{identity} | {count/fps:.2f}s'))
            if count in specials:
                target = evidence/f'{count:04}-{specials[count]}.png'
                cv2.imwrite(str(target),frame)
                details.append({'frame':count,'path':target.relative_to(episode).as_posix(),'sha256':sha(target)})
            metrics.append({'frame':count,'shotId':identity,'outsideTitlePsnrDb':round(psnr,3),'faceCandidates':boxes})
            count += 1
            if count % 600 == 0:
                print(f'Final frame inspection {count}/{total} ({100*count/total:.1f}%)',flush=True)
    finally:
        for cap in caps:
            cap.release()
    if count != total:
        raise ValueError('Final decoded frame count mismatch')

    def sheet(items,name,columns=4,cell=(416,258)):
        target = evidence/name
        canvas = Image.new('RGB',(columns*cell[0],math.ceil(len(items)/columns)*cell[1]),'#242424')
        draw = ImageDraw.Draw(canvas)
        for index,(picture,label) in enumerate(items):
            picture = picture.copy()
            picture.thumbnail((cell[0],cell[1]-24))
            x,y = index%columns*cell[0],index//columns*cell[1]
            canvas.paste(picture,(x+(cell[0]-picture.width)//2,y+24))
            draw.text((x+4,y+3),label,font=font,fill='white')
        canvas.save(target)
        return {'path':target.relative_to(episode).as_posix(),'sha256':sha(target),'items':len(items)}

    shot_sheets = [sheet(samples[offset:offset+8],f'shots-{offset+1:02}-{min(offset+8,len(samples)):02}.png')
                   for offset in range(0,len(samples),8)]
    candidate_sheets = [sheet(items,identity+'-final-candidates.png',columns=5,cell=(208,220))
                        for identity,items in sorted(candidates.items())]
    (directory/'final-frame-metrics.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in metrics),encoding='utf-8',newline='\n')
    report = {'schemaVersion':'vivhite-encoded-film-inspection-2','filmSha256':sha(directory/'film.mp4'),
        'selectedPictureSha256':sha(directory/plan['pictureFile']),'planSha256':sha(plan_file),'workerSha256':sha(__file__),
        'width':width,'height':height,'fps':fps,'decodedAndComparedFrames':count,'faceDetectorFrames':count,
        'faceDetectorInputSize':[832,468],'faceModelSha256':sha(face_model),'faceScoreThreshold':.6,
        'minimumOutsideTitlePsnrDb':min(row['outsideTitlePsnrDb'] for row in metrics),
        'lowSimilarityFrames':[row for row in metrics if row['outsideTitlePsnrDb']<30],
        'candidateFrames':sum(bool(row['faceCandidates']) for row in metrics),'candidateEvidence':candidate_sheets,
        'shotEvidence':shot_sheets,'titleFadeEvidence':details,
        'machineCoverage':'All final frames decoded, compared with selected picture outside known title bounds, and passed through the stated face detector. Source clips have separate native-size inspections.',
        'semanticReview':'Separate all-source-frame and candidate interpretation required; never automatically approved.',
        'humanFullPlayback':False,'elapsedSeconds':round(time.monotonic()-began,3)}
    write_json(directory/'encoded-film-inspection.json',report)
    print(json.dumps({key:report[key] for key in ('decodedAndComparedFrames','minimumOutsideTitlePsnrDb','candidateFrames','elapsedSeconds')}),flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan','directory','evidence','face-model'):
        parser.add_argument('--'+name,required=True,type=Path)
    args = parser.parse_args()
    inspect(args.plan,args.directory,args.evidence,args.face_model)
