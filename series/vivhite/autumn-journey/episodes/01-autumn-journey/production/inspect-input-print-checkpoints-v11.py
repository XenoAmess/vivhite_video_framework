"""Extract first-frame input artwork checks; never approve a 4K output.

Existing 768p inputs and the submitted plan remain unchanged. GPL-3.0-only.
"""
import argparse
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import sys

import cv2
from PIL import Image, ImageDraw, ImageFont, ImageOps

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from local_video_pipeline import read, save


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def preserve_image(path, picture):
    buffer = BytesIO()
    picture.save(buffer,format='PNG')
    data = buffer.getvalue()
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Preserve existing evidence; use a new evidence identity')
    if not path.exists():
        path.write_bytes(data)


def inspect(directory):
    plan_file = EP/'production-plan-v11-native-4k.json'
    plan = read(plan_file)
    shots = {shot['id']:shot for shot in plan['shots']}
    regions_file = directory/'metadata/input-print-region-origins.json'
    regions = read(regions_file)
    evidence = EP/'assets/generated/production-v11-native-4k-001/review/input-print-checkpoints'
    evidence.mkdir(parents=True,exist_ok=True)
    pictures, records = [], []
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for ordinal, region in enumerate(regions):
        shot = shots[region['id']]
        source = directory/shot['inputSource']
        if sha(source) != shot['inputSourceSha256']:
            raise ValueError('The approved actual input changed: '+shot['id'])
        capture = cv2.VideoCapture(str(source))
        try:
            ok, frame = capture.read()
        finally:
            capture.release()
        if not ok or frame.shape[:2] != (768,1344):
            raise ValueError('Expected the approved 1344x768 input frame')
        x,y = region['center']
        radius = math.ceil(region['radius']*1.3)
        box = [max(0,x-radius),max(0,y-radius),min(1344,x+radius),min(768,y+radius)]
        crop = Image.fromarray(cv2.cvtColor(frame[box[1]:box[3],box[0]:box[2]],cv2.COLOR_BGR2RGB))
        identity = f"{shot['id']}-region{ordinal+1:02}-{shot['inputSourceSha256'][:10]}"
        crop_file = evidence/(identity+'-f000.png')
        preserve_image(crop_file,crop)
        cell = Image.new('RGB',(350,390),'#242424')
        draw = ImageDraw.Draw(cell)
        draw.text((8,6),identity,font=font,fill='white')
        draw.text((8,31),'768p INPUT f000 only',font=font,fill='white')
        # This labeled enlargement is for inspection, not new reference art.
        enlarged = ImageOps.contain(crop,(320,320),Image.Resampling.LANCZOS)
        cell.paste(enlarged,((350-enlarged.width)//2,65+(320-enlarged.height)//2))
        pictures.append(cell)
        historical_name = Path(region['file']).name
        detail_master = shot.get('designMaster')
        if '-badge-' in historical_name:
            detail_master = 'assets/generated/production-v2-fasth3-001/masters/M05-badge-v1.png'
        elif '-plush-' in historical_name:
            detail_master = 'assets/generated/production-v2-fasth3-001/masters/M04-plush-v1.png'
        records.append({'shotId':shot['id'],'regionOrdinal':ordinal+1,
            'sourceSha256':shot['inputSourceSha256'],'frame':0,'inputSize':[1344,768],
            'box':box,'cropPath':crop_file.relative_to(EP).as_posix(),'cropSha256':sha(crop_file),
            'historicalRegionMetadata':Path(region['file']).as_posix(),
            'shotDesignMaster':shot.get('designMaster'),'detailMaster':detail_master,
            'detailMasterBasis':'Historical region label when badge/plush is explicit; otherwise shot design master.',
            'actualOutputReview':False})
    pages = []
    for offset in range(0,len(pictures),12):
        batch = pictures[offset:offset+12]
        canvas = Image.new('RGB',(1400,math.ceil(len(batch)/4)*390),'#242424')
        for index, cell in enumerate(batch):
            canvas.paste(cell,((index%4)*350,(index//4)*390))
        file = evidence/f'input-print-first-frame-aspect-p{offset//12+1:02}.png'
        preserve_image(file,canvas)
        pages.append({'path':file.relative_to(EP).as_posix(),'sha256':sha(file),'items':len(batch)})
    save(evidence/'manifest-aspect-v3.json',{'schemaVersion':'vivhite-input-print-spot-check-1',
        'sourcePlanSha256':sha(plan_file),'workerSha256':sha(__file__),
        'regionsMetadataSha256':sha(regions_file),'regions':records,'pages':pages,
        'coverage':'Only the first frame of each existing input print region. Not full-motion or 4K-output review.',
        'semanticAcceptance':'not-granted','originalInputsUnchanged':True})
    print(len(records),'input print checkpoints;',len(pages),'pages; no output acceptance granted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    inspect(parser.parse_args().directory.resolve())
