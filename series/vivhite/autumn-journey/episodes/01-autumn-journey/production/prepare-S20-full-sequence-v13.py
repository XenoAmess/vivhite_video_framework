"""Prepare a separate ten-second S20 rerun after actual usable S48 review.

No HTTP submission or automatic semantic approval. GPL-3.0-only.
"""
import argparse
import copy
from pathlib import Path
import shutil
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from local_video_pipeline import read, save, validate
from reference_finisher import sha


def prepare(original_directory, directory):
    old_plan_file = EP / 'production-plan-v11-native-4k.json'
    if sha(old_plan_file) != '5797a7ea8d61e53b5ce7372a57fcce24cb8d924225a7c3760333651a2eda50fa':
        raise ValueError('Original submitted plan changed')
    ending_file = EP / 'production/S48-full-sequence-source-review-v11-4k.json'
    ending = read(ending_file)
    if (ending['decision']['decision'] != 'accepted'
            or ending['wholeSceneFramesActuallyViewed'] != 336
            or ending['nativeButterflyFramesActuallyViewed'] != 336
            or ending['serverResult']['temporal_strategy'] != 'full_sequence'
            or ending['serverResult']['windows'] != 1
            or ending['serverResult']['independent_window_fallback'] is not False
            or sha(original_directory / 'sources/S48.mp4') != ending['sourceSha256']):
        raise ValueError('Require the actually reviewed usable full-sequence ending')
    original = read(old_plan_file)
    shot = copy.deepcopy(next(s for s in original['shots'] if s['id'] == 'S20'))
    source = original_directory / shot['inputSource']
    if sha(source) != '025d002be5f23377e55054b29db8688b944d0e71cc6066cbdbb0eec9696ae901':
        raise ValueError('Use the original complete adopted768P input, not an old multi-window4K output')
    destination = EP / 'production-plan-v13-S20-full-sequence-native-4k-r1.json'
    if directory.exists() or destination.exists():
        raise ValueError('Preserve existing runs/plans; do not prepare over an earlier attempt')
    shot['startFrame'] = 0
    shot['prompt'] = shot['prompt'].replace(
        'do not restart, freeze, loop or replace the view at a window boundary.',
        'do not restart, freeze, loop or replace the view during the complete ten-second sequence.')
    shot['prompt'] += (
        ' Preserve the same dark fabric shoulder bag, its attached round original character badge and the '
        'same supported seated plush on the same rock. The plush is a passive fabric object, not a living '
        'character: no independent nod, head turn, limb gesture, facial animation or blinking. Preserve '
        'the original sewn open violet-pink eye patterns, fine round gold glasses and small smile on both '
        'the doll and badge. Preserve their original camera-relative perspective and the complete original '
        'slow pullback, lake ripples, clouds and mountain contours continuously for all ten seconds.')
    shot['acceptanceCriteria'] = (
        'Require actual server result temporal_strategy=full_sequence, windows=1 and '
        'independent_window_fallback=false. Decode and actually review all240 native3840x2160 source frames '
        'plus original doll/body/eyes/glasses and round badge details. Reject scene reset, cuts, autonomous '
        'toy nod/gesture/blink, deforming print, new person/face/reflection/limb, added foreground prop or '
        'a multi-video-window fallback. Preserve full ten seconds75to85 and final frames2250to2549. '
        'This input review does not approve any future output.')
    plan = {k: copy.deepcopy(v) for k, v in original.items() if k != 'shots'}
    plan.update(revision=13, totalFrames=300, shots=[shot], titleOverlays=[], closingCredit='',
        shotDurationExceptions={'S20': 10}, director='director-v12.md',
        sourceReviewReuse='All240 actual768P whole frames and native first whole were reread for this request; no new4K output approved.',
        sourceContinuation='Rerun only S20 on the new server full-sequence backend; append at ordinary queue tail.',
        scope='Separate user-requested continuous10second nativeUHD rerun after usableS48 review. Preserve all old versions; no preemption or other-shot duration changes.',
        sourcePlanSha256=sha(old_plan_file),
        usableEndingReviewSha256=sha(ending_file),
        requiredServerResult={'temporal_strategy': 'full_sequence', 'windows': 1,
                              'independent_window_fallback': False},
        finalAssemblyPlacement={'id': 'S20', 'startFrame': 2250, 'seconds': 10, 'frames': 300,
                                'fullFilmSeconds': 205, 'fullFilmFrames': 6150})
    validate(plan)
    (directory / 'input-sources').mkdir(parents=True)
    shutil.copyfile(source, directory / shot['inputSource'])
    assert sha(directory / shot['inputSource']) == shot['inputSourceSha256']
    save(destination, plan)
    print('Prepared only S20; input SHA', sha(source), 'plan SHA', sha(destination))
    print('No HTTP submission; new plan and actual input require matching semantic-review receipt/check.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-directory', required=True, type=Path)
    parser.add_argument('--directory', required=True, type=Path)
    args = parser.parse_args()
    prepare(args.original_directory.resolve(), args.directory.resolve())
