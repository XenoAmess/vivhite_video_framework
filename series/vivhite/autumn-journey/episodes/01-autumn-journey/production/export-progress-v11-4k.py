"""Export real native UHD milestones without granting semantic acceptance.

Weights: reviewed inputs 5, downloaded sources 60, source acceptance 20,
final encoding 5, encoded review 7, published release 3. GPL-3.0-only.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

EP = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def export(base,episode_directory=EP,emit=True):
    episode_directory = Path(episode_directory).resolve()
    directory = base/'production-v11-native-4k-001'
    plan = read(episode_directory/'production-plan-v11-native-4k.json')
    decisions = {s['id']:s for s in read(directory/'clip-decisions.json').get('shots',[])}
    selections = read(directory/'source-selections.json')
    rows = []
    completed_frames = accepted_frames = 0
    total_frames = sum(s['sourceSeconds']*24 for s in plan['shots'])
    for shot in plan['shots']:
        job = read(directory/'jobs'/f"{shot['id']}.json")
        completed = job.get('status') == 'completed' and bool(job.get('sourceSha256'))
        decision = decisions.get(shot['id'],{})
        source_digest = job.get('sourceSha256')
        selected = selections.get('selections',{}).get(shot['id'])
        if selected:
            source = (directory/selected['path']).resolve()
            source_digest = (selected['sha256'] if source.is_relative_to(directory.resolve())
                and source.is_file() and sha(source) == selected['sha256']
                and selections.get('sourcePlanSha256') == sha(episode_directory/'production-plan-v11-native-4k.json')
                and selected['parentSha256'] == job.get('sourceSha256') else None)
        accepted = (completed and decision.get('decision') == 'accepted'
            and source_digest is not None and decision.get('sourceSha256') == source_digest
            and decision.get('allSourceFrameReview') is True
            and decision.get('reviewedNativeFrames',0) >= shot['sourceSeconds']*24
            and all(decision.get(key) == 'passed' for key in (
                'noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle',
                'motionAndContinuity','merchandiseBehavior','referenceAppearance')))
        completed_frames += shot['sourceSeconds']*24*completed
        accepted_frames += shot['sourceSeconds']*24*accepted
        rows.append({'id':shot['id'],'jobId':job.get('jobId'),
            'status':job.get('status','not-submitted'),
            'reportedRemoteProgress':job.get('remote',{}).get('progress'),
            'reportedRemoteStage':job.get('remote',{}).get('stage'),
            'completedSource':completed,'acceptedSource':accepted,
            'selectedCorrection':bool(selected),'reviewedSourceSha256':source_digest})
    finish = read(directory/'final-assembly-receipt.json')
    inspection = read(directory/'encoded-film-inspection.json')
    qa = read(episode_directory/'production/final-review-v11-4k.json')
    release = read(episode_directory/'production/release-v11-4k.json')
    final_file = episode_directory/'final-assembly-plan-v11-4k.json'
    final_plan = read(final_file)
    encoded = (finish.get('frames') == 6150 and finish.get('fullAudioVideoDecode') == 'passed'
        and final_plan.get('width') == 3840 and final_plan.get('height') == 2160
        and finish.get('planSha256') == (sha(final_file) if final_file.exists() else None))
    reviewed = (encoded and qa.get('filmSha256') == finish.get('filmSha256')
        and inspection.get('decodedAndComparedFrames') == 6150)
    published = bool(release.get('releaseId')) and release.get('remoteDigestsVerified') is True
    percent = round(5+60*completed_frames/total_frames+20*accepted_frames/total_frames
        +5*encoded+7*reviewed+3*published,2)
    result = {'schemaVersion':'vivhite-native-4k-progress-1','revision':11,
        'snapshotAt':datetime.now(timezone.utc).isoformat(),'overallPercent':percent,
        'totalShots':48,'completedSources':sum(r['completedSource'] for r in rows),
        'acceptedSources':sum(r['acceptedSource'] for r in rows),
        'expectedCompleteSourceFrames':total_frames,'completedSourceFrames':completed_frames,
        'acceptedSourceFrames':accepted_frames,'filmEncoded':encoded,
        'encodedFrameInspectionPercent':round(inspection.get('decodedAndComparedFrames',0)*100/6150,2),
        'releasePublished':published,'width':3840,'height':2160,'fps':30,
        'targetSeconds':205,'targetFrames':6150,
        'submissionWindow':read(directory/'run.json').get('submissionWindow',1),
        'all48TimingsLockedToV10':True,'originalClosingWingCadencePreserved':True,
        'preserved768pRelease':'autumn-journey-v10-768p-20261118',
        'twoKStatus':'stopped-by-user','humanFullPlayback':False,'shots':rows,
        'scope':'Weighted completed work. Server progress is coarse and is not a timing estimate or semantic approval.'}
    technical = read(directory/'technical-preview/receipt.json')
    result['technicalPreviewEncoded'] = technical.get('status') == 'encoded-technical-checks-passed-awaiting-semantic-review'
    result['technicalPreviewIsFormalDelivery'] = False
    destination = episode_directory/'production/run-progress-v11-4k.json'
    partial = destination.with_name(destination.name+f'.{os.getpid()}.partial')
    partial.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    partial.replace(destination)
    if emit:
        print({k:result[k] for k in ('overallPercent','completedSources','acceptedSources','filmEncoded','releasePublished')})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',required=True,type=Path)
    export(parser.parse_args().base.resolve())
