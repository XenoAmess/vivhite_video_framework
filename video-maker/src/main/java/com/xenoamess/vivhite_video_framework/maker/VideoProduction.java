package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.awt.GraphicsEnvironment;
import java.awt.image.DataBufferByte;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import javax.imageio.ImageIO;

/** Production orchestration: plan -> speech -> measured timeline -> animation -> mux -> decode audit. */
public final class VideoProduction {
    private VideoProduction() { }

    static String executable(String variable, String fallback) {
        String value = System.getenv(variable);
        return value == null || value.isBlank() ? fallback : value;
    }

    private static String font(JsonNode plan) {
        String font = plan.path("fontFamily").asText("Microsoft YaHei");
        ProductionPlan.require(Arrays.asList(GraphicsEnvironment.getLocalGraphicsEnvironment().getAvailableFontFamilyNames())
                .contains(font), "Install configured Chinese font or change fontFamily: " + font);
        return font;
    }

    public static void preview(Path planFile, Path directory, Path avatar) throws Exception {
        JsonNode plan = ProductionPlan.load(planFile);
        Files.createDirectories(directory);
        var presenter = PresenterAsset.open(avatar, directory, executable("FFMPEG", "ffmpeg"));
        var canvas = new MathCanvas(plan.path("width").asInt(), plan.path("height").asInt(), presenter, font(plan));
        int i = 0;
        var manifest = DirectorScript.JSON.createObjectNode().put("kind", "technical_preview_not_encoded_film");
        var samples = manifest.putArray("samples");
        for (JsonNode beat : plan.path("beats")) {
            ObjectNode timing = DirectorScript.JSON.createObjectNode().put("frames", 300).put("fps", 30);
            timing.putArray("captions").addObject().put("start", 0).put("end", 10)
                    .put("text", beat.path("narration").asText().substring(0, Math.min(22, beat.path("narration").asText().length())));
            ImageIO.write(canvas.render(beat, timing, 5.2, 5.2, i++, plan.path("beats").size()), "png",
                    directory.resolve(beat.path("id").asText() + ".png").toFile());
            if (beat.path("view").asText().equals("proof")) {
                int steps = beat.path("proof").path("steps").size();
                double duration = Math.max(10, steps * 4);
                timing.put("frames", (int) (duration * 30));
                ((ObjectNode) timing.path("captions").get(0)).put("end", duration);
                var moments = timing.putArray("visualTimes");
                for (int step = 0; step < steps; step++) { moments.add(step * 4.0); }
                for (int step = 0; step < steps; step++) {
                    String file = beat.path("id").asText() + "-proof-step-" + String.format(java.util.Locale.ROOT, "%03d", step + 1) + ".png";
                    double seconds = (step + 0.90) * 4;
                    ImageIO.write(canvas.render(beat, timing, seconds, seconds, i - 1, plan.path("beats").size()),
                            "png", directory.resolve(file).toFile());
                    samples.addObject().put("beatId", beat.path("id").asText()).put("proofStep", step)
                            .put("file", file);
                }
            }
        }
        write(directory.resolve("preview-manifest.json"), manifest);
        System.out.println("Preview frames: " + directory);
    }

