"""Edge narration, real audio timing and sample-exact assembly. GPL-3.0-only."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import subprocess
import unicodedata
import wave

import edge_tts


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def command(argv: list[str], timeout: int = 120) -> None:
    result = subprocess.run(argv, capture_output=True, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace")[-6000:])


def pcm_samples(path: Path) -> int:
    with wave.open(str(path), "rb") as source:
        if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (1, 2, 48000):
            raise ValueError("Unexpected cached PCM format")
        frames = source.getnframes()
        if frames < 2400 or len(source.readframes(frames)) != frames * 2:
            raise ValueError("Empty or truncated audio")
        return frames


def restore_punctuation(events: list[dict], narration: str) -> list[dict]:
    """Restore authored punctuation only when provider words match it exactly."""
    positions = [i for i, c in enumerate(narration) if unicodedata.category(c)[0] in "LN"]
    authored = "".join(narration[i] for i in positions)
    spoken = "".join(c for e in events for c in e["text"] if unicodedata.category(c)[0] in "LN")
    if authored != spoken:
        return events
    result = []
    cursor = 0
    for event in events:
        length = sum(unicodedata.category(c)[0] in "LN" for c in event["text"])
        if not length:
            continue
        start = positions[cursor]
        cursor += length
        end = positions[cursor] if cursor < len(positions) else len(narration)
        result.append({**event, "text": narration[start:end]})
    return result


def caption_groups(events: list[dict]) -> list[dict]:
    """Retain provider word times; break Chinese at punctuation or 22 characters."""
    groups: list[dict] = []
    words: list[dict] = []
    for event in events:
        text = event["text"]
        if words and len("".join(w["text"] for w in words)) + len(text) > 22:
            groups.append(group(words))
            words = []
        words.append(event)
        if re.search(r"[，。！？；：!?;]$", text):
            groups.append(group(words))
            words = []
    if words:
        groups.append(group(words))
    return groups


def group(words: list[dict]) -> dict:
    return {"start": words[0]["start"], "end": words[-1]["end"],
            "text": "".join(w["text"] for w in words)}


def letters(value: str) -> str:
    return "".join(c for c in value if unicodedata.category(c)[0] in "LN")


def phrase_times(beat: dict, words: list[dict], cues: list[dict]) -> list[float]:
    text = letters(beat["narration"])
    if text != "".join(letters(w["text"]) for w in words):
        raise ValueError(f"Cannot bind action cues to changed provider text: {beat['id']}")
    timed = []
    for word in words:
        timed.extend([word["start"]] * len(letters(word["text"])))
    result = []
    for cue in cues:
        index = text.find(letters(cue["phrase"]))
        if index < 0:
            raise ValueError(f"Action phrase missing in {beat['id']}: {cue['phrase']}")
        result.append(timed[index] + cue.get("delay", 0))
    return result


def action_times(beat: dict, words: list[dict], duration: float) -> list[float]:
    """Bind authored actions to actual provider words instead of a planned clock."""
    if not beat.get("moveCues"):
        return []
    result = phrase_times(beat, words, beat["moveCues"])
    if len(result) != len(beat["states"]) - 1 or any(t < 0 or t + 0.75 > duration for t in result):
        raise ValueError(f"Action cues exceed beat duration: {beat['id']}")
    if any(b - a < 0.8 for a, b in zip(result, result[1:])):
        raise ValueError(f"Overlapping action cues: {beat['id']}")
    return result


async def synthesize_one(beat: dict, voice: dict, cache: Path, semaphore: asyncio.Semaphore,
                         ffmpeg: str, offline: bool) -> dict:
    request = {"schema": 1, "providerVersion": importlib.metadata.version("edge-tts"),
               "text": beat["narration"], "voice": voice["name"], "rate": voice["rate"],
               "pitch": voice.get("pitch", "+0Hz"), "volume": voice.get("volume", "+0%"),
               "boundary": "WordBoundary"}
    key = digest(json.dumps(request, sort_keys=True, ensure_ascii=False).encode())
    folder = cache / key
    folder.mkdir(parents=True, exist_ok=True)
    audio = folder / "audio.wav"
    metadata = folder / "tts.json"
    if metadata.exists() and audio.exists():
        saved = json.loads(metadata.read_text(encoding="utf-8"))
        if saved["request"] == request and saved["audioSha256"] == digest(audio.read_bytes()):
            samples = pcm_samples(audio)
            return {**saved, "samples": samples, "audio": str(audio.resolve()), "cacheKey": key}
    if offline:
        raise RuntimeError(f"Offline TTS cache miss: {beat['id']}")
    async with semaphore:
        for attempt in range(3):
            try:
                events = []
                mp3 = folder / "audio.partial.mp3"
                communicator = edge_tts.Communicate(
                    request["text"], request["voice"], rate=request["rate"],
                    pitch=request["pitch"], volume=request["volume"], boundary="WordBoundary")
                with mp3.open("wb") as target:
                    async for chunk in communicator.stream():
                        if chunk["type"] == "audio":
                            target.write(chunk["data"])
                        elif chunk["type"] == "WordBoundary":
                            events.append({"text": chunk["text"], "start": chunk["offset"] / 10_000_000,
                                           "end": (chunk["offset"] + chunk["duration"]) / 10_000_000})
                if not events:
                    raise RuntimeError("Edge returned no word boundaries; refusing guessed subtitles")
                partial = folder / "audio.partial.wav"
                await asyncio.to_thread(command, [ffmpeg, "-v", "error", "-y", "-i", str(mp3),
                                                  "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(partial)])
                samples = pcm_samples(partial)
                partial.replace(audio)
                saved = {"request": request, "samples": samples, "audioSha256": digest(audio.read_bytes()),
                         "captions": caption_groups(events), "wordBoundaries": events}
                write_json(metadata, saved)
                mp3.replace(folder / "audio.mp3")
                print(f"TTS {beat['id']}: {samples / 48000:.2f}s", flush=True)
                return {**saved, "audio": str(audio.resolve()), "cacheKey": key}
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Unreachable")


def srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    return f"{milliseconds // 3600000:02}:{milliseconds // 60000 % 60:02}:{milliseconds // 1000 % 60:02},{milliseconds % 1000:03}"


async def produce(plan_path: Path, output: Path, ffmpeg: str, offline: bool, cache: Path | None = None) -> None:
    raw = plan_path.read_bytes()
    plan = json.loads(raw)
    output.mkdir(parents=True, exist_ok=True)
    cache = cache or output / "tts-cache"
    cache.mkdir(parents=True, exist_ok=True)
    semaphore = asyncio.Semaphore(3)
    # Repeated narration shares one in-flight request and one cache writer.
    tasks = {}
    for beat in plan["beats"]:
        if beat["narration"] not in tasks:
            tasks[beat["narration"]] = asyncio.create_task(synthesize_one(
                beat, plan["voice"], cache, semaphore, ffmpeg, offline))
    results = await asyncio.gather(*(tasks[beat["narration"]] for beat in plan["beats"]))
    fps = plan["fps"]
    timeline = {"schemaVersion": "vivhite-timeline-1", "planSha256": digest(raw), "fps": fps,
                "providerVersion": importlib.metadata.version("edge-tts"), "beats": []}
    offset = 0
    captions = []
    with wave.open(str(output / "narration.partial.wav"), "wb") as target:
        target.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
        for beat, speech in zip(plan["beats"], results, strict=True):
            frames = math.ceil((speech["samples"] / 48000 + 0.42) * fps)
            # All supported frame rates divide 48 kHz. No per-beat rounding drift.
            target_samples = frames * (48000 // fps)
            with wave.open(speech["audio"], "rb") as source:
                target.writeframes(source.readframes(source.getnframes()))
            target.writeframes(b"\0" * ((target_samples - speech["samples"]) * 2))
            local_captions = []
            groups = caption_groups(restore_punctuation(speech["wordBoundaries"], beat["narration"]))
            for i, caption in enumerate(groups):
                item = {**caption, "end": min(caption["end"] + 0.10, frames / fps)}
                if i + 1 < len(groups):
                    item["end"] = min(item["end"], groups[i + 1]["start"])
                if not 0 <= item["start"] < item["end"] <= frames / fps:
                    raise ValueError(f"Invalid provider subtitle timing: {beat['id']}")
                local_captions.append(item)
                captions.append({**item, "start": item["start"] + offset / fps, "end": item["end"] + offset / fps})
            pair_cues = beat.get("focusPairs", [])
            pair_times = phrase_times(beat, speech["wordBoundaries"], pair_cues) if pair_cues else []
            if any(t < 0 or t >= frames / fps for t in pair_times) or pair_times != sorted(pair_times):
                raise ValueError(f"Invalid pair focus timing: {beat['id']}")
            timeline["beats"].append({"id": beat["id"], "startFrame": offset, "frames": frames,
                                      "speechSeconds": speech["samples"] / 48000, "cacheKey": speech["cacheKey"],
                                      "moveTimes": action_times(beat, speech["wordBoundaries"], frames / fps),
                                      "pairFocus": [{"time": t, "pair": cue["pair"]} for t, cue in zip(pair_times, pair_cues)],
                                      "captions": local_captions})
            offset += frames
    (output / "narration.partial.wav").replace(output / "narration.wav")
    timeline["totalFrames"] = offset
    timeline["durationSeconds"] = offset / fps
    timeline["narrationSha256"] = digest((output / "narration.wav").read_bytes())
    write_json(output / "timeline.json", timeline)
    (output / "subtitles.srt").write_text("\n\n".join(
        f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}" for i, c in enumerate(captions, 1)) + "\n", encoding="utf-8", newline="\n")
    (output / "production-plan.json").write_bytes(raw)
    print(f"Timeline: {offset / fps:.2f}s / {offset} frames", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--cache-dir", type=Path)
    args = parser.parse_args()
    asyncio.run(produce(args.plan, args.output, args.ffmpeg, args.offline, args.cache_dir))
