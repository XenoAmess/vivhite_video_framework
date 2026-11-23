"""Full ink projection using explicitly observed material-plane keyframes.

Original physical hand is protected and never projected from the texture. Intermediate plane
coordinates are interpolated; actual alignment must be reviewed. GPL-3.0-only.
"""
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np
from stabilize_carrier_plane import polygon_mask, sha


from project_keyframed_print import quad_at


def skin_mask(image):
    b, g, r = [image[:,:,i].astype(np.int16) for i in range(3)]
    return ((r-g > 10) & (g-b > 5) & (r-b > 40) & (r > 80)).astype(np.uint8)*255


def composite(source, reference, destination, definition):
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Preserve previous candidate')
    cap = cv2.VideoCapture(str(source))
    ok, first = cap.read()
    texture = cv2.imread(str(reference))
    if not ok or texture is None or first.shape != texture.shape:
        raise ValueError('Native source and original texture required')
    mask = polygon_mask(first.shape, definition['patchPolygons'])
    mask = np.clip(cv2.distanceTransform(mask,cv2.DIST_L2,5)/definition['feather'],0,1)
    hand_roi = polygon_mask(first.shape,[definition['referenceHandPolygon']])
    reference_hand = cv2.dilate(cv2.bitwise_and(skin_mask(texture),hand_roi),np.ones((5,5),np.uint8))
    mask[reference_hand > 0] = 0
    lighting = polygon_mask(first.shape,definition['lightingPolygons']) > 0
    reference_median = np.median(texture[lighting],axis=0)
    reference_quad = np.float32(definition['referenceQuad'])
    keyframes = definition['keyframes']
    metrics, count = [], 0
    destination.parent.mkdir(parents=True,exist_ok=True)
    partial = destination.with_suffix('.partial.mp4')
    with destination.with_suffix('.encoder.log').open('wb') as errors:
        encoder = subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','bgr24',
            '-s','1344x768','-r','24','-i','pipe:0','-an','-c:v','libx264','-crf','15',
            '-preset','fast','-pix_fmt','yuv420p',str(partial)],stdin=subprocess.PIPE,stderr=errors)
        try:
            frame = first
            while True:
                quad = quad_at(keyframes,count)
                matrix = cv2.getPerspectiveTransform(reference_quad,quad)
                unwarped = cv2.warpPerspective(frame,np.linalg.inv(matrix),(1344,768))
                gain = np.clip(np.median(unwarped[lighting],axis=0)/reference_median,.8,1.2)
                # Normal cloth exposure applies equally to ink and canvas, no face-only boost.
                ink = cv2.warpPerspective(texture.astype(np.float32)*gain,matrix,(1344,768))
                alpha = cv2.warpPerspective(mask,matrix,(1344,768))[:,:,None]
                current_roi = cv2.warpPerspective(hand_roi,matrix,(1344,768))
                actual_hand = cv2.dilate(cv2.bitwise_and(skin_mask(frame),current_roi),np.ones((5,5),np.uint8))
                alpha[actual_hand > 0] = 0
                result = np.clip(ink*alpha+frame*(1-alpha),0,255).astype(np.uint8)
                encoder.stdin.write(result.tobytes())
                metrics.append({'frame':count,'quad':quad.tolist(),'matrix':matrix.tolist(),'bgrClothGain':gain.tolist()})
                count += 1
                ok, frame = cap.read()
                if not ok:
                    break
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Encoder failed')
        finally:
            cap.release()
            if encoder.poll() is None:
                encoder.kill();encoder.wait()
    if count != 120:
        raise ValueError('Complete120frame source required')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True,timeout=180)
    partial.replace(destination)
    receipt={'schemaVersion':'vivhite-keyframed-print-1','sourceSha256':sha(source),
        'referenceSha256':sha(reference),'workerSha256':sha(__file__),'sha256':sha(destination),
        'definition':definition,'frames':count,'fps':24,'tracking':metrics,'fullDecode':'passed',
        'geometryWorkerSha256':sha(Path(__file__).with_name('project_keyframed_print.py')),
        'method':'Observed pouch anchors and whole original print; blank-cloth exposure matching. Reference hand pixels excluded; actual original grip preserved through restricted skin occlusion mask. No facial tracking or new hand pixels.',
        'semanticAcceptance':'pending-actual-all-frame-alignment-review','humanFullPlayback':False}
    destination.with_suffix('.keyframes.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return receipt
