"""Prepare one native4K S05 repair from the actually reviewed v12 768P delivery.

No generation, reordering or automatic semantic approval. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, validate
from reference_finisher import sha, verify_clip_decisions, run
from prepare_local_refinement import refinement_prompt


def prepare(base, directory):
    draft = base / 'production-v12-saddle-768p-full-001'
    delivery_file = EP / 'delivery-plan-v12-768p.json'
    delivery = read(delivery_file)
    final_file = EP / delivery['finalAssemblyPlan']
    final = read(final_file)
    review_file = EP / delivery['finalReview']
    film = draft / 'film.mp4'
    if (sha(film) != delivery['film']['sha256'] or delivery['machineDecodedFinalFrames'] != 6150
            or sha(final_file) != delivery['finalAssemblyPlanSha256']
            or sha(review_file) != delivery['finalReviewSha256']):
        raise ValueError('Require the exact reviewed205-second v12 768P delivery')
    assets = [film, draft / 'soundtrack.wav', draft / 'titles.ass', review_file, final_file]
    command = [sys.executable, str(ROOT / 'scripts/character_review.py'), 'check',
               '--episode', str(EP / 'episode.json'), '--document', str(delivery_file)]
    for asset in assets:
        command.extend(['--asset', str(asset)])
    subprocess.run(command, check=True, timeout=120)
    verify_clip_decisions(final, draft)
    source = draft / 'sources/S05.mp4'
    if sha(source) != 'd814fd0ade3bd7d62857e3366a19ef2ec51b6a74ed3c1b2e0ad2dc5a9caf19bf':
        raise ValueError('Do not reuse the rejected missing-saddle input')
    probe = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams',
                            '-of', 'json', str(source)]))['streams']
    if (len(probe) != 1 or probe[0]['avg_frame_rate'] != '24/1'
            or int(probe[0]['nb_read_frames']) != 120
            or (probe[0]['width'], probe[0]['height']) != (1344, 768)):
        raise ValueError('Exact complete5second120-frame video-only native768P input required')
    destination = EP / 'production-plan-v12-S05-native-4k-r1.json'
    if directory.exists() or destination.exists():
        raise ValueError('Preserve prior plans/runs; choose a new explicitly reviewed revision')
    original = read(EP / 'production-plan-v12-bf16-768p.json')
    old = read(EP / 'production-plan-v11-native-4k.json')
    plan = {key: copy.deepcopy(value) for key, value in old.items() if key != 'shots'}
    shot = copy.deepcopy(next(row for row in original['shots'] if row['id'] == 'S05'))
    shot.update(startFrame=0, inputSource='input-sources/S05.mp4', inputSourceSha256=sha(source))
    for key in ['references', 'generationAction', 'firstFrameRequirement']:
        shot.pop(key, None)
    shot['prompt'] = refinement_prompt(shot) + (
        ' Preserve the existing visible black padded saddle, rear edge and forward nose, metal saddle rails, '
        'fixed clamp and exposed seatpost continuously joined into the existing seat tube. '
        'Keep the existing seated hip support in every frame; do not remove, conceal, float or deform the saddle or seatpost. '
        'Preserve the exact input leg/crank/boot motion, two opposing crank arms about one bottom-bracket axle '
        'and each original sole on its original pedal; do not invent extra cycles, switch feet or detach limbs. '
        'The corrected768P source, rather than any older shot or written idealized cadence, defines every moment.')
    shot['acceptanceCriteria'] = (
        'Actually view all120 native UHD whole frames plus saddle/rails/clamp/seatpost/hips, legs/cranks/boots '
        'and original printed-face details. Reject missing/floating/unsupported seat, changed frame/axle geometry, '
        'foot/pedal separation, extra limb/person/face/reflection, background reset, fixed-print eye distortion '
        'or autonomous blink. Compare the exact adopted768P source. Final placement remains14to19seconds, '
        'five seconds150final frames420to569; all other47timings remain unchanged.')
    plan.update(revision=12, totalFrames=150, titleOverlays=[], closingCredit='',
        shotDurationExceptions={}, director='director-v12.md', shots=[shot],
        draftPlanSha256=sha(EP / 'production-plan-v12-bf16-768p.json'),
        draftDeliverySha256=sha(delivery_file), draftFilmSha256=sha(film),
        sourceReviewReuse='This exact repaired S05 768P input was fully viewed in this session; old missing-saddle source and approval are revoked. No future4K output approved.',
        sourceContinuation='Regenerate only the adopted repaired S05 source in native UHD; do not resubmit other47 jobs.',
        scope='Separate single-shot saddle repair after full768P delivery review; normal shared queue, no preemption, oldv11 plan/requests retained.',
        finalAssemblyPlacement={'id':'S05', 'startFrame':420, 'seconds':5, 'frames':150,
                                'fullFilmSeconds':205, 'fullFilmFrames':6150})
    validate(plan)
    (directory / 'input-sources').mkdir(parents=True)
    shutil.copyfile(source, directory / shot['inputSource'])
    if sha(directory / shot['inputSource']) != sha(source):
        raise ValueError('Input copy changed')
    shutil.copyfile(delivery_file, directory / 'source-draft-delivery.json')
    shutil.copyfile(final_file, directory / 'source-draft-final-plan.json')
    save(destination, plan)
    print('Prepared one native3840x2160 S05 plan; source SHA', sha(source), 'plan SHA', sha(destination))
    print('No HTTP task submitted. The new plan and actual input still require two semantic judgments and a matching receipt.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    arguments = parser.parse_args()
    prepare(arguments.base.resolve(), arguments.directory.resolve())
