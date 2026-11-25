"""Deploy one reviewed image-first batch to an independent Windows task. GPL-3.0-only."""
from datetime import datetime, timezone
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess


def deploy(name, api):
    if not re.fullmatch(r'[a-z0-9-]{1,24}', name):
        raise ValueError('Use a stable batch name')
    episode = Path(__file__).resolve().parent.parent
    root = episode.parents[4]
    plan = episode/f'production-plan-v3-{name}-768p.json'
    data = json.loads(plan.read_text(encoding='utf-8'))
    python = root/'video-maker/.venv/Scripts/python.exe'
    gate = [str(python),'-X','utf8',str(root/'scripts/character_review.py'),'check',
            '--episode',str(episode/'episode.json'),'--document',str(plan)]
    for shot in data['shots']:
        for ref in shot['references']:
            gate += ['--asset',str(episode/ref)]
    subprocess.run(gate, check=True)
    directory = root.parent/f'vivhite-analysis-output/deepseek/autumn-journey/production-v3-{name}-768p-001'
    if directory.exists():
        raise ValueError('Inspect existing immutable run before any reuse')
    (directory/'metadata').mkdir(parents=True)
    (directory/'runtime/worker-001').mkdir(parents=True)
    (directory/'logs').mkdir()
    sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
    workers = []
    for source in (root/'video-maker/tools').glob('*.py'):
        target = directory/'runtime/worker-001'/source.name
        shutil.copyfile(source, target)
        workers.append({'path':str(target),'sha256':sha(target)})
    evidence = f'assets/generated/production-v3-firstframes-001/review/{name}-768p'
    config = {'schemaVersion':'vivhite-durable-video-config-1','root':str(root),
        'episode':str(episode/'episode.json'),'plan':str(plan),'planSha256':sha(plan),
        'directory':str(directory),'pythonw':str(python.with_name('pythonw.exe')),
        'controller':str(directory/'runtime/worker-001/durable_video_controller.py'),
        'schedulerTask':f'DeepSeek-Autumn-Journey-v3-768P-{name}','frozenWorkers':workers,
        'generationOnly':True,'evidenceRelativeToEpisode':evidence,
        'sourceCatalogRelativeToEpisode':f'production/source-generation-v3-{name}-768p.json',
        'toolDirectories':[str(Path(shutil.which('ffmpeg')).parent)],
        'generationCommand':[str(python),'-X','utf8',str(directory/'runtime/worker-001/local_video_pipeline.py'),
            '--root',str(root),'--episode',str(episode/'episode.json'),'--plan',str(plan),
            '--directory',str(directory),'--api',api,
            '--evidence',str(episode/evidence),'--face-model',
            str(root.parent/'vivhite-analysis-output/models/opencv-yunet-2023mar/face_detection_yunet_2023mar.onnx'),
            '--window','32','--poll-seconds','60']}
    config_file = directory/'metadata/durable-controller-config.json'
    config_file.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8',newline='\n')
    (directory/'run.json').write_text(json.dumps({'status':'generating','planSha256':sha(plan),
        'startedAt':datetime.now(timezone.utc).isoformat()},indent=2)+'\n',encoding='utf-8')
    result = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
        str(root/'scripts/start-durable-video-task.ps1'),'-Configuration',str(config_file)],
        check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    record = {'schemaVersion':'deepseek-independent-768p-deployment-1','at':datetime.now(timezone.utc).isoformat(),
        'plan':plan.name,'planSha256':sha(plan),'runtimeRelativeToRepositoryParent':directory.relative_to(root.parent).as_posix(),
        'schedulerTask':config['schedulerTask'],'configurationSha256':sha(config_file),
        'controllerSha256':sha(config['controller']),'pipelineSha256':sha(directory/'runtime/worker-001/local_video_pipeline.py'),
        'frozenWorkers':len(workers),'generationOnly':True,'window':32,'pollSeconds':60,
        'launchResult':'scheduled-task-started','actualFramesAndQualityReviewStillRequired':True}
    (episode/f'production/deployment-v3-{name}-768p.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(result.stdout.decode('utf-8','replace'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True)
    parser.add_argument('--api', default=os.environ.get('VIVHITE_LOCAL_VIDEO_API') or 'http://192.168.1.11:8080/v1',
                        help='Video API base to freeze in the scheduled task (overrides VIVHITE_LOCAL_VIDEO_API)')
    args = parser.parse_args()
    deploy(args.name, args.api)
