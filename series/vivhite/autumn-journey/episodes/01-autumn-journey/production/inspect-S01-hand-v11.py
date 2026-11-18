"""Preserve every original UHD S01 hand crop; never change the source video.

The linear region follows this specific shot's existing camera push-in.
GPL-3.0-only.
"""
import argparse
from io import BytesIO
import json
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(EP.parents[4]/'video-maker/tools'))
from reference_finisher import sha


def preserve(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve earlier evidence; use another run')
    if not path.exists():
        path.write_bytes(data)


def inspect(source):
    digest = sha(source)
    out = EP/'assets/generated/production-v11-native-4k-001/review/hand'
    cap = cv2.VideoCapture(str(source))
    pages, boxes, count = [], [], 0
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    try:
        if tuple(round(cap.get(key)) for key in (cv2.CAP_PROP_FRAME_WIDTH,
                cv2.CAP_PROP_FRAME_HEIGHT,cv2.CAP_PROP_FPS,cv2.CAP_PROP_FRAME_COUNT)) != (3840,2160,24,120):
            raise ValueError('Exact 120-frame native UHD S01 source required')
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            left = round(2200+860*count/119)-440
            box = (left,100,left+880,1040)
            boxes.append({'frame':count,'box':box})
            local = count%12
            if local == 0:
                canvas = Image.new('RGB',(3*880,4*966),'#242424')
            x,y = local%3*880,local//3*966
            ImageDraw.Draw(canvas).text((x+4,y+3),f'f{count:03} | {count/24:.3f}s',font=font,fill='white')
            rgb = Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB))
            canvas.paste(rgb.crop(box),(x,y+26))
            count += 1
            if count%12 == 0:
                stem = f'S01-hand-{digest[:10]}-p{count//12:02}'
                paths = []
                for suffix,settings in (('.png',{}),('.jpg',{'quality':94})):
                    path = out/(stem+suffix)
                    buffer = BytesIO()
                    canvas.save(buffer,format='PNG' if suffix == '.png' else 'JPEG',**settings)
                    preserve(path,buffer.getvalue())
                    paths.append({'path':path.relative_to(EP).as_posix(),'sha256':sha(path)})
                pages.append({'firstFrame':count-12,'lastFrame':count-1,'originalPng':paths[0],'jpegViewingCopy':paths[1]})
    finally:
        cap.release()
    if count != 120 or sha(source) != digest:
        raise ValueError('Changed or incomplete source')
    record = {'sourceSha256':digest,'workerSha256':sha(__file__),'frames':count,'pages':pages,
        'nativeBoxes':boxes,'sourceVideoChanged':False,'humanFullPlayback':False,'semanticAcceptance':'not-granted'}
    preserve(out/f'S01-hand-{digest[:10]}.json',(json.dumps(record,indent=2)+'\n').encode())
    print('S01: saved all 120 native hand crops in 10 pages; no acceptance granted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    inspect(parser.parse_args().source)