    public static void produce(Path planFile, Path directory, Path avatar, String python) throws Exception {
        JsonNode plan = ProductionPlan.load(planFile);
        String font = font(plan);
        Files.createDirectories(directory);
        Path worker = Path.of(executable("MAKER_WORKER", "video-maker/tools/production_worker.py")).toAbsolutePath();
        ProductionPlan.require(Files.isRegularFile(worker), "Missing TTS worker: " + worker);
        String ffmpeg = executable("FFMPEG", "ffmpeg");
        String ffprobe = executable("FFPROBE", "ffprobe");
        String planHash = DirectorScript.fingerprint(planFile);
        ObjectNode run = DirectorScript.JSON.createObjectNode().put("schemaVersion", "vivhite-run-1")
                .put("startedAt", Instant.now().toString()).put("planSha256", planHash)
                .put("presenterSha256", DirectorScript.fingerprint(avatar)).put("status", "running");
        Path attempts = directory.resolve("attempts");
        Files.createDirectories(attempts);
        Path receipt = attempts.resolve(Instant.now().toString().replaceAll("[:.]", "-") + ".json");
        write(receipt, run);
        try {
            System.out.println("Synthesizing narration (validated cache is reused)…");
            var speechCommand = new ArrayList<>(List.of(python, worker.toString(), planFile.toAbsolutePath().toString(),
                    directory.toAbsolutePath().toString(), "--ffmpeg", ffmpeg));
            if ("1".equals(System.getenv("MAKER_OFFLINE_TTS"))) { speechCommand.add("--offline"); }
            if (System.getenv("MAKER_TTS_CACHE") != null) { speechCommand.addAll(List.of("--cache-dir", System.getenv("MAKER_TTS_CACHE"))); }
            String speechLog = MediaProcess.run(speechCommand, Duration.ofMinutes(30));
            Files.writeString(directory.resolve("tts.log"), speechLog, StandardCharsets.UTF_8);
            System.out.print(speechLog);
            JsonNode timeline = DirectorScript.JSON.readTree(directory.resolve("timeline.json").toFile());
            ProductionPlan.require(timeline.path("planSha256").asText().equals(planHash), "Stale audio timeline");
            ProductionPlan.require(timeline.path("beats").size() == plan.path("beats").size(), "Incomplete audio timeline");
            int fps = plan.path("fps").asInt();
            int width = plan.path("width").asInt();
            int height = plan.path("height").asInt();
            var presenter = PresenterAsset.open(avatar, directory, ffmpeg);
            var canvas = new MathCanvas(width, height, presenter, font);
            Path segments = directory.resolve("segments");
            Path frames = directory.resolve("review-frames");
            Files.createDirectories(segments);
            Files.createDirectories(frames);
            String engineHash = engineHash();
            String codec = plan.path("videoCodec").asText("libx264");
            ProductionPlan.require(codec.equals("libx264") || codec.equals("h264_nvenc"), "Unsupported video encoder");
            StringBuilder concat = new StringBuilder("ffconcat version 1.0\n");
            StringBuilder director = new StringBuilder("# " + plan.path("title").asText() + " · 实际制作稿\n\n");
            for (int i = 0; i < plan.path("beats").size(); i++) {
                JsonNode beat = plan.path("beats").get(i);
                ObjectNode timing = ((ObjectNode) timeline.path("beats").get(i)).deepCopy().put("fps", fps);
                ProductionPlan.require(timing.path("id").asText().equals(beat.path("id").asText()), "Misordered audio timeline");
                String id = beat.path("id").asText();
                int frameCount = timing.path("frames").asInt();
                double start = timing.path("startFrame").asDouble() / fps;
                Path target = segments.resolve(id + ".mp4");
                Path partial = segments.resolve(id + ".partial.mp4");
                Path cacheFile = segments.resolve(id + ".json");
                String renderKey = hash((engineHash + width + "x" + height + ":" + fps + ":" + codec + ":" + i
                        + ":" + plan.path("beats").size() + beat + timing + run.path("presenterSha256").asText()
                        + font).getBytes(StandardCharsets.UTF_8));
                boolean cached = false;
                if (Files.exists(cacheFile) && Files.exists(target)) {
                    JsonNode metadata = DirectorScript.JSON.readTree(cacheFile.toFile());
                    cached = metadata.path("key").asText().equals(renderKey)
                            && metadata.path("sha256").asText().equals(DirectorScript.fingerprint(target));
                }
                if (!cached) {
                    System.out.printf("Render %d/%d %s (%.2fs)%n", i + 1, plan.path("beats").size(), id, frameCount / (double) fps);
                    var command = new ArrayList<>(List.of(ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pixel_format", "bgr24",
                            "-video_size", width + "x" + height, "-framerate", String.valueOf(fps), "-i", "pipe:0", "-an",
                            "-c:v", codec, "-pix_fmt", "yuv420p"));
                    if (codec.equals("h264_nvenc")) { command.addAll(List.of("-preset", "p5", "-rc", "vbr", "-cq", "20", "-b:v", "0")); }
                    else { command.addAll(List.of("-preset", "fast", "-crf", "20", "-threads", "6")); }
                    command.addAll(List.of("-video_track_timescale", "90000", partial.toAbsolutePath().toString()));
                    final int beatIndex = i;
                    MediaProcess.run(command, Duration.ofMinutes(15), stream -> {
                        for (int f = 0; f < frameCount; f++) {
                            var frame = canvas.render(beat, timing, f / (double) fps, start + f / (double) fps,
                                    beatIndex, plan.path("beats").size());
                            stream.write(((DataBufferByte) frame.getRaster().getDataBuffer()).getData());
                        }
                    });
                    JsonNode probe = probe(ffprobe, partial);
                    JsonNode video = probe.path("streams").get(0);
                    ProductionPlan.require(video.path("nb_frames").asLong() == frameCount, "Segment frame count mismatch: " + id);
                    Files.move(partial, target, StandardCopyOption.REPLACE_EXISTING);
                    write(cacheFile, DirectorScript.JSON.createObjectNode().put("key", renderKey)
                            .put("sha256", DirectorScript.fingerprint(target)).put("frames", frameCount));
                } else { System.out.println("Cached render: " + id); }
                double sampleTime = frameCount / (double) fps * 0.56;
                ImageIO.write(canvas.render(beat, timing, sampleTime, start + sampleTime, i, plan.path("beats").size()), "png",
                        frames.resolve(id + ".png").toFile());
                // Relative names are generated from validated IDs, so concat paths contain no user quoting.
                concat.append("file 'segments/").append(id).append(".mp4'\n");
                director.append("## ").append(id).append(" · ").append(beat.path("chapter").asText()).append(" / ")
                        .append(beat.path("heading").asText()).append("\n\n时间：")
                        .append(String.format(java.util.Locale.ROOT, "%.2f–%.2f 秒", start, start + frameCount / (double) fps))
                        .append("\n\n旁白：").append(beat.path("narration").asText())
                        .append("\n\n画面动作：").append(beat.path("action").asText())
                        .append("\n\n屏幕关系：").append(beat.path("formula").asText()).append("\n\n");
            }
            Files.writeString(directory.resolve("segments.ffconcat"), concat, StandardCharsets.UTF_8);
            Files.writeString(directory.resolve("director-timed.md"), director, StandardCharsets.UTF_8);
            Path partial = directory.resolve("film.partial.mp4");
            Path film = directory.resolve("film.mp4");
            MediaProcess.run(List.of(ffmpeg, "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i",
                    directory.resolve("segments.ffconcat").toAbsolutePath().toString(), "-i", directory.resolve("narration.wav").toString(),
                    "-map", "0:v:0", "-map", "1:a:0",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-af", "loudnorm=I=-16:TP=-1.5:LRA=9",
                    "-metadata", "title=" + plan.path("title").asText(),
                    "-movflags", "+faststart", partial.toString()), Duration.ofMinutes(5));
            JsonNode finalProbe = probe(ffprobe, partial);
            JsonNode video = finalProbe.path("streams").get(0);
            ProductionPlan.require(finalProbe.path("streams").size() == 2
                    && finalProbe.path("streams").get(1).path("codec_type").asText().equals("audio"),
                    "Expected video and audio only; subtitles are burned and supplied separately");
            ProductionPlan.require(video.path("width").asInt() == width && video.path("height").asInt() == height
                    && video.path("nb_frames").asLong() == timeline.path("totalFrames").asLong(), "Final geometry/frame count mismatch");
            double expected = timeline.path("durationSeconds").asDouble();
            ProductionPlan.require(Math.abs(finalProbe.path("format").path("duration").asDouble() - expected) < 0.12,
                    "Final audio/video duration mismatch");
            System.out.println("Decoding the complete film for errors…");
            MediaProcess.run(List.of(ffmpeg, "-v", "error", "-xerror", "-i", partial.toString(), "-map", "0:v:0", "-map", "0:a:0",
                    "-f", "null", "-"), Duration.ofMinutes(10));
            Files.move(partial, film, StandardCopyOption.REPLACE_EXISTING);
            write(directory.resolve("ffprobe.json"), finalProbe);
            run.put("status", "rendered_and_fully_decoded").put("finishedAt", Instant.now().toString())
                    .put("filmSha256", DirectorScript.fingerprint(film)).put("bytes", Files.size(film))
                    .put("durationSeconds", expected).put("totalFrames", timeline.path("totalFrames").asLong())
                    .put("renderEngineSha256", engineHash).put("humanReview", "not_recorded")
                    .put("styleSimilarity", "not_certified").put("presenterMode", presenter.isStill() ? "image_placeholder" : "video_loop");
            write(directory.resolve("production-report.json"), run);
            System.out.println("Film: " + film.toAbsolutePath());
        } catch (Exception failure) {
            run.put("status", "failed").put("error", failure.toString()).put("finishedAt", Instant.now().toString());
            throw failure;
        } finally { write(receipt, run); }
    }

