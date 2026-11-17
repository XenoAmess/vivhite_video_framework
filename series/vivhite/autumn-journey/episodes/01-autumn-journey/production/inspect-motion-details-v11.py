"""Save every native UHD motion crop in four-frame pages for anatomy review.

Extracts inspection evidence only, never edits the video. GPL-3.0-only.
"""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
import cv2
from PIL import Image,ImageDraw,ImageFont

EP=Path(__file__).resolve().parents[1]
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def preserve(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes()!=data:raise ValueError('Preserve existing evidence; use another identity')
    if not path.exists():path.write_bytes(data)
def save_image(path,image,quality=None):
    content=BytesIO();image.save(content,format='JPEG' if quality else 'PNG',**({'quality':quality} if quality else {}))
    preserve(path,content.getvalue())


def inspect(source,run_name,identity,box,expected_frames):
    if not re.fullmatch(r'S\d{2}-[a-z0-9-]+',identity):raise ValueError('Use an explicit shot-region identity')
    if not re.fullmatch(r'production-v11-[a-z0-9-]+',run_name):raise ValueError('Use a separate v11 evidence run')
    source=Path(source).resolve();digest=sha(source)
    evidence=EP/'assets/generated'/run_name/'review/motion-details'
    cap=cv2.VideoCapture(str(source));pages=[];count=0
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    try:
        if not cap.isOpened():raise ValueError('Actual video source is required')
        width,height=round(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),round(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if (width,height,round(cap.get(cv2.CAP_PROP_FPS)))!=(3840,2160,24):raise ValueError('Native UHD at 24fps required')
        x1,y1,x2,y2=box
        if not (0<=x1<x2<=width and 0<=y1<y2<=height):raise ValueError('Invalid native crop box')
        cell=(x2-x1,y2-y1+22);canvas=None;endpoints=[]
        while True:
            ok,frame=cap.read()
            if not ok:break
            rgb=Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            if count in (0,24,48,72,95,119,167,239,287,335) or count==expected_frames-1:
                path=evidence/f'{identity}-{digest[:10]}-native-f{count:03}.png'
                save_image(path,rgb);endpoints.append({'path':path.relative_to(EP).as_posix(),'sha256':sha(path),'frame':count})
            local=count%4
            if local==0:canvas=Image.new('RGB',(2*cell[0],2*cell[1]),'#242424')
            x,y=local%2*cell[0],local//2*cell[1]
            ImageDraw.Draw(canvas).text((x+3,y+3),f'f{count:03} | {count/24:.3f}s',font=font,fill='white')
            canvas.paste(rgb.crop(box),(x,y+22));count+=1
            if count%4==0 or count==expected_frames:
                path=evidence/f'{identity}-{digest[:10]}-p{len(pages)+1:02}.png'
                save_image(path,canvas);save_image(evidence/'proxies'/(path.stem+'.jpg'),canvas,quality=92)
                pages.append({'path':path.relative_to(EP).as_posix(),'sha256':sha(path),'items':local+1,'firstFrame':count-local-1,'lastFrame':count-1})
    finally:cap.release()
    if count!=expected_frames or sha(source)!=digest:raise ValueError('Wrong frame count or changed original source')
    record={'schemaVersion':'vivhite-fixed-motion-region-inspection-1','sourceSha256':digest,'workerSha256':sha(__file__),
        'nativeSize':[3840,2160],'framesPerPage':4,'box':list(box),'nativeFrames':count,'originalPixelsOnly':True,'pages':pages,'nativeEvidence':endpoints,'semanticAcceptance':'not-granted'}
    preserve(evidence/f'{identity}-{digest[:10]}.json',(json.dumps(record,indent=2)+'\n').encode())
    print(identity,count,'native crops',len(pages),'pages')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path);p.add_argument('--run-name',required=True)
    p.add_argument('--identity',required=True);p.add_argument('--box',required=True,nargs=4,type=int)
    p.add_argument('--frames',type=int,choices=(120,240,336),default=120)
    a=p.parse_args();inspect(a.source,a.run_name,a.identity,tuple(a.box),a.frames)
