"""Prepare the 49-shot, five-second-maximum revision without submitting inference.

Preserves the previous director and all source media. GPL-3.0-only.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

EP = Path(__file__).resolve().parents[1]
ROOT = EP.parents[4]
sys.path.insert(0, str(ROOT / 'video-maker/tools'))
from reference_finisher import run, sha, write_json


def timing(seconds):
    return f'{seconds//60:02}:{seconds%60:02}'


def prepare(previous, output):
    previous, output = previous.resolve(), output.resolve()
    if previous == output or output.is_relative_to(previous) or previous.is_relative_to(output):
        raise ValueError('Use a separate run directory')
    baseline_file = EP/'final-assembly-plan-v5.json'
    baseline = json.loads(baseline_file.read_text(encoding='utf-8'))
    baseline_hashes = {item['path']:item['sha256'] for item in baseline['files']}
    output.mkdir(parents=True, exist_ok=True)
    (output/'motion-reference').mkdir(exist_ok=True)
    shots = []
    frame = 0
    for original in baseline['shots']:
        source = previous/original['sourceFile']
        if sha(source) != baseline_hashes[original['sourceFile']]:
            raise ValueError('Previously selected source changed')
        ids = ('S20A','S20B') if original['id'] == 'S20' else (original['id'],)
        for identity in ids:
            shot = copy.deepcopy(original)
            shot.update(id=identity, seconds=min(original['seconds'],5), sourceSeconds=5, startFrame=frame)
            shot.pop('postprocess',None)
            shot.pop('sourceFile',None)
            if identity == 'S20A':
                shot['action'] = '高山湖岸的玩偶与背包近中景，镜头轻缓后移一小段，让湖面逐渐显露；玩偶静止，云影缓缓变化。'
            elif identity == 'S20B':
                shot['action'] = '同一高山湖的开阔宽景，小玩偶和背包留在左下前景岩石；镜头近乎固定，云影与细水纹缓慢移动。'
                shot['references'] = ['assets/generated/production-v5-bf16-001/scenes/S20B-v1.png']
                shot['seed'] += 1000
            elif identity == 'S44':
                shot['action'] = '帐内近景只见一名女性的手收拢帐门并缓缓拉动一段拉链，门边白绮布袋轻摆；镜头止于前臂，头部始终在画外。'
            elif identity == 'S48':
                shot['action'] = '无人海岸宽景，小蓝蝶在角落平静而缓慢地开合翅膀，每次完整开合约4秒；海浪轻缓，画面保持无字，片名与献词仅由后期叠加。'
            offset = 5 if identity == 'S20B' else 0
            # Already reviewed source footage supplies motion only. This is a
            # separately hashed actual external asset, not a server-local path.
            motion = output/'motion-reference'/f'{identity}.mp4'
            used = min(5, original['seconds']-offset)
            if motion.exists():
                existing = json.loads(run(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(motion)]))
                if float(existing['format']['duration']) > used+.03:
                    archive = output/'motion-reference-history'/f'{identity}-{sha(motion)[:12]}.mp4'
                    archive.parent.mkdir(exist_ok=True)
                    shutil.copyfile(motion,archive)
                    run(['ffmpeg','-v','error','-y','-ss',str(offset),'-i',str(source),'-an',
                         '-frames:v',str(used*24),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(motion)])
            if not motion.exists():
                run(['ffmpeg','-v','error','-y','-ss',str(offset),'-i',str(source),'-an',
                     '-frames:v',str(used*24),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(motion)])
            shot['motionReference'] = motion.relative_to(output).as_posix()
            shot['motionReferenceSha256'] = sha(motion)
            shot['motionReferenceSeconds'] = used
            shot['motionParentSha256'] = sha(source)
            shot['motionParentStartSeconds'] = offset
            shot['motionParentSourceFile'] = original['sourceFile']
            people = ('Only the exact one adult woman already partly visible in Picture 1 may appear. '
                      'Preserve the same feminine white/deep violet-black/gold sleeves, skirt, opaque white legwear and purple shoes. '
                      'Keep the head completely outside the entire frame. Never reveal a face or another body part by reframing. '
                      'No additional person, hand, body, silhouette, reflection or background bystander.'
                      if shot['mode'] == 'H' else
                      'Only the exact single illustrated adult woman already present may appear, strictly back-facing throughout. '
                      'No turn of the head, no human face, no second character, body, hand, reflection or silhouette.'
                      if shot['mode'] == 'A' else
                      'No living human or human body part may appear anywhere. No hands, heads, human faces, distant people, silhouettes or reflected people.')
            shot['generationAction'] = shot['action']
            if identity == 'S06':
                shot['generationAction'] = '城市电车窗角已有白绮小贴纸固定不动，窗外彩色立面缓缓掠过；玻璃空白区域保持干净无字。'
            elif identity == 'S48':
                shot['generationAction'] = '无人海岸宽景，小蓝蝶保持原有角落位置，平静而缓慢地开合翅膀，每次完整开合约4秒；海浪轻缓，天空保持干净无字。'
            shot['prompt'] = (
                'One uninterrupted restrained realistic travel-film shot, generated at native 1344x768. '
                'Picture 1 fixes the exact first-frame composition, object identities, ordinary weather and natural light. '
                'Video 1 supplies only a reference for gentle motion and tempo; its lower pixel resolution must not limit output detail. '
                'Start with the framing in Picture 1; use only the explicitly described gentle motion. '
                'No internal edits, cuts, sudden camera motion, or reveal of any previously unseen person or human anatomy. '
                + people + ' No human face or facial fragment anywhere, including glass, water, mirrors, photographs, screens or background. '
                'Existing printed/embroidered Vivhite faces on inert merchandise are allowed and must remain exactly unchanged. '
                'Never blink, move eyes or mouth, warp the illustration, change clothing, or animate a plush as a living creature. '
                'No speech, voices, narration, singing, humming or laughter; no readable text, subtitles or credits. '
                'Keep ordinary believable terrain, vegetation and infrastructure; no invented flowers, sunset, magical lighting or scenic beautification. '
                'Gentle action: '+shot['generationAction']+' Nonverbal sound only: '+shot['soundDescription'])
            shots.append(shot)
            frame += shot['seconds']*30
    assert len(shots) == 49 and frame == 5880 and max(s['seconds'] for s in shots) == 5
    plan = {'schemaVersion':'vivhite-local-two-stage-video-1','episodeId':'01-autumn-journey','revision':5,
        'model':'fasth3-omni-bf16','stage':'draft','fps':30,'width':1344,'height':768,'sourceSize':'1344x768',
        'sourceFps':24,'sourceSeconds':5,'maxShotSeconds':5,'totalFrames':frame,
        'noSpeech':True,'noHumanFaces':True,'noAddedPeople':True,'allCharactersFemale':True,
        'costumeStyle':'女性化白／深紫黑／细金边、裙装、白色腿部服装和紫色鞋靴，贴近角色参考图。',
        'numInferenceSteps':8,'decoderLayers':36,'decoderVerification':'GET /v1/models on 2026-11-16',
        'titleOverlays':baseline['titleOverlays'],'closingCredit':'','shots':shots,
        'refinement':{'model':'open-h3-2k','size':'2560x1440','sampler':'up3','seed':1234,
            'startCondition':'768p film delivered and every actual five-second input video independently reviewed',
            'scope':'Local video regeneration through port 8002; not a closed-source MiniMax teacher model.'},
        'baselinePlanSha256':sha(baseline_file),
        'clientArchiveSha256':'b818bd94ea799ad4349e4ea43545882a6cf6eaaaeda4b1f7edee268450b716a9',
        'sourceAlignmentNote':'Requested five-second model outputs can include alignment tail frames. Preserve raw output; final shots remain 2-5 seconds.'}
    write_json(EP/'production-plan-v5-bf16-768p.json',plan)

    director = (EP/'director.md').read_text(encoding='utf-8')
    original_rows = {}
    for line in director.splitlines():
        match = re.match(r'^\| (S\d{2}) [^|]+\| ([A-Z]) \| (.*?) \| (.*?) \| (.*?) \|$',line)
        if match:
            original_rows[match[1]] = match.groups()[1:]
    assert len(original_rows) == 48
    rows = []
    for shot in shots:
        parent_id = 'S20' if shot['id'] in ('S20A','S20B') else shot['id']
        mode,action,sound,note = original_rows[parent_id]
        if shot['id'] in ('S20A','S20B','S44','S48'):
            action = shot['action']
        if shot['id'] == 'S20A':
            note = 'M04；第一镜关注玩偶与手边小物，保持自然材质和静止表情。'
        elif shot['id'] == 'S20B':
            note = 'M04；第二镜景别明确变宽，延续同一风声和乐句，合计停留10秒。'
        elif shot['id'] == 'S48':
            note = 'I01；后期只叠片名与献词两行，详见第6节；无制作署名。'
        start = shot['startFrame']//30
        rows.append(f"| {shot['id']} {timing(start)}–{timing(start+shot['seconds'])}／{shot['seconds']}秒 | {mode} | {action} | {sound} | {note} |")
    director = re.sub(r'^\| S\d{2} [^\n]+\n', '', director, flags=re.M)
    marker = '| --- | --- | --- | --- | --- |\n'
    assert director.count(marker) == 1
    director = director.replace(marker,marker+'\n'.join(rows)+'\n')
    replacements = {
        '导演案 v3':'导演案 v5（768P／2K 制作版）',
        '48 个连续镜头，单镜 2–10 秒，排练总长 3 分 22 秒（202 秒）':'49 个连续镜头，单镜 2–5 秒，总长 3 分 16 秒（196 秒）',
        '建议 1920×1080、30fps':'先将原生1344×768源片合成为30fps版本，再逐镜调用本地2K接口制作2560×1440／30fps版本；模型源片均为24fps',
        '2–10 秒':'2–5 秒','超过 10 秒':'超过 5 秒','5–10 秒':'5 秒','48 镜连续分镜':'49 镜连续分镜',
        '文字仅限片名及英文副题、周边上后排的“Vivhite”和最终实际制作署名':'文字仅限S06片名及英文副题、S48片名与献词，以及已有周边上的“Vivhite”；画面不显示工具、模型或音乐制作署名',
        'S01–S12，00:00–00:48':'S01–S12，00:00–00:47',
        'S13–S28，00:48–01:59':'S13–S28（含S20A／S20B），00:47–01:56',
        'S29–S40，01:59–02:49':'S29–S40，01:56–02:44',
        'S41–S48，02:49–03:22':'S41–S48，02:44–03:16','60–300 帧':'60–150 帧',
        '具体场景以 v3 制作计划和对应参考图为准':'具体场景以本版制作计划和对应参考图为准'}
    for before,after in replacements.items():
        director = director.replace(before,after)
    director = re.sub(r'\*\*文字。\*\*[^\n]+',
        '**文字。** S06沿用片名与英文副题。S48只显示以下两行，标题、献词与淡出包含在该镜5秒内；不显示英文副题或制作署名。图像与模型视频阶段保持无字，由后期统一排版。\n\n```text\n白绮|秋日旅程\n献给最可爱的你\n```',director)
    director += '\n## 8. 本轮制作与保留\n\nS20拆成S20A、S20B两个独立5秒镜头，以明确的景别变化连接，保留合计10秒的停留。其他原6秒镜头均调整到5秒，动作重新选择起止，不统一加速。S48蓝蝶完整开合约4秒，保留平静美感。\n\n768P先完成生成、逐镜审核、声音与片名合成并交付；其后每个镜头单独调用本地2K重生成接口，2K结果重新逐镜审核和合成。2K模型为open-h3-2k，本地开源重生成路线，不能称作完整H3教师模型。两接口共享GPU，按阶段执行。\n\n旧导演稿、旧成片、完整请求、上传回执、任务状态、原始源片、对齐尾帧、失败尝试、修订与成片全部保留。全部新增图像与检查图片保存本项目并入库，大型媒体保存在仓库外独立运行目录。任何模型输出都须另审，计划审核不能替代实际成片审核。\n'
    (EP/'director-v5.md').write_text(director,encoding='utf-8',newline='\n')
    schedule = {'schemaVersion':'vivhite-production-schedule-1','timezone':'Asia/Shanghai',
        'estimatedAt':'2026-11-16T19:10:00+08:00','status':'initial-estimate-before-production',
        'shotCount':49,'filmSeconds':196,'draftSecondsPerFiveSecondClip':759.21,
        'refinementSecondsPerFiveSecondClip':1500,'sharedGpu':True,'existingOtherRunningJobs':2,
        'draftDeliveryWindow':['2026-11-17T09:00:00+08:00','2026-11-17T13:00:00+08:00'],
        'refinementDeliveryWindow':['2026-11-18T12:00:00+08:00','2026-11-18T20:00:00+08:00'],
        'assumptions':['Historical timings supplied in client docs, not new benchmark results.',
                       'Includes preparation, inspection, assembly and a rework allowance.',
                       'Recalculate after the first three completed jobs; queue and rework can change delivery windows.']}
    write_json(EP/'production/schedule-768p-2k-v1.json',schedule)
    print('Prepared director-v5.md and 49-shot, 196-second BF16 plan. No inference submitted.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--previous',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args()
    prepare(args.previous,args.output)
