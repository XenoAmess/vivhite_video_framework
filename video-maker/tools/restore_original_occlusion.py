"""Restore only existing source hand pixels over a supported-prop composite. GPL-3.0-only."""
import argparse
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from stabilize_carrier_plane import polygon_mask,sha
from project_keyframed_print_occlusion_v2 import skin_mask


def composite(base, original, destination, definition):
    base,original,destination=map(Path,(base,original,destination))
    if destination.exists(): raise ValueError('Retain previous candidate')
    a=cv2.VideoCapture(str(base));b=cv2.VideoCapture(str(original))
    ok,first=a.read();ok2,raw=b.read()
    if not ok or not ok2 or first.shape!=raw.shape: raise ValueError('Synchronized native inputs required')
    roi=polygon_mask(first.shape,definition['originalHandPolygons'])
    destination.parent.mkdir(parents=True,exist_ok=True)
    partial=destination.with_suffix('.partial.mp4'); count=0;metrics=[]
    encoder=subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','bgr24','-s','1344x768',
        '-r','24','-i','pipe:0','-an','-c:v','libx264','-crf','15','-preset','fast','-pix_fmt','yuv420p',str(partial)],stdin=subprocess.PIPE)
    try:
        frame=first
        while True:
            visible=cv2.dilate(cv2.bitwise_and(skin_mask(raw),roi),np.ones((5,5),np.uint8))
            visible=cv2.bitwise_and(visible,roi)>0
            result=frame.copy();result[visible]=raw[visible]
            encoder.stdin.write(result.tobytes());metrics.append({'frame':count,'restoredOriginalPixels':int(visible.sum())})
            count+=1;ok,frame=a.read();ok2,raw=b.read()
            if ok!=ok2: raise ValueError('Input frame counts differ')
            if not ok: break
        encoder.stdin.close()
        if encoder.wait(timeout=180): raise RuntimeError('Occlusion encoder failed')
    finally:
        a.release();b.release()
        if encoder.poll() is None:encoder.kill();encoder.wait()
    if count!=120: raise ValueError('Require complete synchronized120frame sources')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True,timeout=180)
    partial.replace(destination)
    record={'schemaVersion':'vivhite-original-occlusion-1','baseSha256':sha(base),'originalSha256':sha(original),
        'workerSha256':sha(__file__),'skinWorkerSha256':sha(Path(__file__).with_name('project_keyframed_print_occlusion_v2.py')),
        'definition':definition,'sha256':sha(destination),'frames':count,'fps':24,'allFrames':metrics,
        'method':'Within explicit hand ROI, preserve actual original connected skin pixels above the complete physical pouch. No human pixel is generated or transferred from a different frame.',
        'fullDecode':'passed','semanticAcceptance':'pending-actual-complete-frame-review'}
    destination.with_suffix('.occlusion.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['base','original','destination','definition']:parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    composite(args.base,args.original,args.destination,json.loads(args.definition.read_text(encoding='utf-8')))
