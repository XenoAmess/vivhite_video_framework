"""Restore existing printed eye/glasses artwork without replacing the whole head.

Original media and failed candidates are retained. Every corrected frame still
requires actual review. Never use this to cover a generated person. GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path
import subprocess

import cv2
import numpy as np

from stabilize_printed_patch import PrintedPatch, fingerprint


def eye_registration(reference_eyes, target_eyes):
    original = np.asarray(reference_eyes,dtype=np.float64).reshape(2,2)
    target = np.asarray(target_eyes,dtype=np.float64).reshape(2,2)
    if not np.isfinite(original).all() or not np.isfinite(target).all():
        raise ValueError('Finite printed eye landmarks required')
    before,after = original[1]-original[0],target[1]-target[0]
    norm = before@before
    if norm < 1 or after@after < 1:
        raise ValueError('Distinct printed eye landmarks required')
    real = (before@after)/norm
    imaginary = (before[0]*after[1]-before[1]*after[0])/norm
    rotation = np.array([[real,-imaginary],[imaginary,real]])
    return np.column_stack((rotation,target[0]-rotation@original[0]))


def projected_eyes(reference, reference_eyes, target_eyes, size, gain_rgb, mask_scale=1):
    if reference is None or reference.ndim != 3 or reference.shape[2] != 4:
        raise ValueError('Original RGBA merchandise artwork required')
    gain = np.asarray(gain_rgb,dtype=np.float32)
    if gain.shape != (3,) or not np.isfinite(gain).all() or np.any(gain <= 0) or np.any(gain > 1.5):
        raise ValueError('Explicit finite RGB lighting gains required')
    if not np.isfinite(mask_scale) or not .05 <= mask_scale <= 4:
        raise ValueError('Finite reference mask scale from .05 to four required')
    matrix = eye_registration(reference_eyes,target_eyes)
    mask = np.zeros(reference.shape[:2],dtype=np.float32)
    eyes = np.asarray(reference_eyes).reshape(2,2)
    for x,y in eyes:
        cv2.ellipse(mask,(round(x),round(y+23*mask_scale)),
            (round(95*mask_scale),round(78*mask_scale)),0,0,360,1,-1)
    cv2.rectangle(mask,(round(eyes[0,0]+85*mask_scale),round(min(eyes[:,1])-5*mask_scale)),
        (round(eyes[1,0]-85*mask_scale),round(max(eyes[:,1])+45*mask_scale)),1,-1)
    mask = cv2.GaussianBlur(mask,(0,0),18*mask_scale)*reference[:,:,3].astype(np.float32)/255
    texture = np.clip(reference[:,:,:3].astype(np.float32)*gain[::-1],0,255)
    return (cv2.warpAffine(texture,matrix,size),
        cv2.warpAffine(mask,matrix,size),matrix)


def restore(source, destination, reference_file, reference_eyes, target_eyes, center, radius, frames, gain_rgb, mask_scale=1):
    source,destination,reference_file = Path(source),Path(destination),Path(reference_file)
    if destination.exists() or destination.with_suffix('.partial.mp4').exists():
        raise ValueError('Use a new correction version; preserve existing candidates')
    source_digest = fingerprint(source)
    reference_digest = fingerprint(reference_file)
    capture = cv2.VideoCapture(str(source))
    encoder = None
    try:
        if (round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                round(capture.get(cv2.CAP_PROP_FPS)),round(capture.get(cv2.CAP_PROP_FRAME_COUNT))) != (3840,2160,24,frames):
            raise ValueError('Require the complete actual native UHD source')
        ok,first = capture.read()
        if not ok:
            raise ValueError('Cannot read original source')
        texture,mask,registration = projected_eyes(cv2.imread(str(reference_file),cv2.IMREAD_UNCHANGED),
            reference_eyes,target_eyes,(3840,2160),gain_rgb,mask_scale)
        tracker = PrintedPatch(cv2.resize(first,(1344,768)),tuple(center),radius)
        scaling = np.diag([1344/3840,768/2160,1])
        inverse = np.linalg.inv(scaling)
        destination.parent.mkdir(parents=True,exist_ok=True)
        partial = destination.with_suffix('.partial.mp4')
        tracking = []
        with destination.with_suffix('.encoder.log').open('wb') as log:
            encoder = subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','bgr24',
                '-s','3840x2160','-r','24','-i','pipe:0','-i',str(source),'-map','0:v:0','-map','1:a:0?',
                '-c:v','libx264','-preset','fast','-crf','16','-pix_fmt','yuv420p','-c:a','copy',str(partial)],
                stdin=subprocess.PIPE,stderr=log)
            image = first
            for index in range(frames):
                if index:
                    ok,image = capture.read()
                    if not ok:
                        raise ValueError('Unexpected truncated source')
                    _,metric = tracker.frame(cv2.resize(image,(1344,768)))
                    tracking.append({'frame':index,**metric})
                transform = inverse@tracker.transform@scaling
                warped = cv2.warpPerspective(texture,transform,(3840,2160))
                alpha = np.clip(cv2.warpPerspective(mask,transform,(3840,2160)),0,1)[:,:,None]
                corrected = (warped*alpha+image*(1-alpha)).clip(0,255).astype(np.uint8)
                encoder.stdin.write(corrected.tobytes())
            if capture.read()[0]:
                raise ValueError('Unexpected extra source frames')
            encoder.stdin.close()
            if encoder.wait(timeout=180):
                raise RuntimeError('Printed artwork encoder failed; preserve partial and log')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True,timeout=180)
        if fingerprint(source) != source_digest or fingerprint(reference_file) != reference_digest:
            raise ValueError('Source or reference changed during restoration')
        partial.replace(destination)
        receipt = {'schemaVersion':'vivhite-printed-eye-restoration-1','sourceSha256':source_digest,
            'correctedSha256':fingerprint(destination),'referenceTextureSha256':reference_digest,
            'workerSha256':fingerprint(__file__),'trackingWorkerSha256':fingerprint(Path(__file__).with_name('stabilize_printed_patch.py')),
            'frames':frames,'fps':24,'nativeSize':[3840,2160],'referenceEyes':list(reference_eyes),
            'targetEyes':list(target_eyes),'registration':registration.tolist(),'gainRgb':list(gain_rgb),
            'referenceMaskScale':mask_scale,
            'trackingCenter':list(center),'trackingRadius':radius,'tracking':tracking,
            'method':'Original RGBA eye/glasses texture, two-landmark similarity registration, feathered lens masks and original prop tracking.',
            'scope':'Local printed eye/glasses pixels before whole-frame CRF16 re-encoding. No person removed; original head outline and scene retained.',
            'status':'technical-correction-completed-review-required','humanFullPlayback':False}
        destination.with_suffix('.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
        print(frames,'native frames corrected; actual complete-frame review required.')
        return receipt
    finally:
        capture.release()
        if encoder is not None:
            try:
                if encoder.stdin and not encoder.stdin.closed:
                    encoder.stdin.close()
            except BrokenPipeError:
                pass  # The original encoder failure remains the primary error.
            finally:
                if encoder.poll() is None:
                    encoder.kill()
                    encoder.wait()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--destination',required=True,type=Path)
    parser.add_argument('--reference',required=True,type=Path)
    parser.add_argument('--reference-eyes',required=True,type=float,nargs=4)
    parser.add_argument('--target-eyes',required=True,type=float,nargs=4)
    parser.add_argument('--tracking-center',required=True,type=int,nargs=2)
    parser.add_argument('--tracking-radius',required=True,type=int)
    parser.add_argument('--frames',required=True,type=int,choices=(120,240,336))
    parser.add_argument('--gain-rgb',type=float,nargs=3,default=(1,1,1))
    parser.add_argument('--mask-scale',type=float,default=1,
        help='Scale lens masks in reference-image pixels; retain one for the original M09 coordinates')
    args = parser.parse_args()
    restore(args.source,args.destination,args.reference,args.reference_eyes,args.target_eyes,
        args.tracking_center,args.tracking_radius,args.frames,args.gain_rgb,args.mask_scale)
