"""Track on a small proxy, save unaltered native UHD print pixels for review.

No video is edited and no semantic decision is produced. GPL-3.0-only.
"""
import argparse
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from reference_finisher import sha
from stabilize_printed_patch import PrintedPatch


def preserve(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes() != content:
        raise ValueError('Preserve earlier evidence; use another region identity')
    if not path.exists():
        path.write_bytes(content)


def save_image(path, picture, jpeg=False):
    buffer = BytesIO()
    picture.save(buffer,format='JPEG' if jpeg else 'PNG',**({'quality':94} if jpeg else {}))
    preserve(path,buffer.getvalue())


def inspect(source, identity, center, radius, frame_count, max_scale):
    if not re.fullmatch(r'S\d{2}-[a-z0-9-]+',identity) or frame_count not in (120,240,336):
        raise ValueError('Use an explicit UHD region and complete source interval')
    source = Path(source).resolve()
    digest = sha(source)
    evidence = EP/'assets/generated/production-v11-native-4k-001/review/print'
    cap = cv2.VideoCapture(str(source))
    count = 0
    items, tracking = [], []
    native_evidence = []
    try:
        if (round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                round(cap.get(cv2.CAP_PROP_FPS))) != (3840,2160,24):
            raise ValueError('Actual native 3840x2160 at 24fps source required')
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            proxy = cv2.resize(frame,(1344,768))
            if count == 0:
                tracker = PrintedPatch(proxy,center,radius,max_scale)
                metric = {'center':list(center),'scale':1,'inliers':len(tracker.points)}
            else:
                # Its corrected proxy is discarded. Saved pixels always come
                # directly from this unmodified native source frame.
                _, metric = tracker.frame(proxy)
            x,y = metric['center']
            extent = radius*metric['scale']*1.3
            wanted = [math.floor((x-extent)*3840/1344),math.floor((y-extent)*2160/768),
                      math.ceil((x+extent)*3840/1344),math.ceil((y+extent)*2160/768)]
            box = [max(0,wanted[0]),max(0,wanted[1]),min(3840,wanted[2]),min(2160,wanted[3])]
            if box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError('Tracked print left the frame; inspect native context separately')
            picture = Image.fromarray(cv2.cvtColor(frame[box[1]:box[3],box[0]:box[2]],cv2.COLOR_BGR2RGB))
            items.append(picture)
            tracking.append({'frame':count,**metric,'nativeBox':box,'frameEdgeClipped':box != wanted})
            if count in (0,24,48,72,95,119,167,239,287,335):
                path = evidence/f'{identity}-{digest[:10]}-native-f{count:03}.png'
                save_image(path,picture)
                native_evidence.append({'frame':count,'path':path.relative_to(EP).as_posix(),'sha256':sha(path)})
            count += 1
    finally:
        cap.release()
    if count != frame_count or sha(source) != digest:
        raise ValueError('Source changed or complete UHD frame count differs')
    pages = []
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
    for offset in range(0,count,16):
        batch = items[offset:offset+16]
        cell = (max(p.width for p in batch),max(p.height for p in batch)+26)
        canvas = Image.new('RGB',(4*cell[0],math.ceil(len(batch)/4)*cell[1]),'#242424')
        draw = ImageDraw.Draw(canvas)
        for local, picture in enumerate(batch):
            x,y = local%4*cell[0],local//4*cell[1]
            draw.text((x+4,y+3),f'f{offset+local:03} | {(offset+local)/24:.3f}s',font=font,fill='white')
            canvas.paste(picture,(x+(cell[0]-picture.width)//2,y+26))
        path = evidence/f'{identity}-{digest[:10]}-p{offset//16+1:02}.png'
        save_image(path,canvas)
        proxy_path = evidence/'proxies'/(path.stem+'.jpg')
        canvas.thumbnail((1680,2400))
        save_image(proxy_path,canvas,jpeg=True)
        pages.append({'firstFrame':offset,'lastFrame':offset+len(batch)-1,
            'path':path.relative_to(EP).as_posix(),'sha256':sha(path),
            'proxy':proxy_path.relative_to(EP).as_posix(),'proxySha256':sha(proxy_path)})
    result = {'schemaVersion':'vivhite-native-print-detail-inspection-1','sourceSha256':digest,
        'workerSha256':sha(__file__),'trackingWorkerSha256':sha(ROOT/'video-maker/tools/stabilize_printed_patch.py'),
        'nativeSize':[3840,2160],'trackingProxySize':[1344,768],'centerInProxy':list(center),
        'radiusInProxy':radius,'maximumTrackedScale':max_scale,'nativeFrames':count,
        'nativePagesResized':False,'clippedRegionsStretchedToSquare':False,
        'originalVideoUnchanged':True,'pages':pages,'nativeEvidence':native_evidence,
        'tracking':tracking,'semanticAcceptance':'not-granted','humanFullPlayback':False}
    preserve(evidence/f'{identity}-{digest[:10]}.json',(json.dumps(result,indent=2)+'\n').encode())
    print(identity,count,'native print crops;',len(pages),'pages; no acceptance granted.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--identity',required=True)
    parser.add_argument('--center',required=True,type=int,nargs=2)
    parser.add_argument('--radius',required=True,type=int)
    parser.add_argument('--frames',required=True,type=int,choices=(120,240,336))
    parser.add_argument('--max-scale',type=float,default=2.5)
    args = parser.parse_args()
    inspect(args.source,args.identity,tuple(args.center),args.radius,args.frames,args.max_scale)
