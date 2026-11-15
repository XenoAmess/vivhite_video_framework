package com.xenoamess.vivhite_video_framework.maker;

import static org.junit.jupiter.api.Assertions.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ReferenceVideoProductionTest {
    @TempDir Path directory;

    @Test void typedReferencesReachTheApiAndFailureIsPreserved() throws Exception {
        Path png = directory.resolve("reference.png");
        Files.write(png, new byte[]{1, 2, 3});
        AtomicReference<JsonNode> received = new AtomicReference<>();
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        server.createContext("/v1/videos", exchange -> {
            received.set(DirectorScript.JSON.readTree(exchange.getRequestBody()));
            byte[] body = "{\"id\":\"video-test\",\"status\":\"queued\"}".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (var output = exchange.getResponseBody()) { output.write(body); }
        });
        server.createContext("/v1/videos/video-test", exchange -> {
            byte[] body = "{\"id\":\"video-test\",\"status\":\"failed\",\"error\":{\"message\":\"sampler mismatch\"}}"
                    .getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, body.length);
            try (var output = exchange.getResponseBody()) { output.write(body); }
        });
        server.createContext("/v1/videos/video-test/content", exchange -> {
            byte[] body = new byte[]{4, 5};
            exchange.sendResponseHeaders(200, body.length);
            try (var output = exchange.getResponseBody()) { output.write(body); }
        });
        server.start();
        try {
            var provider = new FastH3VideoProvider(URI.create("http://127.0.0.1:" + server.getAddress().getPort() + "/v1"));
            JsonNode result = provider.submit(provider.request("A quiet landscape", 5, "1344x768", 42, List.of(png)));
            assertEquals("video-test", result.path("id").asText());
            assertEquals("ref2va", received.get().path("task").asText());
            assertFalse(received.get().has("input_reference"));
            assertEquals("data:image/png;base64,AQID", received.get().path("image_reference").get(0).path("image_url").asText());
            assertEquals(8, received.get().path("num_inference_steps").asInt());
            assertEquals("sampler mismatch", provider.status("video-test").path("error").path("message").asText());
            Path partial = directory.resolve("partial.mp4");
            Files.write(partial, new byte[]{9, 9, 9, 9, 9});
            provider.download("video-test", partial);
            assertArrayEquals(new byte[]{4, 5}, Files.readAllBytes(partial));
            assertThrows(IllegalArgumentException.class, () -> provider.status("../other"));
        } finally { server.stop(0); }
    }

    @Test void timingAndReferenceBoundariesAreEnforced() throws Exception {
        Files.write(directory.resolve("reference.png"), new byte[]{1});
        Path file = directory.resolve("plan.json");
        ObjectNode plan = DirectorScript.JSON.createObjectNode().put("schemaVersion", "vivhite-reference-video-1")
                .put("width", 1920).put("height", 1080).put("fps", 30).put("noSpeech", true)
                .put("noHumanFaces", true).put("allCharactersFemale", true)
                .put("costumeStyle", "Feminine white, purple and gold costume").put("totalFrames", 60);
        var shot = plan.putArray("shots").addObject().put("id", "S01").put("seconds", 2)
                .put("sourceSeconds", 5).put("startFrame", 0).put("prompt", "Only a hand, no face");
        shot.putArray("references").add("reference.png");
        Files.writeString(file, plan.toString());
        assertEquals(60, ReferenceVideoProduction.load(file).path("totalFrames").asInt());
        plan.put("allCharactersFemale", false);
        Files.writeString(file, plan.toString());
        assertThrows(IOException.class, () -> ReferenceVideoProduction.load(file));
        plan.put("allCharactersFemale", true);
        shot.put("seconds", 11);
        Files.writeString(file, plan.toString());
        assertThrows(IOException.class, () -> ReferenceVideoProduction.load(file));
        shot.put("seconds", 2).put("startFrame", 1);
        Files.writeString(file, plan.toString());
        assertThrows(IOException.class, () -> ReferenceVideoProduction.load(file));
        shot.put("startFrame", 0).putArray("references").add("../outside.png");
        Files.writeString(file, plan.toString());
        assertThrows(IOException.class, () -> ReferenceVideoProduction.load(file));
    }
}
