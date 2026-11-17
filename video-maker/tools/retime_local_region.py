"""Slow a reviewed local motion interval while the surrounding shot keeps real time.

Creates an independent video-only candidate, never approval. GPL-3.0-only.
"""
import argparse
import json
import math
from pathlib import Path
import subprocess

from reference_finisher import run, sha, write_json


def retime_region(source, destination, box, factor, start_seconds, output_seconds, feather, reason, motion_fps=24):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if (source == destination or not reason.strip() or not math.isfinite(factor) or not 1 < factor <= 32
            or not math.isfinite(start_seconds) or start_seconds < 0
            or not isinstance(output_seconds, int) or isinstance(output_seconds, bool) or output_seconds not in (5, 10, 14)
            or len(box) != 4 or any(not isinstance(value, int) or value < 0 or value % 2 for value in box)
            or not isinstance(feather, int) or feather <= 0 or motion_fps not in (12, 24)):
        raise ValueError('Specify a separate candidate and valid explicit region/timing parameters')
    x1, y1, x2, y2 = box
    width, height = x2 - x1, y2 - y1
    if width <= 0 or height <= 0 or 2 * feather >= min(width, height):
        raise ValueError('Region and feather geometry are invalid')
    probe = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(source)]))
    if len(probe['streams']) != 1 or probe['streams'][0].get('codec_type') != 'video':
        raise ValueError('Use the exact complete video-only source')
    original = probe['streams'][0]
    if (original['avg_frame_rate'] != '24/1' or x2 > original['width'] or y2 > original['height']
            or int(original['nb_read_frames']) < output_seconds * 24):
        raise ValueError('Source dimensions, frame rate or complete duration are insufficient')
    # Keep real future frames for bidirectional interpolation; never fill with a
    # loop or cloned ending when an interval approaches the original endpoint.
    if start_seconds + output_seconds / factor + 2 / 24 > int(original['nb_read_frames']) / 24:
        raise ValueError('Selected motion interval lacks real interpolation context')
    identity = {'parentSha256': sha(source), 'box': list(box), 'factor': factor, 'startSeconds': start_seconds,
                'frames': output_seconds * 24, 'fps': 24, 'motionSampleFps': motion_fps, 'featherPixels': feather,
                'recipe': 'local-setpts-mci-no-scd-feather-original-timeline-crf16-2', 'workerSha256': sha(__file__)}
    receipt_file = destination.with_suffix('.json')
    if destination.exists():
        record = json.loads(receipt_file.read_text(encoding='utf-8'))
        if record['identity'] != identity or record['sha256'] != sha(destination):
            raise ValueError('Preserve this candidate; use a new version path')
        return record
    destination.parent.mkdir(parents=True, exist_ok=True)
    alpha = f'255*min(1,min(min(X,W-1-X),min(Y,H-1-Y))/{feather})'
    timing = f'trim=start={start_seconds},setpts=PTS-STARTPTS,'
    if motion_fps != 24:
        timing += f'fps={motion_fps},'
    timing += f'setpts={factor}*PTS'
    filters = (
        f'[0:v]split=2[base][region];'
        f'[region]crop={width}:{height}:{x1}:{y1},{timing},'
        'minterpolate=fps=24:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1:scd=none,'
        f"format=yuva420p,geq=lum='lum(X,Y)':cb='cb(X,Y)':cr='cr(X,Y)':a='{alpha}'[slow];"
        f'[base][slow]overlay=x={x1}:y={y1}:shortest=1:eof_action=endall:format=yuv420[out]')
    command = ['ffmpeg', '-v', 'error', '-n', '-i', str(source), '-filter_complex', filters,
               '-map', '[out]', '-an', '-frames:v', str(output_seconds * 24), '-c:v', 'libx264',
               '-preset', 'fast', '-crf', '16', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(destination)]
    write_json(destination.with_suffix('.command.json'), {'argv': command, 'identity': identity})
    snapshot = destination.with_suffix('.worker.py')
    if snapshot.exists() and snapshot.read_bytes() != Path(__file__).read_bytes():
        raise ValueError('Preserve the existing processing worker snapshot')
    snapshot.write_bytes(Path(__file__).read_bytes())
    try:
        completed = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace', timeout=1800)
    except subprocess.TimeoutExpired as error:
        captured = error.stdout or ''
        if isinstance(captured, bytes):
            captured = captured.decode('utf-8', errors='replace')
        destination.with_suffix('.ffmpeg.log').write_text(captured, encoding='utf-8', newline='\n')
        raise TimeoutError('Local retiming timed out; partial output, command, worker and log retained') from error
    destination.with_suffix('.ffmpeg.log').write_text(completed.stdout, encoding='utf-8', newline='\n')
    if completed.returncode:
        raise RuntimeError(f'Local retiming failed; output and complete log retained: {completed.stdout[-2000:]}')
    actual = json.loads(run(['ffprobe', '-v', 'error', '-count_frames', '-show_streams', '-of', 'json', str(destination)]))
    video = actual['streams'][0]
    if (len(actual['streams']) != 1 or int(video['nb_read_frames']) != output_seconds * 24
            or video['avg_frame_rate'] != '24/1'
            or (video['width'], video['height']) != (original['width'], original['height'])):
        raise ValueError('Candidate dimensions or complete frame count changed; retain for inspection')
    run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(destination), '-f', 'null', '-'])
    if sha(source) != identity['parentSha256']:
        raise ValueError('Original source changed during processing')
    record = {'schemaVersion': 'vivhite-local-region-retime-candidate-1', 'identity': identity,
              'sha256': sha(destination), 'reason': reason, 'durationSeconds': output_seconds,
              'nativeSize': [video['width'], video['height']],
              'regionSourceIntervalSeconds': [start_seconds, start_seconds + output_seconds / factor],
              'outsideRegionTimeline': 'Original source time, unchanged',
              'loopOrClonedPaddingUsed': False, 'originalPreserved': True,
              'semanticReview': 'pending', 'entersFilm': False}
    write_json(receipt_file, record)
    print('Created separate local-motion candidate; all-frame, boundary and outside-motion review required.')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    parser.add_argument('--box', required=True, nargs=4, type=int)
    parser.add_argument('--factor', required=True, type=float)
    parser.add_argument('--start-seconds', required=True, type=float)
    parser.add_argument('--output-seconds', type=int, choices=(5, 10, 14), default=14)
    parser.add_argument('--feather', type=int, default=8)
    parser.add_argument('--motion-fps', type=int, choices=(12, 24), default=24,
                        help='Optional local cadence sampling before interpolation; the surrounding video stays at 24fps')
    parser.add_argument('--reason', required=True)
    args = parser.parse_args()
    retime_region(args.source, args.destination, tuple(args.box), args.factor, args.start_seconds,
                  args.output_seconds, args.feather, args.reason, args.motion_fps)
