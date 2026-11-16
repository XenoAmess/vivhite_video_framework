"""Export safe progress and preserved-image inventory; never grants acceptance.

GPL-3.0-only.
"""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime,timezone

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0,str(ROOT/'video-maker/tools'))
from reference_finisher import sha,write_json
from PIL import Image


def export(directory):
    directory = directory.resolve()
    state = json.loads((directory/'run.json').read_text(encoding='utf-8'))
    decisions_file = directory/'clip-decisions.json'
    decisions = json.loads(decisions_file.read_text(encoding='utf-8'))['shots'] if decisions_file.exists() else []
    keys = ('noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle','motionAndContinuity','merchandiseBehavior')
    accepted = [row for row in decisions if row.get('allSourceFrameReview') is True
                and all(row.get(key)=='passed' for key in keys)]
    jobs = []
    for file in sorted((directory/'jobs').glob('S*.json')):
        row = json.loads(file.read_text(encoding='utf-8'))
        jobs.append({key:row.get(key) for key in ('shotId','status','jobId','submittedAt','firstInProgressAt',
                                                'downloadedAt','rawSha256','sourceSha256','requestSha256')})
        jobs[-1]['inferenceSeconds'] = row.get('remote',{}).get('result',{}).get('inference_time_s')
    progress = {'schemaVersion':'vivhite-local-production-progress-1','snapshotAt':datetime.now(timezone.utc).isoformat(),
        'sourcePlanSha256':state['planSha256'],'model':state['model'],'status':state['status'],
        'completedSources':sum(bool(row['sourceSha256']) for row in jobs),'acceptedSources':len(accepted),
        'totalShots':49,'finalFilmDelivered':False,'humanFullPlayback':False,
        'runRelativeToRepositoryParent':directory.relative_to(ROOT.parent).as_posix(),'jobs':jobs,
        'semanticScope':'Only recorded actual source decisions count as accepted. No final film acceptance is implied.'}
    write_json(EP/'production/run-progress-v5.json',progress)
    if decisions_file.exists():
        write_json(EP/'production/clip-decisions-v5-768p.json',json.loads(decisions_file.read_text(encoding='utf-8')))
    images = []
    for path in sorted((EP/'assets/generated').rglob('*')):
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
            continue
        with Image.open(path) as picture:
            size,format_name = list(picture.size),picture.format
        images.append({'path':path.relative_to(EP).as_posix(),'sha256':sha(path),'bytes':path.stat().st_size,
                       'size':size,'format':format_name,'category':'inspection-evidence' if any(part in path.parts for part in ('review','inspection','proxies')) else 'imagegen-artwork'})
    write_json(EP/'production/image-inventory-v5-768p.json',{'schemaVersion':'vivhite-generated-image-inventory-1',
        'scope':'All preserved generated pictures through this in-progress 768P snapshot, including historical and rejected versions. Not a final acceptance receipt.',
        'imageCount':len(images),'totalBytes':sum(item['bytes'] for item in images),'images':images})
    print(json.dumps({'completedSources':progress['completedSources'],'acceptedSources':len(accepted),'images':len(images)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',required=True,type=Path)
    export(parser.parse_args().directory)
