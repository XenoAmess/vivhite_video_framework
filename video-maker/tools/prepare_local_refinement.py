"""Prepare per-shot 2K inputs after the reviewed 768p film has been delivered.

Does not submit jobs or manufacture review decisions. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

from local_video_pipeline import validate,read,save
from reference_finisher import sha,run,verify_clip_decisions


def prepare(episode,draft_plan,draft_directory,delivery_file,directory,destination,root):
    draft_directory,directory = Path(draft_directory).resolve(),Path(directory).resolve()
    if draft_directory == directory or directory.is_relative_to(draft_directory) or draft_directory.is_relative_to(directory):
        raise ValueError('Keep 2K and draft runs separate')
    delivery = read(delivery_file)
    film = draft_directory/'film.mp4'
    if (delivery.get('schemaVersion') != 'vivhite-delivery-plan-1' or sha(film) != delivery['film']['sha256']
            or delivery.get('machineDecodedFinalFrames') != delivery['film']['frames']):
        raise ValueError('An actual completed 768p delivery is required before 2K')
    print(run([sys.executable,str(Path(root).resolve()/'scripts/character_review.py'),'check',
               '--episode',str(Path(episode).resolve()),'--document',str(Path(delivery_file).resolve()),
               '--asset',str(film)],timeout=120))
    original = read(draft_plan)
    validate(original)
    final_file = Path(delivery_file).resolve().parent/delivery['finalAssemblyPlan']
    if sha(final_file) != delivery['finalAssemblyPlanSha256']:
        raise ValueError('768p assembly binding changed')
    final = read(final_file)
    verify_clip_decisions(final,draft_directory)
    source_hashes = {item['path']:item['sha256'] for item in final['files']}
    decisions = {row['id']:row for row in read(draft_directory/'clip-decisions.json')['shots']}
    directory.mkdir(parents=True,exist_ok=True)
    (directory/'input-sources').mkdir(exist_ok=True)
    plan = copy.deepcopy(original)
    plan['draftGenerationMetadata'] = {key:plan.pop(key) for key in
        ('numInferenceSteps','decoderLayers','decoderVerification') if key in plan}
    plan.update(stage='refine',model='open-h3-2k',width=2560,height=1440,sourceSize='2560x1440',
                refinementSeed=1234,sampler='up3',draftPlanSha256=sha(draft_plan),
                draftDeliverySha256=sha(delivery_file),draftFilmSha256=sha(film))
    for shot,selected in zip(plan['shots'],final['shots']):
        assert shot['id'] == selected['id']
        source = draft_directory/selected['sourceFile']
        decision = decisions[shot['id']]
        if (sha(source) != source_hashes[selected['sourceFile']] or decision.get('allSourceFrameReview') is not True
                or decision.get('reviewedNativeFrames',0) < 120):
            raise ValueError('Every full five-second 2K input requires actual semantic review, including unused draft tails')
        probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
        if (len(probe['streams']) != 1 or int(probe['streams'][0]['nb_read_frames']) != 120
                or probe['streams'][0]['avg_frame_rate'] != '24/1'):
            raise ValueError('2K input must be the exact reviewed five-second video-only source')
        target = directory/'input-sources'/f"{shot['id']}.mp4"
        if target.exists() and sha(target) != sha(source):
            raise ValueError('Preserve existing 2K inputs; use a new directory')
        if not target.exists():
            shutil.copyfile(source,target)
        shot.update(inputSource=target.relative_to(directory).as_posix(),inputSourceSha256=sha(target))
        for key in ('motionReference','motionReferenceSha256','motionReferenceSeconds','references'):
            shot.pop(key,None)
        shot['prompt'] = (
            'Regenerate this same uninterrupted travel shot in clear 2560x1440 detail. '
            'Preserve the exact framing, camera motion, timing, ordinary weather, terrain and existing objects. '
            'Preserve the exact existing number and identity of people; add no person, human body part, hand, silhouette or reflected person. '
            'All existing people are adult women in feminine white/deep violet-black/gold costumes. '
            'Keep every real head and face outside all frames, including reflections, backgrounds, posters and screens. '
            'Any illustrated character already facing away must remain strictly back-facing. '
            'Existing faces drawn or embroidered on inert plushes and printed merchandise remain exactly the same; '
            'no blinking, mouth motion, morphing print, costume change or living toy. '
            'No readable text, subtitles, credits, voices, speech, singing, humming or laughter. '
            'No beautifying the location, invented flowers or magical lighting. '
            'Keep the existing gentle action: '+shot['generationAction'])
    for name in ('soundtrack.wav','soundtrack-receipt.json'):
        target = directory/name
        if target.exists() and sha(target) != sha(draft_directory/name):
            raise ValueError('Existing audio changed; preserve this run')
        if not target.exists():
            shutil.copyfile(draft_directory/name,target)
    shutil.copyfile(draft_plan,directory/'source-draft-plan.json')
    shutil.copyfile(delivery_file,directory/'source-draft-delivery.json')
    validate(plan)
    save(destination,plan)
    print('Prepared separate 2K plan and 49 reviewed inputs. New plan requires both independent reviews before submission.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('episode','draft-plan','draft-directory','delivery','directory','destination'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    prepare(args.episode,args.draft_plan,args.draft_directory,args.delivery,args.directory,args.destination,args.root)
