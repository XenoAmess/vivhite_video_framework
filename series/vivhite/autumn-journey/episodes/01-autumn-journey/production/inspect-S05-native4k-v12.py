"""Extract the repaired S05 native UHD mechanics after its exact job completes.

Inspection only: original media remain unchanged, no semantic approval.
GPL-3.0-only.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
PLAN = EP / 'production-plan-v12-S05-native-4k-r1.json'
PLAN_SHA = 'f7d10a7c80e72a02bbf541b4109871be0e4845653c4ada12075e4b9de6b63842'
INPUT_SHA = 'd814fd0ade3bd7d62857e3366a19ef2ec51b6a74ed3c1b2e0ad2dc5a9caf19bf'
JOB_ID = 'video_gen_ab78089d679c4c66ba653410717fc5f5'
RUN_NAME = 'production-v12-S05-native-4k-001'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def preserve(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve all previous evidence; use a new variant')
    if not path.exists():
        path.write_bytes(data)


def picture(path, image):
    data = io.BytesIO()
    image.save(data, format='JPEG' if path.suffix == '.jpg' else 'PNG',
               **({'quality': 95, 'subsampling': 0} if path.suffix == '.jpg' else {}))
    preserve(path, data.getvalue())
    return {'path': path.relative_to(EP).as_posix(), 'sha256': sha(path)}


def inside(directory, value):
    path = (directory / value).resolve()
    if not path.is_relative_to(directory):
        raise ValueError('Actual source, input and reports must stay inside the repair run')
    return path


def bound_source(directory):
    if directory.name != RUN_NAME or sha(PLAN) != PLAN_SHA:
        raise ValueError('Use the separate immutable v12 S05 native4K run and plan')
    job_file = directory / 'jobs/S05.json'
    request_file = directory / 'requests/S05.json'
    job = read(job_file)
    if (job.get('status') != 'completed' or job.get('jobId') != JOB_ID
            or job.get('shotId') != 'S05' or job.get('planSha256') != PLAN_SHA):
        raise ValueError('The exact repaired S05 native4K job has not completed')
    plan, request = read(PLAN), read(request_file)
    if (sha(request_file) != job.get('requestSha256')
            or any(request.get(key) != value for key, value in {
                'model': 'open-h3-2k', 'size': '3840x2160', 'sampler': 'up3', 'seed': 1234}.items())
            or request.get('prompt') != plan['shots'][0]['prompt']):
        raise ValueError('Request must match this native4K plan and original prompt')
    remote = job.get('remote', {})
    result = remote.get('result', {})
    if (remote.get('id') != JOB_ID or remote.get('status') != 'completed'
            or remote.get('size') != '3840x2160' or remote.get('model') != 'open-h3-2k'
            or any(result.get(key) != value for key, value in {
                'width': 3840, 'height': 2160, 'frames': 120, 'fps': 24,
                'windows': 1, 'native_resolution': '4k'}.items())):
        raise ValueError('Require completed single-window native UHD server provenance')
    shot = plan['shots'][0]
    source = inside(directory, job['sourceFile'])
    original = inside(directory, shot['inputSource'])
    raw = inside(directory, job['rawFile'])
    if (sha(original) != INPUT_SHA or shot['inputSourceSha256'] != INPUT_SHA
            or sha(source) != job.get('sourceSha256')
            or sha(raw) != job.get('rawSha256') or sha(raw) != result.get('sha256')):
        raise ValueError('Actual repaired input and complete native downloads must match their hashes')
    report_file = directory / 'clip-inspection/S05.json'
    report = read(report_file)
    if (report.get('status') != 'decoded' or report.get('shotId') != 'S05'
            or report['identity'].get('sourceSha256') != sha(source)
            or report['identity'].get('usedSeconds') != 5 or report.get('sourceFps') != 24
            or report.get('decodedFrames') != 120 or report.get('usedFramesAnalysed') != 120
            or sum(row['items'] for row in report['allUsedFrameEvidence']) != 120):
        raise ValueError('Bound complete120-frame inspection required before extracting evidence')
    return source, report_file, report, job_file, request_file


def inspect(directory, variant, regions):
    if not re.fullmatch(r'native-r[1-9][0-9]*', variant):
        raise ValueError('Use a separate numbered native evidence variant')
    if set(regions) != {'saddle-hips', 'legs-cranks', 'sticker'}:
        raise ValueError('Explicit saddle/hip, leg/crank and sticker regions are all required')
    for box in regions.values():
        if len(box) != 4 or not (0 <= box[0] < box[2] <= 3840 and 0 <= box[1] < box[3] <= 2160):
            raise ValueError('Require native UHD boxes covering the complete actual motion')
    source, report_file, report, job_file, request_file = bound_source(directory)
    digest = sha(source)
    destination = EP / 'assets/generated' / RUN_NAME / 'review' / ('cycle-' + variant)
    records = {'wholeScenePages': [], 'nativeWholeCheckpoints': [], 'regions': {}}
    for index, entry in enumerate(report['allUsedFrameEvidence'], 1):
        original = Path(entry['path']).resolve()
        if not original.is_relative_to(EP) or sha(original) != entry['sha256']:
            raise ValueError('Complete whole-scene frame evidence changed')
        with Image.open(original) as image:
            view = image.convert('RGB')
            view.thumbnail((1680, 2400), Image.Resampling.LANCZOS)
            records['wholeScenePages'].append({**picture(destination / f'whole-p{index:02}.jpg', view),
                                               'items': entry['items']})
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 17)
    records['regions'] = {name: {'nativeBox': box, 'nativeFrames': 120,
        'framesPerPage': 4, 'pages': [], 'originalPixelsOnly': True} for name, box in regions.items()}
    canvases = {}
    capture = cv2.VideoCapture(str(source))
    count = 0
    try:
        if tuple(round(capture.get(key)) for key in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT)) != (3840, 2160, 24, 120):
            raise ValueError('Actual3840x2160/24fps/120frame media required; no768P or2K substitution')
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if count >= 120:
                raise ValueError('Unexpected extra source frames; keep partial evidence')
            rgb = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            if count in (0, 24, 48, 72, 95, 119):
                records['nativeWholeCheckpoints'].append({**picture(destination / f'native-f{count:03}.png', rgb),
                                                         'frame': count})
            for name, box in regions.items():
                width, height = box[2]-box[0], box[3]-box[1]
                if count % 4 == 0:
                    canvases[name] = Image.new('RGB', (2*width, 2*(height+26)), '#242424')
                canvas = canvases[name]
                x, y = count % 2 * width, (count % 4 // 2) * (height+26)
                canvas.paste(rgb.crop(box), (x, y+26))
                ImageDraw.Draw(canvas).text((x+4, y+3), f'f{count:03} | {count/24:.3f}s', font=font, fill='white')
                if count % 4 == 3:
                    target = destination / name / f'p{count//4+1:02}.png'
                    row = {**picture(target, canvas), 'firstFrame': count-3, 'lastFrame': count, 'items': 4}
                    view = canvas.copy()
                    view.thumbnail((2240, 2400), Image.Resampling.LANCZOS)
                    row['viewingCopy'] = picture(target.with_suffix('.jpg'), view)
                    records['regions'][name]['pages'].append(row)
            count += 1
    finally:
        capture.release()
    if count != 120 or sha(source) != digest:
        raise ValueError('Incomplete decoding or changed media; preserve partial evidence')
    extractor = Path(__file__).with_name('extract-native-candidates-v11.py')
    command = [sys.executable, str(extractor), '--source', str(source), '--report', str(report_file),
               '--destination', str(destination / 'candidates')]
    subprocess.run(command, cwd=ROOT, check=True, timeout=1800)
    result = {'schemaVersion': 'vivhite-saddle-native4k-inspection-1',
        'sourcePlanSha256': PLAN_SHA, 'inputSourceSha256': INPUT_SHA, 'jobId': JOB_ID,
        'jobReceiptSha256': sha(job_file), 'requestSha256': sha(request_file),
        'sourceSha256': digest, 'inspectionReportSha256': sha(report_file), 'workerSha256': sha(__file__),
        'candidateExtractorSha256': sha(extractor), 'candidateExtractionCommand': command,
        'nativeSize': [3840, 2160], 'fps': 24, 'decodedFrames': count, **records,
        'semanticAcceptance': False, 'humanContinuousPlayback': False,
        'scope': 'Extraction only. All120 whole/mechanical/print frames and all detector crops still require actual viewing. Fixed regions must be checked against the actual camera motion; clipped anatomy requires a new wider variant.'}
    preserve(destination / 'manifest.json', (json.dumps(result, indent=2)+'\n').encode('utf-8'))
    print('Complete native4K mechanical evidence extracted; no source or film approval.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--variant', default='native-r1')
    parser.add_argument('--region', required=True, action='append', nargs=5,
                        metavar=('NAME', 'X0', 'Y0', 'X1', 'Y1'))
    args = parser.parse_args()
    regions = {row[0]: [int(value) for value in row[1:]] for row in args.region}
    if len(regions) != len(args.region):
        raise ValueError('Unique region names required')
    inspect(args.directory.resolve(), args.variant, regions)
