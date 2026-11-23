"""Retain every whole-pouch crop at native pixel resolution, never approve. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
from PIL import Image, ImageDraw

EPISODE=Path(__file__).resolve().parent.parent


def prepare(source,output,box):
    output.mkdir(parents=True,exist_ok=False)
    cap=cv2.VideoCapture(str(source)); frames=[]
    try:
        while True:
            ok,frame=cap.read()
            if not ok: break
            frames.append(Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)).crop(box))
    finally:
        cap.release()
    width,height=box[2]-box[0],box[3]-box[1]
    items=[]
    for offset in range(0,len(frames),30):
        part=frames[offset:offset+30]
        sheet=Image.new('RGB',(5*width,6*(height+20)),'#222')
        draw=ImageDraw.Draw(sheet)
        for i,frame in enumerate(part):
            x=i%5*width;y=i//5*(height+20)
            sheet.paste(frame,(x,y+20));draw.text((x+3,y+3),str(offset+i),fill='white')
        target=output/f'S37-pouch-native-all-{offset//30+1:02d}.png'
        sheet.save(target)
        items.append({'path':target.relative_to(EPISODE).as_posix(),
                      'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'items':len(part)})
    result={'schemaVersion':'deepseek-native-pouch-proofs-3',
        'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'decodedFrames':len(frames),
        'nativeCrop':box,'resized':False,'pages':items,'assistantActuallyViewed':False,
        'scope':'Every actual source frame cropped at native resolution, no upscaling, projection or aesthetic decision.'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(output)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--box',default='840,65,1120,270')
    args=parser.parse_args()
    prepare(args.source,args.output.resolve(),[int(v) for v in args.box.split(',')])
