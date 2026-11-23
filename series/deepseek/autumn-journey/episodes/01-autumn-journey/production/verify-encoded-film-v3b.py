"""Verify actual encoded delivery against v2; no aesthetic decisions. GPL-3.0-only."""
import hashlib
import json
from pathlib import Path
import subprocess

EPISODE=Path(__file__).resolve().parent.parent
ROOT=EPISODE.parents[4]
MEDIA=ROOT.parent/'vivhite-analysis-output/deepseek/autumn-journey'
CURRENT=MEDIA/'production-v3-768p-full-002'
PRIOR=MEDIA/'production-v2-768p-full-001'


def sha(file):
    with file.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(file):
    return json.loads(file.read_text(encoding='utf-8'))


def main():
    current=read(EPISODE/'production-plan-v3b-768p.json')
    prior=read(EPISODE/'production-plan-v2-768p.json')
    assert [(s['id'],s['startFrame'],s['seconds']) for s in current['shots']]==[(s['id'],s['startFrame'],s['seconds']) for s in prior['shots']]
    changed=[s['id'] for s,old in zip(current['shots'],prior['shots']) if s['sourceSha256']!=old['sourceSha256']]
    assert changed==['S37','S47'],changed
    assert (CURRENT/'titles.ass').read_bytes()==(PRIOR/'titles.ass').read_bytes()
    assert sha(CURRENT/'soundtrack.wav')==sha(PRIOR/'soundtrack.wav')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames',
        '-show_streams','-show_format','-of','json',str(CURRENT/'film.mp4')],timeout=240))
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    audio=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert (video['width'],video['height'],video['avg_frame_rate'],int(video['nb_read_frames']))==(1344,768,'30/1',6150)
    assert float(video['duration'])==205 and float(audio['duration'])==205
    def audio_hash(file):
        return subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-map','0:a:0',
            '-c:a','pcm_s16le','-f','hash','-hash','sha256','-'],timeout=180).decode('ascii').strip()
    actual_audio=audio_hash(CURRENT/'film.mp4')
    assert actual_audio==audio_hash(PRIOR/'film.mp4')
    record={'schemaVersion':'deepseek-encoded-verification-3','filmSha256':sha(CURRENT/'film.mp4'),
        'all48TimingsMatchV2':True,'changedSources':changed,'unchangedSources':46,
        'assByteIdenticalToV2':True,'wavByteIdenticalToV2':True,'decodedAudioBitIdenticalToV2':True,
        'decodedPcmHash':actual_audio,'width':1344,'height':768,'fps':30,'frames':6150,
        'videoSeconds':205,'audioSeconds':205,'probe':probe,
        'scope':'Actual output technical comparison. Complete encoded visual/audio proofs and actual aesthetic review are separate.'}
    (EPISODE/'production/encoded-verification-v3b-768p.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8',newline='\n')
    print('Actual205seconds/6150frames; exactly two source changes; ASS/WAV and decoded film music unchanged')


if __name__=='__main__':
    main()
