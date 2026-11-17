"""Prepare per-shot native 4K inputs after the reviewed 768p film is delivered.

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


def refinement_prompt(shot):
    """Describe preservation of the selected video, without replaying draft instructions."""
    framing = ('The same one woman stays in exactly the original body crop with her entire head outside the picture. '
               'Preserve her feminine white/deep-violet/gold clothes and the anatomical identity, '
               'orientation and continuous joints of each original arm and hand. '
               if shot['mode'] == 'H' else
               'The same one illustrated woman remains strictly back-facing throughout. '
               if shot['mode'] == 'A' else 'The existing environment stays unoccupied by people. ')
    merchandise = ('The exact existing fabric doll remains an inert object with its same sewn face, expression and costume. '
                   if shot.get('designMaster','').endswith('M04-plush-v1.png') else
                   'The existing printed illustration remains identical and fixed to its original surface. '
                   if shot['mode'] not in ('A','W') and shot['id'] not in ('S18','S39','S48') else '')
    if merchandise:
        merchandise += ('Every existing printed or sewn character face, including any small badge beside the doll, '
                        'keeps its original OPEN violet-pink eyes, iris and eyelid contours, thin round gold glasses '
                        'and original face proportions throughout. No blink, squint, eye shift, facial redraw, '
                        'expression change or turning illustration. Preserve transparent acrylic areas as real background. ')
    details = {
        'S01': 'Keep the same anatomical LEFT backhand grip: knuckles and the back of the hand face the camera, '
               'palm faces the curtain and window, thumb opposes the curved index on the lower near side. '
               'Preserve the small existing grip and fabric motion and the input camera movement. '
               'Do not turn the palm towards the camera, exchange hands or twist the wrist. ',
        'S05': 'Keep the existing alternating pedalling and continuous road and tree motion; '
               'no background reset, spatial jump or scene transition. ',
        'S07': 'Keep the input continuous walking and alternating weight-bearing steps from the first frame. ',
        'S15': 'Keep the existing slow lifting and holding of the cup with the same two hands; '
               'no repeated stroking, extra hand or movement towards a visible mouth. ',
        'S20': 'Keep the entire continuous lake shot, existing camera movement and stationary supported doll; '
               'do not restart, freeze, loop or replace the view at a window boundary. ',
        'S28': 'Keep the existing hands spreading the wrapper beside the bread. '
               'The space immediately above the bread stays clear, without invented white shapes or steam. ',
        'S44': 'Preserve the exact input action and timing: begin with the opaque tent door fully CLOSED, '
               'then the same attached right hand unzips once and draws the released cloth aside, '
               'revealing the outside before the four-second cut and keeping the door open. '
               'No reversed zipper travel, second closure or transparent cloth. ',
        'S47': 'Preserve the same two uncrossed attached arms and anatomically coherent hands, '
               'each staying on its original side of the doll. Keep the small whole-doll straightening, '
               'settling and release in the input, with stable sewn OPEN eyes and glasses. '
               'No extra hand, reversed thumb, wrist folding, stretched limb or hand passing through the doll. ',
        'S48': 'Preserve the input butterfly wing motion at its EXACT ORIGINAL SPEED and cadence. '
               'Do not slow down, accelerate, retime or add wing cycles. Keep the same single blue motif '
               'at its original bottom-right position and size. Preserve the unobstructed coast, plain sky '
               'and original clear frame margins. No new foreground tree, branch, leaf or vegetation. '
    }
    return ('Regenerate this same uninterrupted quiet travel video in clear native 3840x2160 detail. '
            'The INPUT VIDEO is the sole definition of scene contents, action, motion speed and camera trajectory. '
            'Keep every original moment in its original temporal order and preserve the complete input duration. '
            'Preserve exact framing, natural light, ordinary weather, colors, terrain and object count. '
            + framing + merchandise + details.get(shot['id'],'') +
            'Introduce no extra person or body part. No real human face or facial fragment anywhere, '
            'including reflections and background. No new readable lettering, subtitles, credits, '
            'speech, singing or other voices. No cuts, synthetic beautification, scene replacement, '
            'invented props, frozen padding or looping. Preserve the input action without performing it again.')


def prepare(episode,draft_plan,draft_directory,delivery_file,directory,destination,root):
    draft_directory,directory = Path(draft_directory).resolve(),Path(directory).resolve()
    if draft_directory == directory or directory.is_relative_to(draft_directory) or draft_directory.is_relative_to(directory):
        raise ValueError('Keep 4K and draft runs separate')
    delivery = read(delivery_file)
    film = draft_directory/'film.mp4'
    if (delivery.get('schemaVersion') != 'vivhite-delivery-plan-1' or sha(film) != delivery['film']['sha256']
            or delivery.get('machineDecodedFinalFrames') != delivery['film']['frames']):
        raise ValueError('An actual completed 768p delivery is required before 4K')
    delivery_assets = [film]
    if delivery.get('finalReview'):
        review_file = Path(delivery_file).resolve().parent/delivery['finalReview']
        if sha(review_file) != delivery['finalReviewSha256']:
            raise ValueError('768p final review binding changed')
        delivery_assets.extend([draft_directory/'soundtrack.wav',draft_directory/'titles.ass',
                                review_file,Path(delivery_file).resolve().parent/delivery['finalAssemblyPlan']])
    gate = [sys.executable,str(Path(root).resolve()/'scripts/character_review.py'),'check',
            '--episode',str(Path(episode).resolve()),'--document',str(Path(delivery_file).resolve())]
    for asset in delivery_assets:
        gate.extend(['--asset',str(asset)])
    print(run(gate,timeout=120))
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
    plan.update(stage='refine',model='open-h3-2k',width=3840,height=2160,sourceSize='3840x2160',
                refinementSeed=1234,sampler='up3',draftPlanSha256=sha(draft_plan),
                draftDeliverySha256=sha(delivery_file),draftFilmSha256=sha(film))
    plan['scope'] = ('Separate native UHD 4K refinement plan bound to the delivered 768p film and '
                     'its complete reviewed sources. Preparation submits no job; exact new input review is required.')
    plan['sourceContinuation'] = 'Regenerate all selected input videos in native UHD; preserve every final shot duration, title and original soundtrack.'
    plan['sourceAlignmentNote'] = 'Preserve the exact reviewed source frame count at 24fps and the unchanged final 30fps timeline; no temporal padding or retiming.'
    plan.pop('promptRevision',None)
    plan['refinement'] = {'model':'open-h3-2k','size':'3840x2160','sampler':'up3',
                          'submissionWindow':1,'scope':'Native UHD regeneration; historical provider model ID retained. No 2K output.'}
    for shot,selected in zip(plan['shots'],final['shots']):
        assert shot['id'] == selected['id']
        source = draft_directory/selected['sourceFile']
        decision = decisions[shot['id']]
        if (sha(source) != source_hashes[selected['sourceFile']] or decision.get('allSourceFrameReview') is not True
                or decision.get('reviewedNativeFrames',0) < source_frame_count(shot)):
            raise ValueError('Every complete 4K input requires actual semantic review, including unused draft tails')
        probe = json.loads(run(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(source)]))
        if (len(probe['streams']) != 1 or int(probe['streams'][0]['nb_read_frames']) != source_frame_count(shot)
                or probe['streams'][0]['avg_frame_rate'] != '24/1'):
            raise ValueError('4K input must be the exact complete reviewed video-only source')
        target = directory/'input-sources'/f"{shot['id']}.mp4"
        if target.exists() and sha(target) != sha(source):
            raise ValueError('Preserve existing 4K inputs; use a new directory')
        if not target.exists():
            shutil.copyfile(source,target)
        shot.update(inputSource=target.relative_to(directory).as_posix(),inputSourceSha256=sha(target))
        for key in ('motionReference','motionReferenceSha256','motionReferenceSeconds','references',
                    'generationAction','firstFrameRequirement','motionParentSha256',
                    'motionParentStartSeconds','motionParentSourceFile'):
            shot.pop(key,None)
        shot['acceptanceCriteria'] = ('Actually review all native UHD source frames and native-resolution hand, '
            'eye/glasses and window-boundary details against the selected input video. Preserve the original '
            'population, anatomy, fixed artwork and actual motion timing; reject invented people, real faces, '
            'changed printed eyes, cuts, window seams, extra limbs or new props. Preserve the locked final duration. '
            'Source review does not approve the later encoded film or claim human continuous playback.')
        shot['prompt'] = refinement_prompt(shot)
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
    print(f"Prepared separate native 4K plan and {len(plan['shots'])} reviewed inputs. New plan requires both independent reviews before submission.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('episode','draft-plan','draft-directory','delivery','directory','destination'):
        parser.add_argument('--'+name,required=True,type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    prepare(args.episode,args.draft_plan,args.draft_directory,args.delivery,args.directory,args.destination,args.root)
