"""Retain an imagegen original and a separately normalized first frame. GPL-3.0-only."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from PIL import Image


def save(sid, source, version='v1'):
    if not re.fullmatch(r'S\d{2}', sid):
        raise ValueError('Invalid stable shot ID')
    if not re.fullmatch(r'v[1-9]\d*', version):
        raise ValueError('Invalid candidate version')
    episode = Path(__file__).resolve().parent.parent
    assets = episode/'assets/generated/production-v1-firstframes-001'
    sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    raw = assets/'originals'/f'{sid}-{version}.png'
    frame = assets/'scenes'/f'{sid}-{version}.png'
    raw.parent.mkdir(exist_ok=True)
    frame.parent.mkdir(exist_ok=True)
    if raw.exists():
        if sha(raw) != sha(source):
            raise ValueError('Keep previous candidate and use a new version')
    else:
        shutil.copyfile(source, raw)
    if not frame.exists():
        subprocess.run(['ffmpeg','-v','error','-n','-i',str(raw),'-vf',
            'scale=1344:768:force_original_aspect_ratio=increase,crop=1344:768,setsar=1',
            '-frames:v','1',str(frame)], check=True)
    with Image.open(frame) as image:
        if image.size != (1344,768):
            raise ValueError('Unexpected export dimensions')
        image.verify()
    with Image.open(raw) as image:
        original_size = list(image.size)
    receipt = {'schemaVersion':'deepseek-first-frame-1','id':sid,'version':version,'generator':'built-in-imagegen',
        'recordedAt':datetime.now(timezone.utc).isoformat(),'defaultSource':str(source),
        'original':raw.relative_to(episode).as_posix(),'originalSha256':sha(raw),
        'originalSize':original_size,'frame':frame.relative_to(episode).as_posix(),
        'frameSha256':sha(frame),'frameSize':[1344,768],
        'export':'FFmpeg aspect-preserving scale and centered crop only; no creative edit',
        'userVideoApproval':'pending'}
    target = assets/'results'/f'{sid}-{version}.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(sid, receipt['frameSha256'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--version', default='v1')
    args = parser.parse_args()
    save(args.id, args.source.resolve(), args.version)
