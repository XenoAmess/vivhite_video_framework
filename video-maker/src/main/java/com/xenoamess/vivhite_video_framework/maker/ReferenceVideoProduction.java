package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashSet;
import java.util.List;

/** Generate real reference-conditioned clips with review gates and resumable remote jobs. */
final class ReferenceVideoProduction {
    private ReferenceVideoProduction() { }

    static List<Path> references(Path planFile, JsonNode shot) throws IOException {
        var paths = new ArrayList<Path>();
        Path owner = planFile.toAbsolutePath().normalize().getParent();
        for (JsonNode item : shot.path("references")) {
            Path path = owner.resolve(item.asText()).normalize();
            if (Path.of(item.asText()).isAbsolute() || !path.startsWith(owner)
                    || !Files.isRegularFile(path) || !path.toRealPath().startsWith(owner.toRealPath())) {
                throw new IOException("Reference must be an existing file inside the episode directory");
            }
            paths.add(path);
        }
        if (paths.isEmpty() || paths.size() > 9) { throw new IOException("Each shot needs 1-9 reference images"); }
        return paths;
    }

    static JsonNode load(Path file) throws IOException {
        JsonNode plan = DirectorScript.JSON.readTree(file.toFile());
        if (!plan.path("schemaVersion").asText().equals("vivhite-reference-video-1")
                || plan.path("fps").asInt() != 30 || plan.path("width").asInt() != 1920
                || plan.path("height").asInt() != 1080 || !plan.path("noSpeech").asBoolean()
                || !plan.path("noHumanFaces").asBoolean() || !plan.path("allCharactersFemale").asBoolean()
                || plan.path("costumeStyle").asText().isBlank() || !plan.path("shots").isArray()
                || plan.path("shots").isEmpty()) {
            throw new IOException("Invalid silent reference-video plan");
        }
        var ids = new LinkedHashSet<String>();
        int expected = 0;
        for (JsonNode shot : plan.path("shots")) {
            String id = shot.path("id").asText();
            int seconds = shot.path("seconds").asInt();
            int source = shot.path("sourceSeconds").asInt();
            if (!id.matches("S[0-9]{2}") || !ids.add(id) || seconds < 2 || seconds > 10
                    || (source != 5 && source != 10) || source < seconds
                    || shot.path("startFrame").asInt(-1) != expected || shot.path("prompt").asText().isBlank()) {
                throw new IOException("Invalid shot identity, contiguous timing or 2-10-second duration");
            }
            references(file, shot);
            expected += seconds * 30;
        }
        if (expected != plan.path("totalFrames").asInt()) { throw new IOException("Plan total frames do not match shots"); }
        return plan;
    }

