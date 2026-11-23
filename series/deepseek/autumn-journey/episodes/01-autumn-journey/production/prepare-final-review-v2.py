"""Decode the complete finished movie and retain timestamped review proofs.

No semantic acceptance is inferred from decoding or frame selection.
GPL-3.0-only.
"""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess

import cv2
from PIL import Image

EPISODE = Path(__file__).resolve().parent.parent
ROOT = EPISODE.parents[4]
MEDIA = ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey/production-v2-768p-full-001'


def sha(file):
    with Path(file).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare():
    film = MEDIA/'film.mp4'
    plan = json.loads((EPISODE/'final-assembly-plan-v2-768p.json').read_text(encoding='utf-8'))
    receipt = json.loads((MEDIA/'final-assembly-receipt.json').read_text(encoding='utf-8'))
    digest = sha(film)
    if receipt['filmSha256'] != digest or plan['totalFrames'] != 6150:
        raise ValueError('Use the actually finished, bound full film')
    output = EPISODE/'assets/generated/production-v2-final-review-001'
    manifest_file = output/'manifest.json'
    if manifest_file.exists():
        prior = json.loads(manifest_file.read_text(encoding='utf-8'))
        if prior['filmSha256'] != digest or prior['workerSha256'] != sha(__file__):
            raise ValueError('Preserve the prior final-review version')
        for item in prior['proofPages']+prior['titleAndEndingFrames']:
            if sha(EPISODE/item['pathRelativeToEpisode']) != item['sha256']:
                raise ValueError('Actual review proof changed')
        print(manifest_file)
        return
    if output.exists() and any(output.iterdir()):
        raise ValueError('Unfinished review artifacts retained; inspect before a new version')
    output.mkdir(parents=True, exist_ok=True)
    helper = runpy.run_path(str(EPISODE/'production/prepare-source-proof-v1.py'))
    samples = set(range(0, 6150, 15))
    for shot in plan['shots']:
        samples.update([shot['startFrame'], shot['startFrame']+shot['seconds']*30-1])
    native_targets = {570, 600, 660, 690-1, 5730, 5745, 5760, 5820,
                      5850, 5880, 6000, 6090, 6120, 6149}
    capture = cv2.VideoCapture(str(film))
    count = 0
    entries, details, metrics = [], [], []
    previous = None
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if frame.shape[:2] != (768, 1344):
                raise ValueError('Unexpected actual encoded dimensions')
            gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (168, 96))
            change = None if previous is None else float(cv2.absdiff(gray, previous).mean())
            metrics.append({'frame': count, 'meanLuma': round(float(gray.mean()), 5),
                            'meanAbsoluteChange': None if change is None else round(change, 5)})
            previous = gray
            if count in samples:
                shot = next(row for row in plan['shots']
                            if row['startFrame'] <= count < row['startFrame']+row['seconds']*30)
                entries.append((Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)),
                                f"{shot['id']} f{count} {count/30:.2f}s"))
            if count in native_targets:
                target = output/f'film-f{count:04}.png'
                cv2.imwrite(str(target), frame)
                details.append(helper['describe'](target, 1))
            count += 1
    finally:
        capture.release()
    if count != 6150:
        raise ValueError('Incomplete final encoded decode')
    pages = []
    for offset in range(0, len(entries), 32):
        part = entries[offset:offset+32]
        target = output/f'film-timeline-{offset//32+1:02}.png'
        helper['sheet'](part, target, cell=(256, 165), columns=4)
        pages.append(helper['describe'](target, len(part)))
    metrics_file = output/'all-frame-metrics.json'
    metrics_file.write_text(json.dumps(metrics, indent=2)+'\n', encoding='utf-8', newline='\n')
    audio = subprocess.run(['ffmpeg', '-v', 'info', '-i', str(film), '-map', '0:a:0',
                            '-af', 'astats=metadata=0:reset=0', '-f', 'null', '-'],
                           capture_output=True, text=True, timeout=180)
    if audio.returncode:
        raise ValueError('Actual final audio decode failed')
    audio_file = MEDIA/'final-audio-decode-astats.log'
    audio_file.write_text(audio.stderr, encoding='utf-8', newline='\n')
    result = {'schemaVersion': 'deepseek-final-review-proofs-1', 'filmSha256': digest,
              'workerSha256': sha(__file__), 'decodedEncodedFrames': count,
              'outputSize': '1344x768', 'fps': 30, 'seconds': 205,
              'sampledEncodedFrames': len(entries), 'proofPages': pages,
              'titleAndEndingFrames': details, 'allFrameMetricsSha256': sha(metrics_file),
              'fullAudioDecode': 'passed', 'audioDecodeLogSha256': sha(audio_file),
              'assistantActuallyViewed': False, 'humanFullPlayback': False,
              'userAestheticAcceptance': 'pending',
              'scope': 'Complete encoded frame/audio decode plus2fps and every-shot-boundary visual proofs. Does not replace separately recorded complete native-source frame review or infer semantic acceptance.'}
    manifest_file.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(manifest_file)


if __name__ == '__main__':
    prepare()
