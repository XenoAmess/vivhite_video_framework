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


def inspect(source,evidence,identity,center,radius,max_scale=2.5,frame_count=120):
    if frame_count not in (120,240):
        raise ValueError('Inspection must cover a complete five- or ten-second source')
    evidence = Path(evidence).resolve()
    evidence.mkdir(parents=True,exist_ok=True)
    digest = sha(source)
    stem = f'{identity}-{digest[:10]}-tracked-print-region-v2'
    destinations = [evidence/(stem+(f'-p{index+1:02}' if frame_count>120 else '')+'.png')
                    for index in range(frame_count//120)]
    if any(path.exists() for path in destinations):
        raise ValueError('Preserve the existing inspection; choose another identity')
    cap = cv2.VideoCapture(str(source))
    ok,frame = cap.read()
    if not ok:
        cap.release()
        raise ValueError('Cannot decode actual source')
    try:
        tracker = PrintedPatch(frame,center,radius,max_scale)
    except Exception:
        cap.release()
        raise
    sheets = [Image.new('RGB',(1680,2304),'#242424') for _ in destinations]
    metrics = []
    try:
        for index in range(frame_count):
            if index:
                ok,frame = cap.read()
                if not ok:
                    raise ValueError(f'Source does not cover all {frame_count} frames')
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
            sheet = sheets[index//120]
            local_index = index%120
            sheet.paste(picture,((local_index%10)*168,(local_index//10)*192+24))
            ImageDraw.Draw(sheet).text(((local_index%10)*168+3,(local_index//10)*192+4),f'f{index}',fill='white')
            metrics.append({'frame':index,**metric})
    finally:
        cap.release()
    proxies = evidence/'proxies'
    proxies.mkdir(exist_ok=True)
    images = []
    for sheet,destination in zip(sheets,destinations):
        sheet.save(destination)
        proxy = proxies/(destination.stem+'.jpg')
        sheet.thumbnail((1248,2200))
        sheet.save(proxy,'JPEG',quality=90)
        images.extend((destination,proxy))
    write_json(evidence/(stem+'.json'),{'sourceSha256':digest,'frames':frame_count,'center':list(center),
        'radius':radius,'maximumTrackedScale':max_scale,
        'workerSha256':sha(__file__),
        'trackingWorkerSha256':sha(Path(__file__).with_name('stabilize_printed_patch.py')),
        'originalVideoUnchanged':True,'semanticReview':'pending',
        'scope':'Tracked crops of original pixels only; no corrected frame or modified video is saved.',
        'images':[{'path':p.relative_to(evidence).as_posix(),'sha256':sha(p)} for p in images],
        'tracking':metrics})
    print(json.dumps({'images':[str(path) for path in images],'frames':frame_count}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--evidence',required=True,type=Path)
    parser.add_argument('--identity',required=True)
    parser.add_argument('--center',required=True,type=int,nargs=2)
    parser.add_argument('--radius',required=True,type=int)
    parser.add_argument('--max-scale',type=float,default=2.5)
    parser.add_argument('--frames',type=int,choices=(120,240),default=120)
    args = parser.parse_args()
    inspect(args.source,args.evidence,args.identity,tuple(args.center),args.radius,args.max_scale,args.frames)