    static void produce(Path episode, Path planFile, Path out, URI base, String python) throws Exception {
        JsonNode plan = load(planFile);
        var assets = new LinkedHashSet<Path>();
        for (JsonNode shot : plan.path("shots")) { assets.addAll(references(planFile, shot)); }
        var gate = new ArrayList<>(List.of(python, "scripts/character_review.py", "check", "--episode",
                episode.toString(), "--document", planFile.toString()));
        for (Path asset : assets) { gate.addAll(List.of("--asset", asset.toString())); }
        System.out.print(MediaProcess.run(gate, Duration.ofMinutes(2)));
        Files.createDirectories(out.resolve("jobs"));
        Files.createDirectories(out.resolve("requests"));
        Files.createDirectories(out.resolve("attempts"));
        Files.createDirectories(out.resolve("sources"));
        Files.createDirectories(out.resolve("segments"));
        var provider = new FastH3VideoProvider(base);
        StringBuilder concat = new StringBuilder("ffconcat version 1.0\n");
        var run = DirectorScript.JSON.createObjectNode().put("schemaVersion", "vivhite-reference-run-1")
                .put("planSha256", DirectorScript.fingerprint(planFile)).put("startedAt", Instant.now().toString())
                .put("status", "running");
        write(out.resolve("run.json"), run);
        try {
            for (JsonNode shot : plan.path("shots")) {
                String id = shot.path("id").asText();
                var request = provider.request(shot.path("prompt").asText(), shot.path("sourceSeconds").asInt(),
                        plan.path("sourceSize").asText("1344x768"), shot.path("seed").asLong(), references(planFile, shot));
                String key = hash((base + "\n" + request).getBytes(StandardCharsets.UTF_8));
                Path receiptFile = out.resolve("jobs/" + id + ".json");
                ObjectNode receipt;
                if (Files.isRegularFile(receiptFile)) {
                    receipt = (ObjectNode) DirectorScript.JSON.readTree(receiptFile.toFile());
                    if (!receipt.path("requestSha256").asText().equals(key)) {
                        throw new IOException("Changed request for " + id + "; use a new output directory");
                    }
                } else {
                    receipt = DirectorScript.JSON.createObjectNode().put("shotId", id).put("requestSha256", key)
                            .put("status", "prepared");
                    write(receiptFile, receipt);
                }
                // The server's in-memory index does not survive restarts. Keep the full exact request locally.
                Path requestFile = out.resolve("requests/" + id + ".json");
                if (!Files.isRegularFile(requestFile)) { write(requestFile, request); }
                String jobId = receipt.path("jobId").asText();
                Path source = out.resolve("sources/" + id + ".mp4");
                boolean cached = Files.isRegularFile(source) && DirectorScript.fingerprint(source)
                        .equals(receipt.path("sourceSha256").asText());
                if (!cached) {
                    if (receipt.path("status").asText().equals("prepared") || receipt.path("status").asText().equals("failed")) {
                        submit(provider, request, receipt, receiptFile, out);
                        jobId = receipt.path("jobId").asText();
                    }
                    if (jobId.isBlank()) { throw new IOException("Ambiguous previous POST for " + id + "; inspect remote jobs before retrying"); }
                    long deadline = System.nanoTime() + Duration.ofMinutes(45).toNanos();
                    String lastState = "";
                    boolean restarted = false;
                    while (true) {
                        if (Thread.currentThread().isInterrupted()) { throw new InterruptedException("Generation interrupted; job ID retained"); }
                        JsonNode status;
                        try {
                            status = provider.status(jobId);
                        } catch (FastH3VideoProvider.ApiException error) {
                            if (error.statusCode != 404 || restarted) { throw error; }
                            // The service owner confirmed that a missing indexed job must be resubmitted.
                            submit(provider, request, receipt, receiptFile, out);
                            jobId = receipt.path("jobId").asText();
                            restarted = true;
                            continue;
                        }
                        String state = status.path("status").asText();
                        receipt.set("remote", status);
                        receipt.put("status", state);
                        write(receiptFile, receipt);
                        if (!state.equals(lastState)) { System.out.println(id + " " + state + " " + jobId); lastState = state; }
                        if (state.equals("failed")) {
                            throw new IOException(id + " failed on model service: " + status.path("error").path("message").asText());
                        }
                        if (state.equals("completed")) { break; }
                        if (!List.of("queued", "in_progress").contains(state)) { throw new IOException("Unknown remote job state: " + state); }
                        if (System.nanoTime() > deadline) { throw new IOException(id + " polling timed out; resume using the saved job ID"); }
                        Thread.sleep(Duration.ofSeconds(3));
                    }
                    Path partial = out.resolve("sources/" + id + ".partial.mp4");
                    provider.download(jobId, partial);
                    MediaProcess.run(List.of(VideoProduction.executable("FFMPEG", "ffmpeg"), "-v", "error", "-xerror",
                            "-i", partial.toString(), "-f", "null", "-"), Duration.ofMinutes(5));
                    Files.move(partial, source, StandardCopyOption.REPLACE_EXISTING);
                    receipt.put("sourceSha256", DirectorScript.fingerprint(source));
                    write(receiptFile, receipt);
                }
                Path segment = out.resolve("segments/" + id + ".mp4");
                Path partial = out.resolve("segments/" + id + ".partial.mp4");
                int frames = shot.path("seconds").asInt() * 30;
                String filter = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30";
                MediaProcess.run(List.of(VideoProduction.executable("FFMPEG", "ffmpeg"), "-v", "error", "-y",
                        "-i", source.toString(), "-map", "0:v:0", "-an", "-vf", filter,
                        "-frames:v", String.valueOf(frames), "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                        "-pix_fmt", "yuv420p", partial.toString()), Duration.ofMinutes(10));
                JsonNode probe = DirectorScript.JSON.readTree(MediaProcess.run(List.of(VideoProduction.executable("FFPROBE", "ffprobe"),
                        "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "json", partial.toString()), Duration.ofMinutes(3)));
                if (probe.path("streams").path(0).path("nb_read_frames").asInt() != frames) {
                    throw new IOException(id + " source too short or frame count mismatch");
                }
                Files.move(partial, segment, StandardCopyOption.REPLACE_EXISTING);
                receipt.put("segmentSha256", DirectorScript.fingerprint(segment)).put("segmentFrames", frames);
                write(receiptFile, receipt);
                concat.append("file '").append(segment.toAbsolutePath().toString().replace('\\', '/').replace("'", "'\\''")).append("'\n");
            }
            Files.writeString(out.resolve("segments.ffconcat"), concat, StandardCharsets.UTF_8);
            // This intermediate intentionally excludes unreviewed generated speech and is not the final sound mix.
            MediaProcess.run(List.of(VideoProduction.executable("FFMPEG", "ffmpeg"), "-v", "error", "-y", "-f", "concat",
                    "-safe", "0", "-i", out.resolve("segments.ffconcat").toString(), "-c", "copy", "-movflags", "+faststart",
                    out.resolve("picture-assembly.mp4").toString()), Duration.ofMinutes(10));
            run.put("status", "picture-assembly-completed-audio-and-semantic-review-pending");
        } catch (Exception error) {
            run.put("status", "incomplete").put("error", error.toString());
            throw error;
        } finally {
            run.put("updatedAt", Instant.now().toString());
            write(out.resolve("run.json"), run);
        }
    }

    private static String hash(byte[] value) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value));
    }

    private static void submit(FastH3VideoProvider provider, ObjectNode request, ObjectNode receipt,
                               Path receiptFile, Path out) throws Exception {
        if (receipt.hasNonNull("jobId")) {
            write(out.resolve("attempts/" + receipt.path("shotId").asText() + "-"
                    + java.util.UUID.randomUUID() + ".json"), receipt);
        }
        receipt.remove("jobId");
        receipt.remove("remote");
        receipt.put("status", "submitting");
        write(receiptFile, receipt);
        // A timed-out POST is never blindly repeated: the remote job may already have been created.
        JsonNode submitted = provider.submit(request);
        receipt.put("jobId", submitted.path("id").asText()).set("remote", submitted);
        receipt.put("status", "submitted");
        write(receiptFile, receipt);
    }

    private static void write(Path file, JsonNode value) throws IOException {
        Path partial = file.resolveSibling(file.getFileName() + ".partial");
        Files.writeString(partial, DirectorScript.JSON.writerWithDefaultPrettyPrinter().writeValueAsString(value) + "\n",
                StandardCharsets.UTF_8);
        Files.move(partial, file, StandardCopyOption.REPLACE_EXISTING);
    }
}
