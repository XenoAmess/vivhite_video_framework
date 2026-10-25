package com.xenoamess.vivhite_video_framework.analyzer;

import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.JSON;
import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.requiredText;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

public final class AnalysisPipeline {
    private AnalysisPipeline() { }

    public static void prepare(Path configFile, Path directory, boolean reuseOnly) throws Exception {
        JsonNode config = JsonFiles.read(configFile);
        String caseId = requiredText(config, "caseId");
        if (!caseId.matches("[A-Za-z0-9_-]+")) {
            throw new IllegalArgumentException("caseId must contain only letters, digits, underscores and hyphens");
        }
        int windowMs = config.path("windowSeconds").asInt(30) * 1000;
        if (windowMs < 1000 || windowMs > 120000) {
            throw new IllegalArgumentException("windowSeconds must be between 1 and 120");
        }
        Files.createDirectories(directory);
        ObjectNode workspace = JSON.createObjectNode().put("schemaVersion", "1.0").put("caseId", caseId);
        workspace.put("status", "preparing");
        workspace.set("config", config);
        ObjectNode sources = workspace.putObject("sources");
        ArrayNode packets = workspace.putArray("packets");
        JsonFiles.write(directory.resolve("workspace.json"), workspace);
        for (String role : List.of("content", "style")) {
            Path sourcePath = Path.of(requiredText(config, role + "Video")).toAbsolutePath().normalize();
            if (!Files.isRegularFile(sourcePath)) {
                throw new IOException("Video does not exist: " + sourcePath);
            }
            Path roleDirectory = directory.resolve(role);
            Files.createDirectories(roleDirectory);
            String sha256 = JsonFiles.sha256(sourcePath);
            JsonNode probe = JSON.readTree(Processes.capture(List.of("ffprobe", "-v", "error", "-show_format",
                    "-show_streams", "-of", "json", sourcePath.toString()), Duration.ofMinutes(2)));
            long durationMs = Math.round(probe.path("format").path("duration").asDouble() * 1000);
            if (durationMs <= 0) {
                throw new IOException("Cannot determine positive source duration: " + sourcePath);
            }
            ObjectNode source = sources.putObject(role).put("path", sourcePath.toString())
                    .put("sha256", sha256).put("durationMs", durationMs);
            source.set("probe", probe);
            JsonFiles.write(roleDirectory.resolve("source.json"), source);
            JsonFiles.write(directory.resolve("workspace.json"), workspace);
            if (!reuseOnly) {
                String python = requiredText(config, "python");
                String worker = requiredText(config, "worker");
                Processes.live(List.of(python, worker, "transcribe", "--input", sourcePath.toString(),
                        "--output", roleDirectory.toString(), "--model", config.path("asrModel").asText("large-v3-turbo"),
                        "--device", config.path("device").asText("cpu"), "--compute-type",
                        config.path("computeType").asText("int8"), "--threads", config.path("threads").asText("12")),
                        Duration.ofHours(4));
                var command = new ArrayList<>(List.of(python, worker, "vision", "--input", sourcePath.toString(),
                        "--output", roleDirectory.toString(), "--sample-seconds",
                        config.path("frameSampleSeconds").asText("5")));
                if (config.path(role + "Ocr").asBoolean(true)) {
                    command.add("--ocr");
                }
                if (config.path(role + "SubtitleBox").isArray()) {
                    command.add("--subtitle-box");
                    config.path(role + "SubtitleBox").forEach(value -> command.add(value.asText()));
                }
                Processes.live(command, Duration.ofHours(4));
                Processes.live(List.of(python, worker, "audio", "--input", sourcePath.toString(),
                        "--output", roleDirectory.toString()), Duration.ofMinutes(10));
            }
            JsonNode transcript = requireArtifact(roleDirectory.resolve("transcript.json"), sha256);
            JsonNode vision = requireArtifact(roleDirectory.resolve("vision.json"), sha256);
            if (vision.at("/identity/ocr").asBoolean() != config.path(role + "Ocr").asBoolean(true)
                    || Double.compare(vision.at("/identity/sampleSeconds").asDouble(),
                            config.path("frameSampleSeconds").asDouble(5)) != 0
                    || !transcript.at("/identity/model").asText().equals(config.path("asrModel").asText("large-v3-turbo"))) {
                throw new IOException("Cached model/OCR/frame interval differs from case configuration; rerun without --reuse");
            }
            JsonNode audio = JsonFiles.read(roleDirectory.resolve("audio-metrics.json"));
            if (!audio.path("status").asText().equals("complete")
                    || !audio.path("sourceSha256").asText().equals(sha256)
                    || Math.abs(audio.path("durationMs").asLong() - durationMs) > 500) {
                throw new IOException("Audio measurement fingerprint or duration mismatch");
            }
            validateMediaCoverage(transcript, vision, durationMs);
            source.put("transcriptSegments", transcript.path("segments").size());
            source.put("decodedFrames", vision.path("decodedFrames").asLong());
            source.put("selectedFrames", vision.path("frames").size());
            source.put("ocrObservations", vision.path("subtitleObservations").size());
            source.put("asrQuality", transcript.path("qualityStatus").asText());
            source.put("ocrCompleteness", vision.path("ocrPolicy").path("recognitionCompleteness").asText());
            for (long start = 0, index = 1; start < durationMs; start += windowMs, index++) {
                long end = Math.min(start + windowMs, durationMs);
                String id = role + "-w%04d".formatted(index);
                ObjectNode packet = buildPacket(role, id, start, end, transcript, vision);
                ArrayNode audioBins = packet.putArray("audioRmsBins");
                for (JsonNode bin : audio.path("bins")) {
                    if (bin.path("startMs").asLong() < end && bin.path("endMs").asLong() > start) {
                        audioBins.add(bin);
                    }
                }
                String relative = "packets/" + id + ".json";
                JsonFiles.write(directory.resolve(relative), packet);
                packets.addObject().put("id", id).put("role", role).put("path", relative)
                        .put("startMs", start).put("endMs", end);
            }
        }
        workspace.put("status", "evidence_ready");
        workspace.put("semanticReviewStatus", "not_run");
        workspace.put("manualPlaybackStatus", "not_run");
        JsonFiles.write(directory.resolve("workspace.json"), workspace);
        JsonFiles.writeText(directory.resolve("review-instructions.md"), "# 案例审查任务\n\n"
                + "逐一阅读 packets/ 中全部连续窗口及其原始转写、OCR 和图像。\n"
                + "内容来源与风格来源分别审查；为每个语音段返回 unitReviews，并为每个窗口写 summary。\n"
                + "审查结果通过 import-review 导入；它会验证来源指纹、全部窗口及全部语音段覆盖。\n"
                + "解码完成、机器转写完成与语义审查完成为不同状态；不得混用。\n");
        System.out.println("Evidence prepared: " + packets.size() + " windows at " + directory);
    }

