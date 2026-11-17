"""Copy already reviewed, unchanged source bytes into a separate v6 assembly run.

Does not generate or approve media. The final plan still needs its own semantic
and character binding review. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import contained, read, source_frame_count, validate
from reference_finisher import sha

ORIGINS = {
    'S17': ('production-v5-bf16-768p-S17-image-only-003', 'production-plan-v5-S17-image-only-r3.json'),
    'S20': ('production-v6-bf16-768p-S20-001', 'production-plan-v6-S20-image-only-r1.json'),
    'S29': ('production-v6-bf16-768p-S29-image-only-001', 'production-plan-v6-S29-image-only-r1.json'),
    'S43': ('production-v6-bf16-768p-S43-image-only-001', 'production-plan-v6-S43-image-only-r1.json'),
}
DEFAULT = ('production-v5-bf16-768p-002', 'production-plan-v5-bf16-768p-r2.json')
CHECKS = ('noHumanFaces', 'noAddedPeople', 'allCharactersFemale', 'costumeStyle',
          'motionAndContinuity', 'merchandiseBehavior', 'referenceAppearance')


def collect(base, plan_file=None, origins=None):
    plan_file = Path(plan_file) if plan_file is not None else EP / 'production-plan-v6-bf16-768p.json'
    origins = ORIGINS if origins is None else origins
    plan = read(plan_file)
    validate(plan)
    rows = []
    for shot in plan['shots']:
        identity = shot['id']
        run_name, original_plan_name = origins.get(identity, DEFAULT)
        origin = base / run_name
        original_plan = EP / original_plan_name
        decisions = read(origin / 'clip-decisions.json')
        row = next((item for item in decisions['shots'] if item['id'] == identity), {})
        selections = origin / 'source-selections.json'
        selection = read(selections)['selections'].get(identity) if selections.exists() else None
        try:
            source = contained(origin, selection['path'] if selection else f'sources/{identity}.mp4')
        except ValueError as error:
            raise ValueError(f'{identity}: complete actual source is not available') from error
        digest = sha(source)
        expected = source_frame_count(shot)
        if (decisions['sourcePlanSha256'] != sha(original_plan)
                or row.get('sourceSha256') != digest or row.get('decision') == 'rejected'
                or row.get('method') != 'assistant-frame-review'
                or row.get('allSourceFrameReview') is not True
                or row.get('allUsedFrameReview') is not True
                or row.get('reviewedNativeFrames') != expected
                or any(row.get(key) != 'passed' for key in CHECKS)):
            raise ValueError(f'No exact complete accepted source and original-artwork review for {identity}')
        if sum(item['items'] for item in row['frameEvidence']) != expected:
            raise ValueError(f'Incomplete source frame evidence for {identity}')
        for evidence in row['frameEvidence']:
            if sha(evidence['path']) != evidence['sha256']:
                raise ValueError(f'Changed actual frame evidence for {identity}')
        processing = []
        if selection:
            if digest != selection['sha256'] or sha(contained(origin, selection['parent'])) != selection['parentSha256']:
                raise ValueError(f'Changed selected correction or parent for {identity}')
            for path in dict.fromkeys([selection['receipt'], *selection.get('processingChain', [])]):
                receipt = contained(origin, path)
                processing.append({'path': path, 'sha256': sha(receipt), 'receipt': read(receipt)})
        report = contained(origin, selection.get('inspectionReport', f'clip-inspection/{identity}.json')
                           if selection else f'clip-inspection/{identity}.json')
        inspected = read(report)
        if (inspected['identity']['sourceSha256'] != digest
                or inspected['usedFramesAnalysed'] != expected):
            raise ValueError(f'Stale inspection report for {identity}')
        generation_job = contained(origin, selection.get('generationJobReceipt', f'jobs/{identity}.json')
                                   if selection else f'jobs/{identity}.json')
        job = read(generation_job)
        if selection and selection.get('generationPlan'):
            if sha(contained(origin, selection['generationPlan'])) != job.get('planSha256'):
                raise ValueError(f'Changed imported original generation plan for {identity}')
        rows.append({'id': identity, 'source': source, 'sha256': digest,
                     'originRun': run_name, 'originPlan': original_plan_name,
                     'originPlanSha256': sha(original_plan), 'originSource': source.relative_to(origin).as_posix(),
                     'originalVisualDecision': row, 'selection': selection,
                     'processingReceipts': processing, 'inspectionReportSha256': sha(report),
                     'originJobReceipt': job,
                     'generationJobReceiptSha256': sha(generation_job)})
    return plan_file, plan, rows


def materialize(base, directory, plan_file=None, origins=None):
    base, directory = Path(base).resolve(), Path(directory).resolve()
    # Validate the complete batch before creating or copying anything.
    plan_file, plan, rows = collect(base, plan_file, origins)
    if directory.exists():
        raise ValueError('Preserve the existing run; choose a new assembly directory')
    if any(directory.is_relative_to(base / row['originRun']) for row in rows):
        raise ValueError('The new assembly must be separate from every generation run')
    (directory / 'sources').mkdir(parents=True)
    transferred, provenance = [], []
    for shot, item in zip(plan['shots'], rows):
        source = item.pop('source')
        target = directory / 'sources' / f"{item['id']}.mp4"
        shutil.copyfile(source, target)
        if sha(target) != item['sha256']:
            raise ValueError('A copied source changed; partial run retained for inspection')
        decision = copy.deepcopy(item['originalVisualDecision'])
        decision['actualFinalUsedNativeFrames'] = shot['seconds'] * 24
        decision['reusedVisualDecision'] = {
            'originRun': item['originRun'], 'originPlanSha256': item['originPlanSha256'],
            'scope': 'Same already-viewed bytes only; no new visual, persona or final-film approval.'}
        transferred.append(decision)
        provenance.append(item)
    def write(name, value):
        (directory / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    write('clip-decisions.json', {'schemaVersion': 'vivhite-clip-decisions-1',
          'sourcePlanSha256': sha(plan_file), 'shots': transferred,
          'scope': 'Transferred actual same-byte source decisions. Final plan semantic review remains required.'})
    write('source-imports.json', {'schemaVersion': 'vivhite-source-imports-1',
          'targetPlanSha256': sha(plan_file), 'shots': provenance, 'humanFullPlayback': False,
          'scope': 'No API requests submitted here. All originals, job receipts and failures remain in origin runs.'})
    print(f'Materialized {len(rows)} complete reviewed sources; no film or new semantic approval is implied.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    materialize(args.base, args.directory)
