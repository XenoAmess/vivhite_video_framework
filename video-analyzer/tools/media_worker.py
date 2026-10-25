"""Local inference worker. Business orchestration and report validation live in Java."""

import argparse
import dataclasses
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time


def vision(args):
    import av
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    left, top, right, bottom = args.subtitle_box
    if args.sample_seconds <= 0 or not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("Use a positive sample interval and normalized, nonempty subtitle box")

    output = Path(args.output)
    (output / "frames").mkdir(parents=True, exist_ok=True)
    (output / "sheets").mkdir(exist_ok=True)
    (output / "subtitle-crops").mkdir(exist_ok=True)
    identity = {"sourceSha256": fingerprint(args.input), "sampleSeconds": args.sample_seconds,
                "subtitleBox": args.subtitle_box, "ocr": args.ocr,
                "workerVersion": "1.0", "pyavVersion": av.__version__}
    result_path = output / "vision.json"
    if result_path.exists():
        cached = json.loads(result_path.read_text(encoding="utf-8"))
        if cached.get("identity") == identity and cached.get("status") == "complete":
            print("Reusing completed visual processing", flush=True)
            return
    engine = None
    if args.ocr:
        from rapidocr import RapidOCR
        engine = RapidOCR(params={"EngineConfig.onnxruntime.intra_op_num_threads": 3})
    container = av.open(str(args.input))
    stream = next(s for s in container.streams.video if not (int(s.disposition) & 1024))
    stream.codec_context.thread_count = 4
    frames, subtitles, cuts, sheets = [], [], [], []
    previous_gray = None
    previous_roi = None
    ocr_time = -10000
    next_sample = 0
    count = 0
    origin = None
    previous_pts = None
    decode_gaps = []
    non_monotonic = []
    last_end = 0
    started = time.monotonic()
    sheet_frames = []
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    except OSError:
        font = ImageFont.load_default(size=22)

    def save_sheet():
        if not sheet_frames:
            return
        canvas = Image.new("RGB", (1944, 1584), "#222222")
        draw = ImageDraw.Draw(canvas)
        for index, item in enumerate(sheet_frames):
            x = 8 + (index % 3) * 648
            y = 8 + (index // 3) * 394
            with Image.open(output / item["path"]) as source:
                canvas.paste(source.resize((640, 360)), (x, y + 28))
            seconds = item["timeMs"] / 1000
            draw.text((x, y), f"{int(seconds // 60):02d}:{seconds % 60:05.2f} | {item['id']}",
                      font=font, fill="white")
        name = f"sheets/sheet-{len(sheets) + 1:03d}.jpg"
        canvas.save(output / name, quality=90)
        sheets.append({"path": name, "frameIds": [f["id"] for f in sheet_frames]})
        sheet_frames.clear()

    with (output / "frame-metrics.jsonl").open("w", encoding="utf-8") as metrics:
        for frame in container.decode(stream):
            if frame.pts is None:
                raise ValueError("Decoded frame has no PTS; cannot certify chronological coverage")
            raw_pts_ms = float(frame.pts * stream.time_base) * 1000
            if origin is None:
                origin = raw_pts_ms
            now = round(raw_pts_ms - origin)
            if previous_pts is not None:
                if now <= previous_pts:
                    non_monotonic.append({"previousMs": previous_pts, "currentMs": now})
                if now - previous_pts > 100:
                    decode_gaps.append({"startMs": previous_pts, "endMs": now})
            previous_pts = now
            image = frame.to_ndarray(format="bgr24")
            small = cv2.resize(image, (320, 180))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            difference = 0.0 if previous_gray is None else float(
                np.mean(cv2.absdiff(gray, previous_gray)))
            previous_gray = gray
            count += 1
            frame_duration = (float(frame.duration * stream.time_base) * 1000 if frame.duration
                              else 1000 / float(stream.average_rate))
            last_end = round(now + frame_duration)
            metrics.write(json.dumps({"frame": count, "timeMs": now,
                                       "meanAbsoluteDifference": round(difference, 3)}) + "\n")
            is_cut = difference > 18 and (not cuts or now - cuts[-1] > 200)
            if is_cut:
                cuts.append(now)
            if now >= next_sample or is_cut or count == 1:
                image_name = f"frames/f{now:09d}.jpg"
                cv2.imwrite(str(output / image_name), cv2.resize(image, (1280, 720)),
                            [cv2.IMWRITE_JPEG_QUALITY, 88])
                item = {"id": f"f{now:09d}", "timeMs": now, "sourcePts": frame.pts,
                        "path": image_name, "reason": "cut_candidate" if is_cut else "coverage"}
                frames.append(item)
                sheet_frames.append(item)
                if len(sheet_frames) == 12:
                    save_sheet()
                if now >= next_sample:
                    next_sample = now + round(args.sample_seconds * 1000)
            height, width = image.shape[:2]
            left, top, right, bottom = args.subtitle_box
            roi = image[round(top * height):round(bottom * height),
                        round(left * width):round(right * width)]
            roi_gray = cv2.cvtColor(cv2.resize(roi, (480, 64)), cv2.COLOR_BGR2GRAY)
            roi_difference = 999 if previous_roi is None else float(
                np.mean(cv2.absdiff(roi_gray, previous_roi)))
            # Decode and inspect every frame. OCR is change-triggered with a bounded refresh;
            # the cooldown and selected images are reported, not called exhaustive recognition.
            should_ocr = now - ocr_time >= 200 and (roi_difference > 2.0 or now - ocr_time >= 1500)
            if engine is not None and should_ocr:
                result = engine(roi)
                texts = list(result.txts or ())
                scores = list(result.scores or ())
                text = " ".join(texts)
                if text and subtitles and subtitles[-1]["text"] == text:
                    subtitles[-1]["lastObservedMs"] = now
                elif text:
                    crop_name = f"subtitle-crops/t{now:09d}.jpg"
                    cv2.imwrite(str(output / crop_name), roi)
                    subtitles.append({"id": f"t{len(subtitles) + 1:05d}", "timeMs": now,
                                      "lastObservedMs": now, "text": text,
                                      "scores": scores, "path": crop_name})
                previous_roi = roi_gray
                ocr_time = now
            if count % 1800 == 0:
                print(f"Decoded {count} frames / {now / 1000:.1f}s; "
                      f"{len(subtitles)} OCR observations", flush=True)
    container.close()
    save_sheet()
    write_json(result_path, {"schemaVersion": "1.0", "status": "complete", "identity": identity,
                            "sourceOriginPtsMs": origin, "decodedFrames": count,
                            "decodedEndMs": last_end, "decodeGaps": decode_gaps,
                            "nonMonotonicPts": non_monotonic, "frames": frames, "sheets": sheets,
                            "cutCandidatesMs": cuts, "subtitleObservations": subtitles,
                            "ocrPolicy": {"enabled": args.ocr, "triggerMeanDifference": 2.0, "cooldownMs": 200,
                                          "maximumRefreshMs": 1500, "allFramesInspected": True,
                                          "recognitionCompleteness": "not_certified" if args.ocr else "not_run"},
                            "semanticReviewStatus": "not_run",
                            "elapsedSeconds": round(time.monotonic() - started, 3)})
    print(f"Visual processing complete: {count} frames, {len(frames)} evidence frames", flush=True)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def fingerprint(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def transcribe(args):
    from faster_whisper import WhisperModel

    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    source_hash = fingerprint(args.input)
    identity = {"sourceSha256": source_hash, "model": args.model, "device": args.device,
                "computeType": args.compute_type, "language": "zh", "beamSize": 5,
                "vadFilter": False, "wordTimestamps": True,
                "audioDecoder": "ffmpeg_pcm_s16le_16000_mono",
                "fasterWhisperVersion": importlib.metadata.version("faster-whisper")}
    completed = output / "transcript.json"
    if completed.exists():
        cached = json.loads(completed.read_text(encoding="utf-8"))
        if cached.get("identity") == identity and cached.get("status") == "complete":
            print("Reusing completed transcription", flush=True)
            return
    started = time.monotonic()
    print(f"Loading {args.model} on {args.device} ({args.compute_type})", flush=True)
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type,
                         cpu_threads=args.threads, num_workers=1)
    audio = decode_audio(args.input)
    segments, info = model.transcribe(audio, language="zh", beam_size=5,
                                      word_timestamps=True, vad_filter=False,
                                      condition_on_previous_text=False)
    results = []
    progress = -30
    with (output / "transcript-progress.jsonl").open("w", encoding="utf-8") as journal:
        for segment in segments:
            value = dataclasses.asdict(segment)
            value["id"] = f"s{len(results) + 1:05d}"
            value["startMs"] = round(segment.start * 1000)
            value["endMs"] = round(segment.end * 1000)
            results.append(value)
            journal.write(json.dumps(value, ensure_ascii=False) + "\n")
            journal.flush()
            if segment.end - progress >= 30:
                print(f"Transcribed {segment.end:.1f}/{info.duration:.1f} seconds", flush=True)
                progress = segment.end
    result = {"schemaVersion": "1.0", "status": "complete", "identity": identity,
              "durationMs": round(info.duration * 1000), "language": info.language,
              "languageProbability": info.language_probability,
              "elapsedSeconds": round(time.monotonic() - started, 3), "segments": results,
              "qualityStatus": "asr_unverified", "secondaryAsrStatus": "not_run"}
    write_json(completed, result)
    lines = ["# 全量机器转写（待核对）", "",
             f"模型：{args.model}；音频时长：{info.duration:.3f} 秒。", ""]
    for segment in results:
        start = segment["startMs"] / 1000
        lines.append(f"[{segment['id']}] {int(start // 60):02d}:{start % 60:06.3f} "
                     f"{segment['text'].strip()}")
    (output / "transcript.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Completed: {len(results)} segments in {result['elapsedSeconds']:.1f}s", flush=True)


def decode_audio(path):
    import numpy as np
    decoded = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(path),
                              "-map", "0:a:0", "-ac", "1", "-ar", "16000",
                              "-f", "s16le", "pipe:1"], check=True,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=300)
    audio = np.frombuffer(decoded.stdout, dtype="<i2").astype(np.float32) / 32768.0
    if not len(audio):
        raise ValueError("Source audio decoded to an empty waveform")
    return audio