    private static JsonNode requireArtifact(Path file, String sha256) throws IOException {
        JsonNode artifact = JsonFiles.read(file);
        if (!artifact.path("status").asText().equals("complete")
                || !artifact.path("identity").path("sourceSha256").asText().equals(sha256)) {
            throw new IOException("Incomplete artifact or source fingerprint mismatch: " + file);
        }
        return artifact;
    }

    static void validateMediaCoverage(JsonNode transcript, JsonNode vision, long durationMs) {
        if (Math.abs(transcript.path("durationMs").asLong() - durationMs) > 500
                || Math.abs(vision.path("decodedEndMs").asLong() - durationMs) > 500
                || vision.path("decodedFrames").asLong() <= 0
                || !vision.path("decodeGaps").isArray() || !vision.path("decodeGaps").isEmpty()
                || !vision.path("nonMonotonicPts").isArray() || !vision.path("nonMonotonicPts").isEmpty()) {
            throw new IllegalArgumentException("Media coverage is incomplete; inspect decoding and audio durations");
        }
        if (!transcript.path("segments").isArray() || transcript.path("segments").isEmpty()) {
            throw new IllegalArgumentException("Transcription is empty");
        }
        for (JsonNode segment : transcript.path("segments")) {
            if (segment.path("startMs").asLong(-1) < 0 || segment.path("endMs").asLong() <= segment.path("startMs").asLong()
                    || segment.path("endMs").asLong() > durationMs + 500) {
                throw new IllegalArgumentException("Invalid ASR interval: " + segment.path("id"));
            }
        }
    }

    static ObjectNode buildPacket(String role, String id, long start, long end,
                                  JsonNode transcript, JsonNode vision) {
        ObjectNode packet = JSON.createObjectNode().put("id", id).put("role", role)
                .put("startMs", start).put("endMs", end);
        ArrayNode units = packet.putArray("units");
        transcript.path("segments").forEach(segment -> {
            if (segment.path("startMs").asLong() < end && segment.path("endMs").asLong() > start) {
                units.add(segment);
            }
        });
        ArrayNode frames = packet.putArray("frames");
        vision.path("frames").forEach(frame -> {
            if (frame.path("timeMs").asLong() >= start && frame.path("timeMs").asLong() < end) {
                frames.add(frame);
            }
        });
        ArrayNode subtitles = packet.putArray("subtitleObservations");
        vision.path("subtitleObservations").forEach(observation -> {
            if (observation.path("timeMs").asLong() < end
                    && observation.path("lastObservedMs").asLong() >= start) {
                subtitles.add(observation);
            }
        });
        packet.put("audioListeningStatus", "not_provided_to_text_image_model");
        packet.set("ocrPolicy", vision.path("ocrPolicy"));
        return packet;
    }
}
