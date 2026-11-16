"""Record an explicit reviewer decision after viewing every full-source frame.

No face detector or threshold supplies semantic acceptance. GPL-3.0-only.
"""
import argparse
from pathlib import Path

from local_video_pipeline import read,save,now,contained,source_frame_count
from reference_finisher import sha


def record(plan_file,directory,identity,observation,accepted,all_frames_viewed,failed_checks=None,reference_fidelity_reviewed=False):
    if not all_frames_viewed or not observation.strip():
        raise ValueError('Actual all-frame review and its concrete observation are required')
    plan = read(plan_file)
    shot = next(row for row in plan['shots'] if row['id']==identity)
    expected_frames = source_frame_count(shot)
    if plan.get('referenceAppearanceRequired') and accepted and not reference_fidelity_reviewed:
        raise ValueError('Explicit actual comparison with the original artwork is required')
    selections_file = Path(directory)/'source-selections.json'
    selected = read(selections_file)['selections'].get(identity) if selections_file.exists() else None
    source = contained(directory,selected['path'] if selected else f'sources/{identity}.mp4')
    if selected:
        parent = contained(directory,selected['parent'])
        contained(directory,selected['receipt'])
        if sha(source) != selected['sha256'] or sha(parent) != selected['parentSha256']:
            raise ValueError('Selected correction or parent changed')
    report = read(contained(directory,selected.get('inspectionReport',f'clip-inspection/{identity}.json')
                            if selected else f'clip-inspection/{identity}.json'))
    if (report['identity']['sourceSha256'] != sha(source) or report['usedFramesAnalysed'] != expected_frames
            or report['identity']['usedSeconds'] != shot.get('sourceSeconds',5)):
        raise ValueError('Review evidence must cover the exact complete actual source')
    file = Path(directory)/'clip-decisions.json'
    decisions = read(file) if file.exists() else {'schemaVersion':'vivhite-clip-decisions-1',
        'sourcePlanSha256':sha(plan_file),'shots':[]}
    if decisions['sourcePlanSha256'] != sha(plan_file):
        raise ValueError('Changed source plan requires independent new review records')
    checks = ('noHumanFaces','noAddedPeople','allCharactersFemale','costumeStyle','motionAndContinuity','merchandiseBehavior')
    if plan.get('referenceAppearanceRequired') or reference_fidelity_reviewed:
        checks += ('referenceAppearance',)
    if not accepted and (not failed_checks or any(key not in checks for key in failed_checks)):
        raise ValueError('A rejection must name the actually failed checks')
    row = {'id':identity,'sourceSha256':sha(source),'method':'assistant-frame-review','reviewedAt':now(),
        'allSourceFrameReview':True,'allUsedFrameReview':True,'reviewedNativeFrames':expected_frames,
        'actualFinalUsedNativeFrames':shot['seconds']*24,'frameEvidence':report['allUsedFrameEvidence'],
        'faceEvidence':report['faceEvidence'],'observation':observation,
        'decision':'accepted' if accepted else 'rejected',
        **{key:'failed' if key in (failed_checks or []) else 'passed' for key in checks}}
    if reference_fidelity_reviewed:
        row['referenceAppearance'] = 'failed' if 'referenceAppearance' in (failed_checks or []) else 'passed'
    if plan.get('referenceAppearanceRequired') and not reference_fidelity_reviewed and 'referenceAppearance' not in (failed_checks or []):
        row['referenceAppearance'] = 'pending'
    existing = next((item for item in decisions['shots'] if item['id']==identity),None)
    if existing:
        history = Path(directory)/'review-history'/f'{identity}-{sha(file)[:12]}.json'
        save(history,existing)
        decisions['shots'].remove(existing)
    decisions['shots'].append(row)
    order = [item['id'] for item in plan['shots']]
    decisions['shots'].sort(key=lambda item:order.index(item['id']))
    save(file,decisions)
    print(f"Recorded actual {'acceptance' if accepted else 'rejection'} for {identity}; no final-film or human-playback claim.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--shot',required=True)
    parser.add_argument('--observation',required=True)
    parser.add_argument('--decision',choices=('accept','reject'),required=True)
    parser.add_argument('--all-frames-viewed',action='store_true',required=True)
    parser.add_argument('--reference-fidelity-reviewed',action='store_true')
    parser.add_argument('--failed-check',action='append',choices=('noHumanFaces','noAddedPeople','allCharactersFemale',
        'costumeStyle','motionAndContinuity','merchandiseBehavior','referenceAppearance'),default=[])
    args = parser.parse_args()
    record(args.plan,args.directory,args.shot,args.observation,args.decision=='accept',args.all_frames_viewed,args.failed_check,args.reference_fidelity_reviewed)
