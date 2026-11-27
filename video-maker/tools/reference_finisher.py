"""Original nonverbal soundtrack and gated finishing of real generated clips.

No speech model, recorded voices or third-party music are used. GPL-3.0-only.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import wave

RATE = 48000
RECIPE = "autumn-instrumental-1"
LEGACY_CLOSING_CREDIT = "影像：imagegen × FastH3 Omni  ·  原创器乐与环境声：程序合成"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def run(argv, *, cwd=None, timeout=600):
    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, creationflags=creation_flags)
    if result.returncode:
        summary = f"{Path(argv[0]).name} exited with status {result.returncode}"
        diagnostics = result.stderr.decode("utf-8", "replace")[-6000:].strip()
        raise RuntimeError(f"{summary}\n{diagnostics}" if diagnostics else summary)
    return result.stdout.decode("utf-8", "replace")


def synthesize(plan, output, seed=20261116):
    import numpy as np

    if plan["fps"] != 30 or plan["totalFrames"] % 30:
        raise ValueError("Soundtrack requires a 30fps integer-second timeline")
    duration = plan["totalFrames"] / 30
    count = plan["totalFrames"] * (RATE // 30)
    music = np.zeros((count, 2), dtype=np.float32)
    ambience = np.zeros_like(music)
    rng = np.random.default_rng(seed)
    events = []
    beat = 60 / 96
    bar = beat * 4
    # Dmaj9, Aadd9, Bm7, Gmaj7. Voice leading stays within one register.
    chords = [(50, [62, 66, 69, 73, 76]), (45, [61, 64, 69, 71, 76]),
              (47, [62, 66, 69, 71, 74]), (43, [62, 66, 67, 71, 74])]
    melody = [
        [(0, 74, 1), (1.5, 78, .5), (2.5, 81, 1)],
        [(0, 78, 1.5), (2, 76, .75), (3, 74, .75)],
        [(.5, 73, .75), (1.5, 76, 1), (3, 81, .75)],
        [(0, 78, 1.5), (2, 76, 1.5)],
        [(0, 74, 1), (1.5, 78, .5), (2.5, 81, 1)],
        [(0, 83, 1.5), (2, 81, .75), (3, 78, .75)],
        [(0, 79, 1), (1.5, 78, .75), (2.5, 76, .75)],
        [(0, 74, 2), (3, 73, .75)],
        [(.5, 78, .75), (1.5, 81, .75), (2.5, 85, 1)],
        [(0, 83, 1), (1.5, 81, 1), (3, 78, .75)],
        [(0, 76, 1), (1.5, 73, .75), (2.5, 76, 1)],
        [(0, 81, 1.5), (2.5, 78, 1)],
        [(0, 78, 1), (1.5, 74, 1), (3, 71, .75)],
        [(0, 74, 1.5), (2, 78, 1.5)],
        [(0, 79, 1), (1.5, 78, .75), (2.5, 76, 1)],
        [(0, 74, 2.75)],
    ]

    def note(start, midi, length, gain, pan=0, kind="pluck"):
        begin = round(start * RATE)
        if begin >= count:
            return
        samples = min(round(length * RATE), count - begin)
        if samples <= 0:
            return
        t = np.arange(samples, dtype=np.float32) / RATE
        freq = 440 * 2 ** ((midi - 69) / 12)
        if kind == "pad":
            envelope = np.minimum(t / .28, 1) * np.minimum((length - t) / .5, 1)
            tone = (np.sin(2 * np.pi * freq * t) + .22 * np.sin(2 * np.pi * freq * 2 * t)) * envelope
        else:
            envelope = (1 - np.exp(-t * 140)) * np.exp(-t * (2.2 if kind == "bell" else 4.2))
            tone = (np.sin(2 * np.pi * freq * t) + .28 * np.sin(2 * np.pi * freq * 2 * t)
                    + .09 * np.sin(2 * np.pi * freq * 3 * t)) * envelope
        signal = (tone * gain).astype(np.float32)
        for channel, level in enumerate((math.sqrt((1 - pan) / 2), math.sqrt((1 + pan) / 2))):
            music[begin:begin + samples, channel] += signal * level
        # Small stereo echo, not a second note or a sampled recording.
        delay = round(.1875 * RATE)
        end = min(count, begin + delay + samples)
        if end > begin + delay:
            music[begin + delay:end, :] += signal[:end - begin - delay, None] * .10
        events.append({"timeSeconds":round(start, 5), "midi":midi, "lengthSeconds":length, "instrument":kind})

    bars = math.ceil(duration / bar)
    for index in range(bars):
        start = index * bar
        root, tones = chords[(index // 2) % 4]
        section = index // 16
        # Opening, open mountain space, bright coast, then an airy closing phrase.
        energy = .68 if section in (0, 2) else 1.0
        if start > duration - 12:
            energy *= .65
        for i, pitch in enumerate(tones[:4]):
            note(start, pitch, bar + .5, .018 * energy, (i - 1.5) * .22, "pad")
        if index >= 4:
            note(start, root - 12, 1.6, .115 * energy, 0, "pluck")
            if section != 2:
                note(start + 2 * beat, root - 12, 1.3, .07 * energy, 0, "pluck")
        pattern = [0, 2, 1, 3, 2, 1, 3, 4]
        for eighth, chord_index in enumerate(pattern):
            if section == 2 and eighth % 2:
                continue
            note(start + eighth * beat / 2, tones[chord_index], 1.25, .055 * energy,
                 -.36 if eighth % 2 else .30)
        if index >= 8 and (index % 16 < 15 or section == 4):
            for offset, pitch, span in melody[index % 16]:
                # Alternating phrase registration avoids repeating an unchanged loop.
                shift = -12 if section == 2 else 0
                note(start + offset * beat, pitch + shift, span * beat + .9,
                     .095 * energy, .08, "bell")
        if index >= 12 and section not in (2, 4):
            for offset in (.0, 2.0):
                begin = round((start + offset * beat) * RATE)
                size = min(round(.16 * RATE), count - begin)
                if size > 0:
                    t = np.arange(size) / RATE
                    tap = (rng.standard_normal(size) * np.exp(-t * 42) * .009).astype(np.float32)
                    music[begin:begin + size] += tap[:, None]

    ambient_events = []
    for shot in plan["shots"]:
        begin = shot["startFrame"] * (RATE // 30)
        size = shot["seconds"] * RATE
        t = np.arange(size, dtype=np.float32) / RATE
        noise = rng.standard_normal(size).astype(np.float32)
        # Moving-average filtered noise is explicitly synthetic; it cannot contain words.
        accumulated = np.cumsum(np.pad(noise, (479, 0)), dtype=np.float64)
        breeze = ((accumulated[480:] - accumulated[:-480]) / 480).astype(np.float32)
        breeze = np.pad(breeze, (0, size - len(breeze)))
        description = shot["soundDescription"]
        kind = "wind"
        level = .25
        signal = breeze * (0.65 + 0.35 * np.sin(2 * np.pi * .22 * t))
        if any(word in description for word in ("水", "浪", "溪", "桨")):
            kind = "water"
            signal += noise * .018 * (1 + .6 * np.sin(2 * np.pi * .31 * t))
            level = .35
        if "雨" in description or "檐滴" in description:
            kind = "rain"
            signal += noise * .035
            level = .38
        if any(word in description for word in ("车", "轮", "缆")):
            kind = "transport"
            signal += .025 * np.sin(2 * np.pi * 56 * t) + .009 * np.sin(2 * np.pi * 112 * t)
        edge = np.minimum(np.arange(size) / (RATE * .12), 1) * np.minimum(np.arange(size)[::-1] / (RATE * .18), 1)
        signal = (signal * level * edge).astype(np.float32)
        ambience[begin:begin + size] += signal[:, None]
        ambient_events.append({"shotId":shot["id"], "kind":kind, "description":description,
                               "source":"procedural noise/oscillators; no field recording"})
    signal = music + ambience
    signal[:RATE] *= np.linspace(0, 1, RATE, dtype=np.float32)[:, None]
    tail = min(count, 3 * RATE)
    signal[-tail:] *= np.linspace(1, 0, tail, dtype=np.float32)[:, None]
    peak = float(np.max(np.abs(signal)))
    signal *= .82 / max(peak, .001)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    raw = output / "soundtrack-raw.wav"
    with wave.open(str(raw), "wb") as target:
        target.setparams((2, 2, RATE, count, "NONE", "uncompressed"))
        target.writeframes((signal * 32767).astype("<i2").tobytes())
    normalized = output / "soundtrack.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af",
         "loudnorm=I=-18:TP=-1.8:LRA=8", "-ar", str(RATE), "-c:a", "pcm_s16le", str(normalized)])
    with wave.open(str(normalized), "rb") as source:
        if source.getnframes() != count:
            raise ValueError("Soundtrack sample count does not match the picture timeline")
    receipt = {"schemaVersion":"vivhite-original-soundtrack-1", "recipe":RECIPE,
               "workerSha256":sha(__file__), "sourcePlanSha256":None,
               "seed":seed, "bpm":96, "key":"D major", "sampleRate":RATE, "channels":2,
               "samplesPerChannel":count, "durationSeconds":duration, "sha256":sha(normalized),
               "speechSource":"none", "thirdPartyMusic":"none", "nativeModelAudioInFinalMix":False,
               "credit":"原创器乐与环境声：程序合成", "noteEvents":events, "ambientEvents":ambient_events}
    write_json(output / "soundtrack-receipt.json", receipt)
    return receipt


def ass_time(seconds):
    cs = round(seconds * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02}:{cs // 100 % 60:02}.{cs % 100:02}"


def output_dimensions(plan):
    dimensions = (plan.get("width",1920),plan.get("height",1080))
    if dimensions not in ((1920,1080),(1344,768),(3840,2160)):
        raise ValueError("Unsupported final output dimensions")
    return dimensions


def titles(plan):
    text = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Title,Microsoft YaHei,66,&H00FFFFFF,&H00FFFFFF,&H50251B30,&H80251B30,0,0,0,0,100,100,4,0,1,2,1,7,110,80,100,1
Style: Subtitle,Microsoft YaHei,30,&H00F4EBE6,&H00FFFFFF,&H50251B30,&H80251B30,0,0,0,0,100,100,2,0,1,1,1,7,114,80,190,1
Style: Credit,Microsoft YaHei,24,&H00FFFFFF,&H00FFFFFF,&H50251B30,&H80251B30,0,0,0,0,100,100,1,0,1,1,1,7,114,80,250,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if any(overlay.get('dedication') for overlay in plan['titleOverlays']):
        style = 'Style: Dedication,Microsoft YaHei,30,&H00F4EBE6,&H00FFFFFF,&H50251B30,&H80251B30,0,0,0,0,100,100,2,0,1,1,1,7,114,80,260,1\n'
        text = text.replace('\n[Events]\n','\n'+style+'\n[Events]\n')
    for overlay in plan["titleOverlays"]:
        shot = next(s for s in plan["shots"] if s["id"] == overlay["shotId"])
        start = shot["startFrame"] / plan["fps"] + .4
        end = (shot["startFrame"] / plan["fps"]) + shot["seconds"] - .35
        for style, value in (("Title", overlay["text"]), ("Subtitle", overlay["subtitle"])):
            if any(c in value for c in "{}\n\r\\"):
                raise ValueError("Title text cannot contain ASS control characters")
            text += f"Dialogue: 0,{ass_time(start)},{ass_time(end)},{style},,0,0,0,,{{\\fad(350,400)}}{value}\n"
        if overlay.get('dedication'):
            value = overlay['dedication']
            delay = overlay.get('dedicationDelaySeconds',3)
            fade_in = overlay.get('dedicationFadeInMs',1800)
            if (not isinstance(value,str) or any(c in value for c in '{}\n\r\\')
                    or not isinstance(delay,(int,float)) or isinstance(delay,bool) or not math.isfinite(delay)
                    or delay < .75 or not isinstance(fade_in,int) or isinstance(fade_in,bool)
                    or not 350 <= fade_in <= 5000 or delay+fade_in/1000+1.5 > shot['seconds']-.35):
                raise ValueError('Dedication must appear after the title and leave sufficient reading time inside its shot')
            dedication_start = shot['startFrame']/plan['fps']+delay
            text += f"Dialogue: 0,{ass_time(dedication_start)},{ass_time(end)},Dedication,,0,0,0,,{{\\fad({fade_in},400)}}{value}\n"
        credit = plan.get("closingCredit", LEGACY_CLOSING_CREDIT) if shot["id"] == "S48" else ""
        if any(c in credit for c in "{}\n\r\\"):
            raise ValueError("Credit text cannot contain ASS control characters")
        if credit:
            text += f"Dialogue: 0,{ass_time(start + .5)},{ass_time(end)},Credit,,0,0,0,,{{\\fad(350,400)}}{credit}\n"
    return text


def prepare(source_plan, directory, destination):
    directory = Path(directory).resolve()
    plan = json.loads(Path(source_plan).read_text(encoding="utf-8"))
    width,height = output_dimensions(plan)
    (directory / "titles.ass").write_text(titles(plan), encoding="utf-8-sig", newline="\n")
    selections_path = directory/"source-selections.json"
    selections = json.loads(selections_path.read_text(encoding="utf-8"))["selections"] if selections_path.exists() else {}
    paths, provenance = [], []
    concat = "ffconcat version 1.0\n"
    for shot in plan["shots"]:
        selected = selections.get(shot["id"])
        path = selected["path"] if selected else f"sources/{shot['id']}.mp4"
        shot["sourceFile"] = path
        paths.append(path)
        segment = directory/"segments"/f"{shot['id']}.mp4"
        if selected:
            for key in ("path","parent","receipt"):
                if not (directory/selected[key]).resolve().is_relative_to(directory):
                    raise ValueError("Corrected source provenance escaped the run")
            if sha(directory/path) != selected["sha256"] or sha(directory/selected["parent"]) != selected["parentSha256"]:
                raise ValueError("Corrected source or its parent changed")
            provenance.extend((selected["parent"],selected["receipt"]))
            corrected_segments = directory/"segments-corrected"
            corrected_segments.mkdir(exist_ok=True)
            segment = corrected_segments/f"{shot['id']}-{selected['sha256'][:10]}.mp4"
            if not segment.exists():
                run(["ffmpeg","-v","error","-y","-i",str(directory/path),"-an","-vf",
                     f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps=30",
                     "-frames:v",str(shot["seconds"]*30),"-c:v","libx264","-preset","fast","-crf","18",
                     "-pix_fmt","yuv420p",str(segment)])
        concat += "file '"+segment.as_posix().replace("'","'\\''")+"'\n"
    picture = "picture-assembly.mp4"
    if selections:
        picture = "picture-assembly-selected.mp4"
        (directory/"selected-segments.ffconcat").write_text(concat,encoding="utf-8",newline="\n")
        run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",
             str(directory/"selected-segments.ffconcat"),"-c","copy","-movflags","+faststart",str(directory/picture)])
        provenance.append("source-selections.json")
    paths += [picture, "soundtrack.wav", "titles.ass", "clip-decisions.json", *provenance]
    if (directory/"source-imports.json").exists():
        paths.append("source-imports.json")
    paths = list(dict.fromkeys(paths))
    files = [{"path":path, "sha256":sha(directory/path)} for path in paths]
    final = {"schemaVersion":"vivhite-reference-finish-1", "sourcePlanSha256":sha(source_plan),
             "fps":plan["fps"], "width":width, "height":height, "totalFrames":plan["totalFrames"],
             "noSpeech":True, "noHumanFaces":True, "allCharactersFemale":True, "noAddedPeople":True,
             "sourceSize":plan["sourceSize"], "files":files, "shots":plan["shots"], "pictureFile":picture,
             "titleOverlays":plan["titleOverlays"], "nativeAudioInFinalMix":False,
             "soundtrackCredit":"原创器乐与环境声：程序合成", "soundtrackRecipe":RECIPE,
             "closingCredit":plan.get("closingCredit", LEGACY_CLOSING_CREDIT),
             "closingFadeSeconds":.8, "spokenSubtitles":[],
             "referenceAppearanceRequired":plan.get("referenceAppearanceRequired",False),
             "shotDurationExceptions":plan.get("shotDurationExceptions",{}),
             "scope":"Final assembly plan; input/source review does not assert final encoded or human aesthetic acceptance."}
    write_json(destination, final)
    verify_clip_decisions(final, directory)
    return final


def bound_files(plan, directory):
    directory = Path(directory).resolve()
    result = []
    for item in plan["files"]:
        relative = Path(item["path"])
        path = (directory/relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(directory) or sha(path) != item["sha256"]:
            raise ValueError("Final input escaped the run directory or changed after review")
        result.append(path)
    return result


def verify_clip_decisions(plan, directory):
    decisions = json.loads((Path(directory)/"clip-decisions.json").read_text(encoding="utf-8"))
    if (decisions.get("schemaVersion") != "vivhite-clip-decisions-1"
            or decisions.get("sourcePlanSha256") != plan["sourcePlanSha256"]):
        raise ValueError("Shot acceptance decisions do not match the current source plan")
    source_hashes = {item["path"]:item["sha256"] for item in plan["files"]}
    rows = decisions.get("shots", [])
    if len(rows) != len(plan["shots"]) or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("Every final shot requires its own actual acceptance decision")
    for shot in plan["shots"]:
        row = next((r for r in rows if r["id"] == shot["id"]), None)
        if plan.get('referenceAppearanceRequired') and (row is None or row.get('referenceAppearance') != 'passed'):
            raise ValueError(f"Original artwork appearance review is unresolved for {shot['id']}")
        if (row is None or row.get("sourceSha256") != source_hashes[shot.get("sourceFile",f"sources/{shot['id']}.mp4")]
                or row.get('decision') == 'rejected' or row.get('referenceAppearance') == 'failed'
                or row.get("method") != "assistant-frame-review" or row.get("allUsedFrameReview") is not True
                or row.get("reviewedNativeFrames",0) < shot["seconds"]*24
                or any(row.get(k) != "passed" for k in ("noHumanFaces","noAddedPeople","allCharactersFemale","costumeStyle",
                                                        "motionAndContinuity","merchandiseBehavior"))):
            raise ValueError(f"Unresolved, failed or stale video acceptance for {shot['id']}")


def finish(episode, plan_file, directory, review_python):
    directory = Path(directory).resolve()
    plan_file = Path(plan_file).resolve()
    plan = json.loads(plan_file.read_text(encoding="utf-8"))
    width,height = output_dimensions(plan)
    if (plan["schemaVersion"] != "vivhite-reference-finish-1" or plan["fps"] != 30
            or not all(plan.get(k) is True for k in ("noSpeech", "noHumanFaces", "allCharactersFemale", "noAddedPeople"))
            or plan.get("nativeAudioInFinalMix") is not False):
        raise ValueError("Invalid nonverbal final assembly plan")
    assets = bound_files(plan, directory)
    verify_clip_decisions(plan, directory)
    root = Path(__file__).resolve().parents[2]
    gate = [review_python, str(root/"scripts/character_review.py"), "check", "--episode", str(Path(episode).resolve()),
            "--document", str(plan_file)]
    for path in assets:
        gate.extend(("--asset", str(path)))
    print(run(gate, cwd=root, timeout=120), flush=True)
    duration = plan["totalFrames"] / plan["fps"]
    fade = plan["closingFadeSeconds"]
    partial = directory / "film.partial.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-i", plan["pictureFile"], "-i", "soundtrack.wav",
         "-map", "0:v:0", "-map", "1:a:0", "-vf", f"ass=titles.ass,fade=t=out:st={duration-fade}:d={fade}",
         "-frames:v", str(plan["totalFrames"]), "-t", str(duration), "-c:v", "libx264", "-crf", "18",
         "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-ar", str(RATE),
         "-movflags", "+faststart", str(partial)], cwd=directory, timeout=1800)
    run(["ffmpeg", "-v", "error", "-xerror", "-i", str(partial), "-f", "null", "-"], timeout=600)
    probe = json.loads(run(["ffprobe", "-v", "error", "-count_frames", "-show_streams", "-show_format", "-of", "json", str(partial)]))
    video = next(s for s in probe["streams"] if s["codec_type"] == "video")
    audio = next(s for s in probe["streams"] if s["codec_type"] == "audio")
    if (int(video["nb_read_frames"]) != plan["totalFrames"] or video["width"] != width
            or video["height"] != height or video["avg_frame_rate"] != "30/1"
            or abs(float(audio["duration"]) - duration) > .03):
        raise ValueError("Final encoded timing or stream format mismatch")
    film = directory / "film.mp4"
    partial.replace(film)
    write_json(directory/"final-probe.json", probe)
    receipt = {"schemaVersion":"vivhite-reference-finish-receipt-1", "status":"encoded-technical-checks-passed",
               "planSha256":sha(plan_file), "workerSha256":sha(__file__), "filmSha256":sha(film),
               "frames":int(video["nb_read_frames"]), "durationSeconds":duration,
               "fullAudioVideoDecode":"passed", "nativeModelAudioInFinalMix":False,
               "semanticReview":"separate evidence and review required", "humanFullPlayback":False}
    write_json(directory/"final-assembly-receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=True), flush=True)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    music = sub.add_parser("soundtrack")
    music.add_argument("--plan", type=Path, required=True)
    music.add_argument("--output", type=Path, required=True)
    prepare_command = sub.add_parser("prepare")
    prepare_command.add_argument("--source-plan", type=Path, required=True)
    prepare_command.add_argument("--directory", type=Path, required=True)
    prepare_command.add_argument("--destination", type=Path, required=True)
    final = sub.add_parser("finish")
    final.add_argument("--episode", type=Path, required=True)
    final.add_argument("--plan", type=Path, required=True)
    final.add_argument("--directory", type=Path, required=True)
    final.add_argument("--review-python", default=sys.executable)
    args = parser.parse_args()
    if args.command == "soundtrack":
        receipt = synthesize(json.loads(args.plan.read_text(encoding="utf-8")), args.output)
        receipt["sourcePlanSha256"] = sha(args.plan)
        write_json(args.output/"soundtrack-receipt.json", receipt)
    elif args.command == "prepare":
        prepare(args.source_plan, args.directory, args.destination)
    else:
        finish(args.episode, args.plan, args.directory, args.review_python)


if __name__ == "__main__":
    main()