    private static JsonNode probe(String executable, Path file) throws Exception {
        return DirectorScript.JSON.readTree(MediaProcess.run(List.of(executable, "-v", "error", "-show_streams", "-show_format",
                "-of", "json", file.toAbsolutePath().toString()), Duration.ofSeconds(45)));
    }

    private static String engineHash() throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        for (Class<?> type : List.of(VideoProduction.class, MathCanvas.class, ProofCanvas.class, ProofScene.class, MathText.class,
                PresenterAsset.class, PuzzleMath.class, ProductionPlan.class)) {
            classFingerprint(digest, type);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static void classFingerprint(MessageDigest digest, Class<?> type) throws Exception {
        try (var stream = type.getResourceAsStream("/" + type.getName().replace('.', '/') + ".class")) {
            if (stream == null) { throw new IllegalStateException("Missing class fingerprint"); }
            digest.update(stream.readAllBytes());
        }
        for (Class<?> nested : Arrays.stream(type.getDeclaredClasses()).sorted(Comparator.comparing(Class::getName)).toList()) {
            classFingerprint(digest, nested);
        }
    }

    private static String hash(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    private static void write(Path path, JsonNode value) throws Exception {
        Path temporary = path.resolveSibling(path.getFileName() + ".tmp");
        Files.writeString(temporary, value.toPrettyString() + "\n", StandardCharsets.UTF_8);
        Files.move(temporary, path, StandardCopyOption.REPLACE_EXISTING);
    }
}
