"""Export actual v10 milestones; source counts and review stay separate.

Overall weights: inputs 20, generation 35, source review 15, encode 15,
encoded review 10, published release 5. GPL-3.0-only.
"""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

EP=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def sha(p):
    with p.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def export(base):
    run=base/'production-v10-motion-768p-001'
    job=read(run/'jobs/S01.json')
    source=run/'sources/S01.mp4'
    digest=sha(source) if source.exists() else None
    row=next(iter(read(run/'clip-decisions.json').get('shots',[])),{})
    accepted=(digest is not None and row.get('id')=='S01' and row.get('sourceSha256')==digest
        and row.get('decision')=='accepted' and row.get('allSourceFrameReview') is True
        and all(row.get(k)=='passed' for k in ('noHumanFaces','noAddedPeople','allCharactersFemale',
            'costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance')))
    final=base/'production-v10-bf16-768p-001'
    finish=read(final/'final-assembly-receipt.json')
    inspection=read(final/'encoded-film-inspection.json')
    qa=read(EP/'production/final-review-v10-768p.json')
    release=read(EP/'production/release-v10-768p.json')
    generation=100 if digest else min(99,float(job.get('remote',{}).get('progress',0)))
    encoded=finish.get('frames')==6150 and finish.get('fullAudioVideoDecode')=='passed'
    reviewed=(bool(qa) and qa.get('filmSha256')==finish.get('filmSha256')
              and inspection.get('decodedAndComparedFrames')==6150)
    published=bool(release.get('releaseId')) and release.get('remoteDigestsVerified') is True
    overall=round(20+generation*.35+accepted*15+encoded*15+reviewed*10+published*5,1)
    result={'schemaVersion':'vivhite-single-shot-revision-progress-1','revision':10,
        'snapshotAt':datetime.now(timezone.utc).isoformat(),'jobId':job.get('jobId'),
        'jobStatus':job.get('status','not-submitted'),'generationPercent':generation,
        'completedSources':int(bool(digest)),'acceptedNewSources':int(accepted),
        'sourceSha256':digest,'filmEncoded':encoded,'fullFilmDecodePassed':encoded,
        'encodedFrameInspectionPercent':round(inspection.get('decodedAndComparedFrames',0)*100/6150,2),
        'releasePublished':published,'overallPercent':overall,'all48TimingsUnchangedFromV9':True,
        'targetSeconds':205,'targetFrames':6150,'changedShots':['S01'],
        'leftBackhandRequired':True,'palmFacingCameraAlternativesRejected':True,
        'twoKStatus':'stopped-by-user','fourKStatus':'not-submitted','humanFullPlayback':False,
        'scope':'Weighted work milestones; no metric grants semantic or user aesthetic acceptance.'}
    (EP/'production/run-progress-v10-768p.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print({k:result[k] for k in ('jobStatus','generationPercent','acceptedNewSources','overallPercent','releasePublished')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    export(p.parse_args().base.resolve())
