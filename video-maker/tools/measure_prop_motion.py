"""Measure prop motion relative to its support; never infer aesthetic acceptance. GPL-3.0-only."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np

from stabilize_carrier_plane import CarrierTracker, polygon_mask, sha


def relative_point(object_matrix, support_matrix, point):
    point = np.asarray([point[0],point[1],1.0],dtype=float)
    mapped = np.linalg.inv(support_matrix) @ object_matrix @ point
    mapped /= mapped[2]
    return [float(mapped[0]-point[0]),float(mapped[1]-point[1])]


def measure(source, definition):
    capture = cv2.VideoCapture(str(source))
    fps = capture.get(cv2.CAP_PROP_FPS)
    ok, first = capture.read()
    if not ok:
        capture.release()
        raise ValueError('Cannot read actual source')
    try:
        subject = CarrierTracker(first,definition['objectPolygons'],max_shift=400,max_scale_change=.35)
        support = CarrierTracker(first,definition['supportPolygons'],definition['objectPolygons'],
                                 max_shift=200,max_scale_change=.3)
        mask = polygon_mask(first.shape,definition['objectPolygons'])
        y,x = np.nonzero(mask)
        point = [float(np.mean(x)),float(np.mean(y))]
        rows=[]; index=0; current=first
        while True:
            if index:
                obj,om=subject.transform(current)
                sup,sm=support.transform(current)
            else:
                obj=sup=np.eye(3); om=sm={'inliers':0,'medianResidual':0,'scale':1}
            dx,dy = relative_point(obj,sup,point)
            rows.append({'frame':index,'seconds':index/fps,'relativeDx':dx,'relativeDy':dy,
                         'objectMatrix':obj.tolist(),'supportMatrix':sup.tolist(),
                         'objectFit':om,'supportFit':sm})
            index+=1
            ok,current=capture.read()
            if not ok: break
    finally:
        capture.release()
    return {'schemaVersion':'vivhite-relative-prop-motion-1','sourceSha256':sha(source),
        'workerSha256':sha(__file__),'definition':definition,'fps':fps,'frames':len(rows),
        'allFrames':rows,'scope':'Independent feature fits for the whole prop and physical support. Pixel displacement is diagnostic evidence, not physical centimetres or semantic approval. Verify subject, support and hand anatomy in actual frames.',
        'semanticAcceptance':'pending-actual-frame-review'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--definition',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise ValueError('Retain prior diagnostic candidate')
    result=measure(args.source,json.loads(args.definition.read_text(encoding='utf-8')))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Relative whole-prop motion measured; no automatic approval')
