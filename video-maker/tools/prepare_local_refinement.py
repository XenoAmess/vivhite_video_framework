"""Prepare per-shot 2K inputs after the reviewed 768p film has been delivered.

Does not submit jobs or manufacture review decisions. GPL-3.0-only.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil
import sys

from local_video_pipeline import validate,read,save,source_frame_count
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
    plan.pop('reusedSources',None)
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
                or decision.get('reviewedNativeFrames',0) < source_frame_count(shot)):
            raise ValueError('Every complete 2K input requires actual semantic review, including unused draft tails')
        probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
        if (len(probe['streams']) != 1 or int(probe['streams'][0]['nb_read_frames']) != source_frame_count(shot)
                or probe['streams'][0]['avg_frame_rate'] != '24/1'):
            raise ValueError('2K input must be the exact complete reviewed video-only source')
        target = directory/'input-sources'/f"{shot['id']}.mp4"
        if target.exists() and sha(target) != sha(source):
            raise ValueError('Preserve existing 2K inputs; use a new directory')
        if not target.exists():
            shutil.copyfile(source,target)
        shot.update(inputSource=target.relative_to(directory).as_posix(),inputSourceSha256=sha(target))
        for key in ('motionReference','motionReferenceSha256','motionReferenceSeconds','references'):
            shot.pop(key,None)
        framing = ('The same one woman stays in exactly the original crop with her entire head outside the picture; '
                   'preserve her feminine white/deep-violet/gold clothes. '
                   if shot['mode']=='H' else
                   'The same one illustrated woman remains strictly back-facing throughout. '
                   if shot['mode']=='A' else 'The existing environment stays unoccupied by people. ')
        merchandise = ('The exact existing fabric doll remains an inert object with its same sewn face, expression and costume. '
                       if shot.get('designMaster','').endswith('M04-plush-v1.png') else
                       'The existing printed illustration remains identical and fixed to its original surface. '
                       if shot['mode'] not in ('A','W') and shot['id'] not in ('S18','S39','S48') else '')
        ending = ('The existing tiny corner butterfly makes just one calm, smooth wing cycle over about four seconds. '
                  if shot['id']=='S48' else '')
        shot['prompt'] = (
            'Regenerate this same uninterrupted quiet travel shot in clear 2560x1440 detail. '
            'The input video defines every scene element. Preserve its exact framing, camera tempo, natural light, '
            'ordinary weather, colors, terrain and object count. '+framing+merchandise+ending+
            'Introduce no extra person or body part. No real human face or facial fragment anywhere, including reflections and background. '
            'No readable lettering, subtitles, credits, speech, singing or other voices. '
            'Keep the original gentle action: '+shot['generationAction'])
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
    print(f"Prepared separate 2K plan and {len(plan['shots'])} reviewed inputs. New plan requires both independent reviews before submission.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('episode','draft-plan','draft-directory','delivery','directory','destination'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    prepare(args.episode,args.draft_plan,args.draft_directory,args.delivery,args.directory,args.destination,args.root)