def audio_metrics(args):
    import numpy as np
    audio = decode_audio(args.input)
    bins = []
    for offset in range(0, len(audio), 16000):
        part = audio[offset:offset + 16000]
        rms = float(np.sqrt(np.mean(part * part)))
        bins.append({"startMs": round(offset / 16), "endMs": round((offset + len(part)) / 16),
                     "rmsDbfs": round(20 * float(np.log10(max(rms, 1e-12))), 3),
                     "samplePeak": round(float(np.max(np.abs(part))), 6)})
    write_json(Path(args.output) / "audio-metrics.json", {
        "schemaVersion": "1.0", "status": "complete", "sourceSha256": fingerprint(args.input),
        "sampleRate": 16000, "channels": 1, "durationMs": round(len(audio) / 16),
        "measurement": "decoded mono PCM RMS dBFS; not LUFS, true peak or emotion detection",
        "bins": bins})
    print(f"Measured full audio: {len(audio) / 16000:.3f}s", flush=True)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    transcription = subparsers.add_parser("transcribe")
    transcription.add_argument("--input", required=True, type=Path)
    transcription.add_argument("--output", required=True, type=Path)
    transcription.add_argument("--model", default="large-v3-turbo")
    transcription.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    transcription.add_argument("--compute-type", default="int8")
    transcription.add_argument("--threads", default=12, type=int)
    transcription.set_defaults(handler=transcribe)
    visual = subparsers.add_parser("vision")
    visual.add_argument("--input", required=True, type=Path)
    visual.add_argument("--output", required=True, type=Path)
    visual.add_argument("--sample-seconds", default=5.0, type=float)
    visual.add_argument("--subtitle-box", nargs=4, type=float, default=[0.05, 0.84, 0.85, 0.96])
    visual.add_argument("--ocr", action="store_true")
    visual.set_defaults(handler=vision)
    acoustic = subparsers.add_parser("audio")
    acoustic.add_argument("--input", required=True, type=Path)
    acoustic.add_argument("--output", required=True, type=Path)
    acoustic.set_defaults(handler=audio_metrics)
    args = parser.parse_args()
    args.handler(args)


if __name__ == "__main__":
    main()
