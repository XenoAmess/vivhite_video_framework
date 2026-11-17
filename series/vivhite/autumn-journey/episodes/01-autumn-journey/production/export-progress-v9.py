"""Export actual two-shot progress without granting acceptance. GPL-3.0-only."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path

EP=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def export(base):
    run=base/'production-v9-motion-768p-001';decisions=read(run/'clip-decisions.json')
    selections=read(run/'source-selections.json').get('selections',{})
    shots=[]
    for sid in ('S44','S47'):
        job=read(run/'jobs'/f'{sid}.json')
        selection=selections.get(sid,{})
        source=(run/selection.get('path',f'sources/{sid}.mp4')).resolve()
        digest=sha(source) if source.is_relative_to(run.resolve()) and source.exists() else None
        row=next((r for r in decisions.get('shots',[]) if r['id']==sid),{})
        accepted=(digest is not None and digest==row.get('sourceSha256')
            and row.get('decision')=='accepted' and row.get('allSourceFrameReview') is True
            and all(row.get(k)=='passed' for k in ('noHumanFaces','noAddedPeople','allCharactersFemale',
                'costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance')))
        shots.append({'id':sid,'jobId':job.get('jobId'),'status':job.get('status','not-submitted'),
            'selectedSourceSha256':digest,'completeSourceAccepted':accepted,'finalSeconds':4,'sourceSeconds':5})
    complete=sum(bool(s['selectedSourceSha256']) for s in shots);accepted=sum(s['completeSourceAccepted'] for s in shots)
    finished=read(base/'production-v9-bf16-768p-001/final-assembly-receipt.json')
    inspection=read(base/'production-v9-bf16-768p-001/encoded-film-inspection.json')
    release=read(EP/'production/release-v9-768p.json')
    result={'schemaVersion':'vivhite-two-shot-revision-progress-1','snapshotAt':datetime.now(timezone.utc).isoformat(),
        'revision':9,'shots':shots,'completedSources':complete,'acceptedNewSources':accepted,
        'generationPercent':complete*50,'acceptancePercent':accepted*50,
        'all48TimingsUnchangedFromV8':True,'targetSeconds':205,'targetFrames':6150,
        'durationDisplayConfirmedCorrectByUser':True,'nativeClosingWingsUnchanged':True,
        'filmEncoded':finished.get('frames')==6150,'fullFilmDecodePassed':finished.get('fullAudioVideoDecode')=='passed',
        'encodedFrameInspectionPercent':round(inspection.get('decodedAndComparedFrames',0)*100/6150,2),
        'releasePublished':bool(release.get('releaseId')),'twoKStatus':'stopped-by-user','fourKStatus':'not-submitted',
        'humanFullPlayback':False,'scope':'Source generation, source acceptance, encoded film and published release are separate milestones.'}
    (EP/'production/run-progress-v9-768p.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print({k:result[k] for k in ('completedSources','acceptedNewSources','generationPercent','acceptancePercent','releasePublished')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',type=Path,required=True)
    export(p.parse_args().base.resolve())
