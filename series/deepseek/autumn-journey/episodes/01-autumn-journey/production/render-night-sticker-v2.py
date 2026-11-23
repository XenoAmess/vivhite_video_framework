"""Rigid full RGBA sticker on newly generated empty glass; gated. GPL-3.0-only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import cv2
import numpy as np

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
sys.path.insert(0, str(ROOT/'video-maker/tools'))
from stabilize_carrier_plane import CarrierTracker


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(plan_file):
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    source = ROOT.parent/plan['input']
    sticker = EPISODE/plan['sticker']
    destination = ROOT.parent/plan['runtimeRelativeToRepositoryParent']/'sources/S40.mp4'
    if destination.exists():
        raise ValueError('Keep prior candidate')
    if sha(source) != plan['inputSha256'] or sha(sticker) != plan['stickerSha256']:
        raise ValueError('Actual background or alpha changed')
    for worker, digest in plan['workers'].items():
        if sha(ROOT/worker) != digest:
            raise ValueError('Reviewed worker changed')
    gate = [sys.executable, '-X', 'utf8', str(ROOT/'scripts/character_review.py'), 'check',
        '--episode', str(EPISODE/'episode.json'), '--document', str(plan_file),
        '--asset', str(source), '--asset', str(sticker)]
    subprocess.run(gate, check=True)
    pixels = cv2.imread(str(sticker), cv2.IMREAD_UNCHANGED)
    if pixels is None or pixels.shape[2] != 4 or pixels[:, :, 3].min() != 0:
        raise ValueError('Actual transparent sticker required')
    cap = cv2.VideoCapture(str(source))
    ok, first = cap.read()
    if not ok:
        raise ValueError('Missing background')
    tracker = CarrierTracker(first, plan['carrierPolygons'], max_shift=25, max_scale_change=.04)
    x, y = plan['position']
    h, w = pixels.shape[:2]
    if x < 0 or y < 0 or x+w > 1344 or y+h > 768:
        raise ValueError('Sticker escaped glass crop')
    color = np.zeros_like(first)
    alpha = np.zeros((768, 1344), np.float32)
    color[y:y+h, x:x+w] = pixels[:, :, :3]
    alpha[y:y+h, x:x+w] = pixels[:, :, 3].astype(np.float32)/255
    # Premultiply before interpolation: no dark RGB fringe at the alpha boundary.
    premultiplied = color.astype(np.float32)*alpha[:, :, None]
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix('.partial.mp4')
    metrics, count = [], 0
    with destination.with_suffix('.encoder.log').open('wb') as errors:
        encoder = subprocess.Popen(['ffmpeg','-v','error','-f','rawvideo','-pix_fmt','bgr24',
            '-s','1344x768','-r','24','-i','pipe:0','-an','-c:v','libx264','-crf','15',
            '-preset','fast','-pix_fmt','yuv420p',str(partial)],stdin=subprocess.PIPE,stderr=errors)
        try:
            frame = first
            while True:
                matrix, metric = (np.eye(3), {'scale':1,'inliers':len(tracker.points),'medianResidual':0}) if count == 0 else tracker.transform(frame)
                ink = cv2.warpPerspective(premultiplied, matrix, (1344,768))
                a = cv2.warpPerspective(alpha, matrix, (1344,768))[:, :, None]
                result = np.clip(ink+frame*(1-a),0,255).astype(np.uint8)
                encoder.stdin.write(result.tobytes())
                metrics.append({'frame':count,'matrix':matrix.tolist(),**metric})
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
                encoder.kill()
                encoder.wait()
    if count != 120:
        raise ValueError('Complete5second native background required')
    subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(partial),'-f','null','-'],check=True,timeout=180)
    partial.replace(destination)
    destination.with_suffix('.composite.json').write_text(json.dumps({'schemaVersion':'deepseek-rigid-night-sticker-1',
        'planSha256':sha(plan_file),'sourceSha256':sha(source),'stickerSha256':sha(sticker),'sha256':sha(destination),
        'frames':count,'fps':24,'tracking':metrics,'fullDecode':'passed','humanFullPlayback':False,
        'semanticAcceptance':'pending-actual-full-sequence-review','method':'Premultiplied-alpha projection of whole imagegen paper sticker onto physical window frame tracking; animated exterior only.'},indent=2)+'\n',encoding='utf-8')
    print(destination,sha(destination))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    render(parser.parse_args().plan.resolve())
