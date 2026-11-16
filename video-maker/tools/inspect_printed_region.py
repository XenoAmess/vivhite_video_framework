"""Extract tracked original pixels for visual inspection, without altering the video.

Tracking success supplies no semantic approval. GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path

import cv2
from PIL import Image,ImageDraw

from reference_finisher import sha,write_json
from stabilize_printed_patch import PrintedPatch


def inspect(source,evidence,identity,center,radius):
    evidence = Path(evidence).resolve()
    evidence.mkdir(parents=True,exist_ok=True)
    digest = sha(source)
    stem = f'{identity}-{digest[:10]}-tracked-print-region-v2'
    destination = evidence/(stem+'.png')
    if destination.exists():
        raise ValueError('Preserve the existing inspection; choose another identity')
    cap = cv2.VideoCapture(str(source))
    ok,frame = cap.read()
    if not ok:
        cap.release()
        raise ValueError('Cannot decode actual source')
    tracker = PrintedPatch(frame,center,radius)
    sheet = Image.new('RGB',(1680,2304),'#242424')
    draw = ImageDraw.Draw(sheet)
    metrics = []
    try:
        for index in range(120):
            if index:
                ok,frame = cap.read()
                if not ok:
                    raise ValueError('Source does not cover all 120 frames')
                # Reuse tested surface tracking. Discard the corrected buffer;
                # every saved pixel below comes from the unaltered original frame.
                _,metric = tracker.frame(frame)
            else:
                metric = {'center':list(center),'scale':1,'inliers':len(tracker.points)}
            x,y = metric['center']
            extent = round(radius*metric['scale']*1.3)
            area = frame[max(0,round(y)-extent):min(frame.shape[0],round(y)+extent),
                         max(0,round(x)-extent):min(frame.shape[1],round(x)+extent)]
            picture = Image.fromarray(cv2.cvtColor(area,cv2.COLOR_BGR2RGB)).resize((168,168))
            sheet.paste(picture,((index%10)*168,(index//10)*192+24))
            draw.text(((index%10)*168+3,(index//10)*192+4),f'f{index}',fill='white')
            metrics.append({'frame':index,**metric})
    finally:
        cap.release()
    sheet.save(destination)
    proxies = evidence/'proxies'
    proxies.mkdir(exist_ok=True)
    proxy = proxies/(stem+'.jpg')
    sheet.thumbnail((1248,2200))
    sheet.save(proxy,'JPEG',quality=90)
    write_json(evidence/(stem+'.json'),{'sourceSha256':digest,'frames':120,'center':list(center),
        'radius':radius,'originalVideoUnchanged':True,'semanticReview':'pending',
        'scope':'Tracked crops of original pixels only; no corrected frame or modified video is saved.',
        'images':[{'path':p.relative_to(evidence).as_posix(),'sha256':sha(p)} for p in (destination,proxy)],
        'tracking':metrics})
    print(json.dumps({'png':str(destination),'proxy':str(proxy),'frames':120}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--identity',required=True)
    parser.add_argument('--center',required=True,type=int,nargs=2)
    parser.add_argument('--radius',required=True,type=int)
    args = parser.parse_args()
    inspect(args.source,args.evidence,args.identity,tuple(args.center),args.radius)
