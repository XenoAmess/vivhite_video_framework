"""Make bound viewing copies of complete frame evidence and native checkpoints.

Inspection only: no video changes or semantic approval. GPL-3.0-only.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

import cv2
from PIL import Image

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def preserve(path, content):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and path.read_bytes() != content:
        raise ValueError('Preserve existing viewing evidence; use a new identity')
    if not path.exists():
        path.write_bytes(content)


def jpeg(path, picture):
    buffer = BytesIO()
    picture.save(buffer,format='JPEG',quality=94)
    preserve(path,buffer.getvalue())


def prepare(directory, identity, source=None, report_file=None):
    if not re.fullmatch(r'S\d{2}',identity):
        raise ValueError('Use an actual episode shot ID')
    source = (source or directory/'sources'/f'{identity}.mp4').resolve()
    report_file = (report_file or directory/'clip-inspection'/f'{identity}.json').resolve()
    if not source.is_relative_to(directory) or not report_file.is_relative_to(directory):
        raise ValueError('Read actual source and inspection evidence inside this run')
    plan_file = EP/'production-plan-v11-native-4k.json'
    plan = json.loads(plan_file.read_text(encoding='utf-8'))
    shot = next(shot for shot in plan['shots'] if shot['id'] == identity)
    expected_frames = shot['sourceSeconds']*24
    report = json.loads(report_file.read_text(encoding='utf-8'))
    digest = sha(source)
    if (report['identity']['sourceSha256'] != digest or report['status'] != 'decoded'
            or report['decodedFrames'] != expected_frames):
        raise ValueError('Require a bound complete-source inspection')
    evidence = EP/'assets/generated/production-v11-native-4k-001/review/viewing-copies'
    evidence.mkdir(parents=True,exist_ok=True)
    pages = []
    for index, entry in enumerate(report['allUsedFrameEvidence']):
        recorded = Path(entry['path'])
        candidates = (recorded,) if recorded.is_absolute() else (EP/recorded,ROOT/recorded)
        matches = {path.resolve() for path in candidates if path.resolve().is_relative_to(EP)
            and path.is_file() and sha(path) == entry['sha256']}
        if len(matches) != 1:
            raise ValueError('Original complete-frame evidence changed')
        original = matches.pop()
        with Image.open(original) as picture:
            viewing = picture.convert('RGB')
            viewing.thumbnail((1680,2400))
            target = evidence/f'{identity}-{digest[:10]}-whole-p{index+1:02}.jpg'
            jpeg(target,viewing)
        pages.append({'originalPath':original.relative_to(EP).as_posix(),
            'originalSha256':entry['sha256'],'path':target.relative_to(EP).as_posix(),
            'sha256':sha(target),'items':entry['items']})
    capture = cv2.VideoCapture(str(source))
    checkpoints = []
    try:
        if (round(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),round(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                round(capture.get(cv2.CAP_PROP_FPS)),round(capture.get(cv2.CAP_PROP_FRAME_COUNT))) != (3840,2160,24,expected_frames):
            raise ValueError('Native UHD full source required')
        indices = sorted({frame for frame in (0,24,48,72,95,119,167,239,287,335,expected_frames-1) if frame < expected_frames})
        for frame_number in indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES,frame_number)
            ok, frame = capture.read()
            if not ok:
                raise ValueError('Cannot decode native checkpoint')
            target = evidence/f'{identity}-{digest[:10]}-native-f{frame_number:03}.jpg'
            jpeg(target,Image.fromarray(cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
            checkpoints.append({'frame':frame_number,'path':target.relative_to(EP).as_posix(),'sha256':sha(target)})
    finally:
        capture.release()
    if sum(page['items'] for page in pages) != expected_frames or sha(source) != digest:
        raise ValueError('Viewing pages do not cover the unchanged full source')
    manifest = {'schemaVersion':'vivhite-source-viewing-copies-1','sourcePlanSha256':sha(plan_file),
        'sourceSha256':digest,'inspectionSha256':sha(report_file),'workerSha256':sha(__file__),
        'nativeFrames':expected_frames,'pages':pages,'nativeCheckpoints':checkpoints,
        'semanticAcceptance':'not-granted','humanFullPlayback':False,
        'scope':'Viewing copies only. Full-scene pages and native checkpoints have different coverage.'}
    preserve(evidence/f'{identity}-{digest[:10]}.json',(json.dumps(manifest,indent=2)+'\n').encode())
    print(identity,expected_frames,'frames represented;',len(pages),'viewing pages; no acceptance granted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    parser.add_argument('--shot',required=True)
    parser.add_argument('--source',type=Path)
    parser.add_argument('--report',type=Path)
    args = parser.parse_args()
    prepare(args.directory.resolve(),args.shot,args.source,args.report)
