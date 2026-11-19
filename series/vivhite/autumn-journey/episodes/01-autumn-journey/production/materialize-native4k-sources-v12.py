"""Import47 reviewed native4K sources plus the separately reviewed S05 repair.

No API requests or automatic approval. Final plan and film need their own review.
GPL-3.0-only.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

import cv2

EP = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native4k_reviewed_source_import',
    Path(__file__).with_name('materialize-sources-v6.py'))
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)
OLD_PLAN = EP / 'production-plan-v11-native-4k.json'
REPAIR_PLAN = EP / 'production-plan-v12-S05-native-4k-r1.json'
OLD_SHA = '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa'
REPAIR_SHA = 'f7d10a7c80e72a02bbf541b4109871be0e4845653c4ada12075e4b9de6b63842'
INPUT_SHA = 'd814fd0ade3bd7d62857e3366a19ef2ec51b6a74ed3c1b2e0ad2dc5a9caf19bf'


def origins():
    return {f'S{number:02}': ('production-v12-S05-native-4k-001', REPAIR_PLAN.name) if number == 5
            else ('production-v11-native-4k-001', OLD_PLAN.name) for number in range(1, 49)}


def build_plan():
    """Construct an unapproved candidate only; never edit submitted plans."""
    if worker.sha(OLD_PLAN) != OLD_SHA or worker.sha(REPAIR_PLAN) != REPAIR_SHA:
        raise ValueError('Submitted origin plans changed')
    plan = copy.deepcopy(worker.read(OLD_PLAN))
    repaired = copy.deepcopy(worker.read(REPAIR_PLAN)['shots'][0])
    repaired['startFrame'] = 420
    plan['shots'][4] = repaired
    plan.update(revision=12, director='director-v12.md', assemblyOnly=True,
        sourceContinuation='Assemble47 actually accepted native4K sources plus the separately accepted repaired S05; no generation requests here.',
        sourceReviewReuse='Exact already-viewed selected bytes only. Pending remaining source and final assembly review; no automatic content approval.',
        draftPlanSha256=worker.sha(EP / 'production-plan-v12-bf16-768p.json'))
    validate_locked_layout(plan)
    return plan


def validate_locked_layout(plan):
    if worker.sha(OLD_PLAN) != OLD_SHA or worker.sha(REPAIR_PLAN) != REPAIR_SHA:
        raise ValueError('Require immutable original and repair plans')
    baseline, repair = worker.read(OLD_PLAN), worker.read(REPAIR_PLAN)
    worker.validate(plan)
    protected = ('model', 'stage', 'fps', 'width', 'height', 'sourceSize', 'sourceFps',
                 'maxShotSeconds', 'totalFrames', 'titleOverlays', 'closingCredit',
                 'shotDurationExceptions', 'noSpeech', 'noHumanFaces', 'noAddedPeople', 'allCharactersFemale')
    if plan.get('assemblyOnly') is not True or any(plan.get(key) != baseline.get(key) for key in protected):
        raise ValueError('Keep the205-second native4K format, policy, titles and dedication unchanged')
    timing = lambda value: [(row['id'], row['seconds'], row['startFrame'], row['sourceSeconds']) for row in value['shots']]
    if len(plan['shots']) != 48 or timing(plan) != timing(baseline):
        raise ValueError('Keep all48 original shot positions and lengths unchanged')
    if any(row != old for row, old in zip(plan['shots'], baseline['shots']) if row['id'] != 'S05'):
        raise ValueError('Do not change the other47 original source instructions')
    expected = copy.deepcopy(repair['shots'][0])
    expected['startFrame'] = 420
    if plan['shots'][4] != expected or expected['inputSourceSha256'] != INPUT_SHA:
        raise ValueError('Only the exact separate repaired S05 may replace the old missing-saddle shot')


def validate_origins(base, plan_file):
    plan = worker.read(plan_file)
    validate_locked_layout(plan)
    _, _, rows = worker.collect(base, plan_file, origins())
    proofs = []
    for shot, row in zip(plan['shots'], rows):
        identity = shot['id']
        origin = base / row['originRun']
        job = row['originJobReceipt']
        selection = row['selection']
        expected = worker.source_frame_count(shot)
        remote, request_file = job.get('remote', {}), origin / 'requests' / (identity + '.json')
        result, request = remote.get('result', {}), worker.read(request_file)
        original_plan = worker.read(EP / row['originPlan'])
        original_shot = next(item for item in original_plan['shots'] if item['id'] == identity)
        if (row['originalVisualDecision'].get('decision') != 'accepted'
                or job.get('status') != 'completed' or remote.get('status') != 'completed'
                or job.get('shotId') != identity or job.get('planSha256') != row['originPlanSha256']
                or remote.get('id') != job.get('jobId') or remote.get('size') != '3840x2160'
                or remote.get('model') != 'open-h3-2k'
                or any(result.get(key) != value for key, value in {'width':3840, 'height':2160,
                    'fps':24, 'frames':expected, 'native_resolution':'4k'}.items())
                or worker.sha(request_file) != job.get('requestSha256')
                or any(request.get(key) != value for key, value in {'model':'open-h3-2k',
                    'size':'3840x2160', 'sampler':'up3', 'seed':1234}.items())
                or request.get('prompt') != original_shot['prompt']):
            raise ValueError(f'{identity}: complete accepted native4K origin and exact request required')
        actual_input = worker.contained(origin, original_shot['inputSource'])
        raw = worker.contained(origin, job['rawFile'])
        normalized = worker.contained(origin, job['sourceFile'])
        parent_hash = selection['parentSha256'] if selection else row['sha256']
        if (worker.sha(actual_input) != original_shot['inputSourceSha256']
                or shot['inputSourceSha256'] != original_shot['inputSourceSha256']
                or worker.sha(raw) != job.get('rawSha256') or worker.sha(raw) != result.get('sha256')
                or worker.sha(normalized) != job.get('sourceSha256') or worker.sha(normalized) != parent_hash):
            raise ValueError(f'{identity}: changed actual input, downloaded raw or normalized parent')
        report_file = worker.contained(origin, selection['inspectionReport'] if selection else f'clip-inspection/{identity}.json')
        report = worker.read(report_file)
        if (report.get('status') != 'decoded' or report.get('sourceFps') != 24
                or report.get('decodedFrames') != expected or report.get('usedFramesAnalysed') != expected):
            raise ValueError(f'{identity}: complete24fps inspection required')
        if selection and (worker.sha(worker.contained(origin, selection['receipt'])) != selection['receiptSha256']
                          or worker.sha(report_file) != selection['inspectionReportSha256']):
            raise ValueError(f'{identity}: selected correction receipt or inspection changed')
        capture = cv2.VideoCapture(str(row['source']))
        try:
            actual = tuple(round(capture.get(key)) for key in (cv2.CAP_PROP_FRAME_WIDTH,
                cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS, cv2.CAP_PROP_FRAME_COUNT))
        finally:
            capture.release()
        if actual != (3840, 2160, 24, expected):
            raise ValueError(f'{identity}: actual native4K full source geometry differs')
        if identity == 'S05' and (original_shot['inputSourceSha256'] != INPUT_SHA
                or job['jobId'] != 'video_gen_ab78089d679c4c66ba653410717fc5f5' or result.get('windows') != 1):
            raise ValueError('Never fall back to the rejected old S05 or a different repair job')
        proofs.append({'id':identity, 'jobId':job['jobId'], 'originPlanSha256':row['originPlanSha256'],
            'requestSha256':worker.sha(request_file), 'inputSourceSha256':worker.sha(actual_input),
            'downloadedRawSha256':worker.sha(raw), 'normalizedParentSha256':worker.sha(normalized),
            'selectedSourceSha256':row['sha256'], 'inspectionReportSha256':worker.sha(report_file),
            'nativeFrames':expected, 'nativeSize':[3840,2160], 'fps':24})
    return proofs


def materialize(base, directory, plan_file):
    proofs = validate_origins(base, plan_file)
    # The existing importer repeats source/decision/evidence hash validation before copying.
    worker.materialize(base, directory, plan_file, origins())
    output = directory / 'native4k-origin-verification.json'
    output.write_text(json.dumps({'sourcePlanSha256':worker.sha(plan_file), 'shots':proofs,
        'scope':'Exact previously reviewed sources imported. No new semantic or final-film approval.'}, indent=2)+'\n',
        encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    args = parser.parse_args()
    materialize(args.base.resolve(), args.directory.resolve(), args.plan.resolve())
