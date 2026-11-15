package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.util.Base64;
import java.util.List;

/** FastH3 Omni's typed Ref2VA HTTP contract; no persona or character registry is sent. */
final class FastH3VideoProvider {
    static final class ApiException extends IOException {
        final int statusCode;
        ApiException(int statusCode, String message) { super(message); this.statusCode = statusCode; }
    }
    private final URI base;
    private final HttpClient client;

    FastH3VideoProvider(URI base) {
        if (!List.of("http", "https").contains(base.getScheme()) || base.getHost() == null
                || base.getUserInfo() != null || base.getQuery() != null || base.getFragment() != null) {
            throw new IllegalArgumentException("Use an HTTP(S) API base without credentials, query or fragment");
        }
        this.base = URI.create(base.toString().replaceAll("/+$", "") + "/");
        client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(20)).build();
    }

    ObjectNode request(String prompt, int seconds, String size, long seed, List<Path> references) throws IOException {
        if (prompt.isBlank() || references.isEmpty() || references.size() > 9 || (seconds != 5 && seconds != 10)) {
            throw new IllegalArgumentException("Ref2VA requires a prompt, 1-9 images and a 5/10-second source clip");
        }
        ObjectNode request = DirectorScript.JSON.createObjectNode().put("model", "fasth3-omni")
                .put("task", "ref2va").put("prompt", prompt).put("seconds", String.valueOf(seconds))
                .put("size", size).put("seed", seed).put("fps", 24)
                .put("num_inference_steps", 8).put("guidance_scale", 1.0);
        var images = request.putArray("image_reference");
        for (Path reference : references) {
            String type = reference.toString().toLowerCase(java.util.Locale.ROOT).endsWith(".png") ? "image/png" : "image/jpeg";
            images.addObject().put("image_url", "data:" + type + ";base64,"
                    + Base64.getEncoder().encodeToString(Files.readAllBytes(reference)));
        }
        return request;
    }

    JsonNode submit(ObjectNode request) throws IOException, InterruptedException {
        return json(HttpRequest.newBuilder(base.resolve("videos")).timeout(Duration.ofSeconds(60))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(request.toString())).build());
    }

    JsonNode status(String id) throws IOException, InterruptedException {
        return json(HttpRequest.newBuilder(job(id)).timeout(Duration.ofSeconds(30)).GET().build());
    }

    void download(String id, Path destination) throws IOException, InterruptedException {
        var response = client.send(HttpRequest.newBuilder(URI.create(job(id) + "/content"))
                .timeout(Duration.ofMinutes(5)).GET().build(), HttpResponse.BodyHandlers.ofFile(destination,
                        StandardOpenOption.CREATE, StandardOpenOption.TRUNCATE_EXISTING, StandardOpenOption.WRITE));
        if (response.statusCode() != 200) {
            throw new IOException("Video download returned HTTP " + response.statusCode());
        }
    }

    private URI job(String id) {
        if (!id.matches("[a-zA-Z0-9_-]+")) { throw new IllegalArgumentException("Invalid video job ID"); }
        return base.resolve("videos/" + id);
    }

    private JsonNode json(HttpRequest request) throws IOException, InterruptedException {
        var response = client.send(request, HttpResponse.BodyHandlers.ofString());
        if (response.statusCode() < 200 || response.statusCode() >= 300) {
            throw new ApiException(response.statusCode(), "Video API returned HTTP " + response.statusCode() + ": "
                    + response.body().substring(0, Math.min(2000, response.body().length())));
        }
        return DirectorScript.JSON.readTree(response.body());
    }
}
