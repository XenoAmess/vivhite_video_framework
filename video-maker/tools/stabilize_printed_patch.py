"""Keep a printed surface inert while preserving its tracked physical motion.

This corrects video texture drift, never hides a newly generated human. Originals
are retained; the corrected clip must receive a new complete frame review.
GPL-3.0-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess


def fingerprint(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class PrintedPatch:
    def __init__(self, first, center, radius, max_scale=2.5):
        import cv2
        import numpy as np
        self.cv2, self.np = cv2, np
        if not math.isfinite(max_scale) or max_scale <= 1:
            raise ValueError("Maximum tracked scale must be finite and greater than one")
        self.max_scale = max_scale
        self.height, self.width = first.shape[:2]
        x,y = center
        if not (radius >= 10 and radius < x < self.width-radius and radius < y < self.height-radius):
            raise ValueError("Printed patch circle must lie inside the frame")
        self.first = first.copy()
        self.gray = cv2.cvtColor(first,cv2.COLOR_BGR2GRAY)
        yy,xx = np.mgrid[:self.height,:self.width]
        distance = np.sqrt((xx-x)**2+(yy-y)**2)
        self.mask = np.clip((radius-distance)/3,0,1).astype(np.float32)
        self.ring = ((distance > radius*.62)&(distance < radius*1.06)).astype(np.uint8)*255
        self.points = self.features(self.gray,self.ring)
        self.transform = np.eye(3,dtype=np.float64)
        self.center = center

    def features(self, gray, mask):
        points = self.cv2.goodFeaturesToTrack(gray,maxCorners=100,qualityLevel=.005,minDistance=3,mask=mask)
        if points is None or len(points)<6:
            raise ValueError("Insufficient stable printed-surface tracking features")
        return points

    def frame(self, image):
        cv2,np = self.cv2,self.np
        gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
        found,status,_ = cv2.calcOpticalFlowPyrLK(self.gray,gray,self.points,None,
                                               winSize=(25,25),maxLevel=3)
        back,back_status,_ = cv2.calcOpticalFlowPyrLK(gray,self.gray,found,None,
                                                   winSize=(25,25),maxLevel=3)
        valid = ((status.ravel()>0)&(back_status.ravel()>0)
                 &(np.linalg.norm(back-self.points,axis=2).ravel()<1.5))
        if valid.sum()<6:
            raise ValueError("Printed-surface tracking lost; no corrected clip accepted")
        matrix,inliers = cv2.estimateAffinePartial2D(self.points[valid],found[valid],
                                                    method=cv2.RANSAC,ransacReprojThreshold=1.5)
        if matrix is None or inliers.sum()<5:
            raise ValueError("Printed-surface tracking is ambiguous")
        step = np.vstack((matrix,[0,0,1]))
        candidate = step@self.transform
        scale = float(np.sqrt(abs(np.linalg.det(candidate[:2,:2]))))
        if not .1<scale<self.max_scale:
            raise ValueError("Unreasonable printed-surface scale")
        patch = cv2.warpPerspective(self.first,candidate,(self.width,self.height),flags=cv2.INTER_LINEAR)
        mask = cv2.warpPerspective(self.mask,candidate,(self.width,self.height),flags=cv2.INTER_LINEAR)
        result = (patch.astype(np.float32)*mask[:,:,None]+image*(1-mask[:,:,None])).clip(0,255).astype(np.uint8)
        self.transform = candidate
        self.gray = gray
        # Refresh only on the stable rim/hair boundary, excluding the changing eyes.
        ring = cv2.warpPerspective(self.ring,candidate,(self.width,self.height),flags=cv2.INTER_NEAREST)
        self.points = self.features(gray,ring)
        center = cv2.perspectiveTransform(np.array([[self.center]],dtype=np.float32),candidate)[0,0]
        return result,{"scale":scale,"center":[float(v) for v in center],"inliers":int(inliers.sum())}


def stabilize(source,destination,center,radius,used_seconds=None,max_scale=2.5):
    import cv2
    cap = cv2.VideoCapture(str(source))
    ok,first = cap.read()
    if not ok:
        raise ValueError("Cannot read printed-surface source")
    fps = cap.get(cv2.CAP_PROP_FPS)
    if used_seconds is not None and (not math.isfinite(used_seconds) or used_seconds <= 0):
        cap.release()
        raise ValueError("Used seconds must be finite and positive")
    frame_limit = math.ceil(used_seconds*fps) if used_seconds is not None else None
    try:
        tracker = PrintedPatch(first,center,radius,max_scale)
    except Exception:
        cap.release()
        raise
    destination = Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():
        raise ValueError("Use a new corrected version; do not overwrite an existing clip")
    partial = destination.with_suffix('.partial.mp4')
    log = destination.with_suffix('.encoder.log')
    frames = 0
    tracking = []
    with log.open('wb') as errors:
        encoder = subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','bgr24',
            '-s',f'{first.shape[1]}x{first.shape[0]}','-r',str(fps),'-i','pipe:0','-i',str(source),
            '-map','0:v:0','-map','1:a:0?','-c:v','libx264','-preset','fast','-crf','16',
            '-pix_fmt','yuv420p','-c:a','copy',str(partial)],stdin=subprocess.PIPE,stderr=errors)
        try:
            encoder.stdin.write(first.tobytes());frames=1
            while frame_limit is None or frames < frame_limit:
                ok,image = cap.read()
                if not ok:
                    break
                corrected,metric = tracker.frame(image)
                tracking.append({'frame':frames,**metric})
                encoder.stdin.write(corrected.tobytes());frames+=1
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Printed-surface encoder failed; original and log retained')
        finally:
            cap.release()
            if encoder.poll() is None:
                encoder.kill();encoder.wait()
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True,timeout=180)
    partial.replace(destination)
    receipt={'schemaVersion':'vivhite-printed-patch-1','sourceSha256':fingerprint(source),
             'correctedSha256':fingerprint(destination),'workerSha256':fingerprint(__file__),
             'center':list(center),'radius':radius,'sourceFrame':0,'frames':frames,'fps':fps,
             'requestedUsedSeconds':used_seconds,'maximumTrackedScale':max_scale,
             'method':'Forward/backward LK on stable surface rim; robust partial-affine projection of original printed texture.',
             'scope':'Only a printed merchandise surface; no new person is removed or covered.',
             'status':'technical-correction-completed-review-required','tracking':tracking}
    destination.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(frames,'frames corrected; original retained; complete review required',flush=True)
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--center',required=True,type=int,nargs=2)
    parser.add_argument('--radius',required=True,type=int)
    parser.add_argument('--used-seconds',type=float)
    parser.add_argument('--max-scale',type=float,default=2.5,
                        help='Explicit observed zoom bound; default 2.5. Full visual review is still required.')
    args=parser.parse_args()
    stabilize(args.source,args.destination,tuple(args.center),args.radius,args.used_seconds,args.max_scale)
