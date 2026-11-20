"""Import46 reviewed original shots plus exact new S05 and full-sequence S20.

No HTTP requests or semantic approval. Historical importers stay unchanged.
GPL-3.0-only.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path

EP = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('native4k_v12_import_for_v13',
    Path(__file__).with_name('materialize-native4k-sources-v12.py'))
previous = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(previous)
worker = previous.worker
PREVIOUS_LAYOUT = previous.validate_locked_layout
RERUN_PLAN = EP / 'production-plan-v13-S20-full-sequence-native-4k-r1.json'
RERUN_SHA = '106f0f0ee8e80cd1a4f9362bbf826f2b75a5d43336d550dea9f9fd954f37073a'
RERUN_JOB = 'video_gen_9ff805618a994ab5a4d2b2234cc384de'
RERUN_INPUT = '025d002be5f23377e55054b29db8688b944d0e71cc6066cbdbb0eec9696ae901'
PREVIOUS_ORIGINS = previous.origins


def origins():
    result = PREVIOUS_ORIGINS()
    result['S20'] = ('production-v13-S20-full-sequence-native-4k-001', RERUN_PLAN.name)
    return result


def validate_locked_layout(plan):
    if worker.sha(RERUN_PLAN) != RERUN_SHA:
        raise ValueError('Require the exact separately submitted full-sequence S20 plan')
    expected = copy.deepcopy(worker.read(RERUN_PLAN)['shots'][0])
    expected['startFrame'] = 2250
    if len(plan.get('shots', [])) != 48 or plan['shots'][19] != expected:
        raise ValueError('Only the new exact ten-second S20 may occupy the original75to85second interval')
    if expected['inputSourceSha256'] != RERUN_INPUT:
        raise ValueError('Wrong S20 input')
    # Reuse the complete v12 format/timing and other47-shot checks by presenting
    # its original S20 only for that check. This does not select any source file.
    baseline = copy.deepcopy(plan)
    baseline['shots'][19] = copy.deepcopy(worker.read(previous.OLD_PLAN)['shots'][19])
    PREVIOUS_LAYOUT(baseline)


def build_plan():
    # Preserve the previous importer and all submitted plan bytes.
    plan = previous.build_plan()
    shot = copy.deepcopy(worker.read(RERUN_PLAN)['shots'][0])
    shot['startFrame'] = 2250
    plan['shots'][19] = shot
    plan.update(revision=13,
        sourceContinuation='Assemble46 exact reviewed original native4K sources plus separately accepted newS05 and full-sequence S20; no generation requests.',
        sourceReviewReuse='All selected output bytes, source decisions and complete evidence must match; no oldS05 or oldS20 fallback, no automatic film approval.',
        longShotRerunPlanSha256=RERUN_SHA)
    validate_locked_layout(plan)
    return plan


def validate_origins(base, plan_file):
    validate_locked_layout(worker.read(plan_file))
    # This independently loaded module is used only in this single-threaded
    # import operation. Restore its extension points even on validation failure.
    old_layout, old_origins = previous.validate_locked_layout, previous.origins
    try:
        previous.validate_locked_layout = validate_locked_layout
        previous.origins = origins
        proofs = previous.validate_origins(base, plan_file)
    finally:
        previous.validate_locked_layout, previous.origins = old_layout, old_origins
    origin = Path(base) / origins()['S20'][0]
    job = worker.read(origin / 'jobs/S20.json')
    result = job['remote']['result']
    if (job['jobId'] != RERUN_JOB or result.get('temporal_strategy') != 'full_sequence'
            or result.get('windows') != 1 or result.get('independent_window_fallback') is not False):
        raise ValueError('Require the exact new S20 job and a single full sequence without fallback')
    return proofs


def materialize(base, directory, plan_file):
    proofs = validate_origins(base, plan_file)
    # Full-source/evidence/decisions are checked again before creating outputs.
    worker.materialize(base, directory, plan_file, origins())
    (directory / 'native4k-origin-verification.json').write_text(json.dumps({
        'sourcePlanSha256': worker.sha(plan_file), 'shots': proofs,
        'requiredS20JobId': RERUN_JOB, 'requiredS20Strategy': 'full_sequence',
        'scope': 'Exact already-reviewed selected sources only; final plan and film require independent review.'
    }, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    parser.add_argument('--plan', required=True, type=Path)
    args = parser.parse_args()
    materialize(args.base.resolve(), args.directory.resolve(), args.plan.resolve())
