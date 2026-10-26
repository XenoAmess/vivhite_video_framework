package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.Set;

public final class ProductionPlan {
    static final Set<String> VIEWS = Set.of("board", "wires", "swap", "parity", "cycle", "search", "route", "credits");
    private ProductionPlan() { }

    static JsonNode load(Path path) throws Exception {
        JsonNode plan = DirectorScript.JSON.readTree(path.toFile());
        validate(plan);
        return plan;
    }

    public static void validate(JsonNode plan) {
        require(plan.path("schemaVersion").asText().equals("vivhite-production-1"), "Unsupported production schema");
        text(plan, "title");
        int width = plan.path("width").asInt();
        int height = plan.path("height").asInt();
        int fps = plan.path("fps").asInt();
        require(width >= 640 && width <= 3840 && width % 2 == 0 && height >= 360 && height <= 2160 && height % 2 == 0
                && width * 9 == height * 16 && (fps == 24 || fps == 25 || fps == 30 || fps == 60), "Invalid 16:9 production geometry");
        require(plan.path("voice").path("provider").asText().equals("edge-tts"), "This worker currently supports edge-tts");
        text(plan.path("voice"), "name");
        require(plan.path("voice").path("rate").asText().matches("[+-]\\d{1,2}%"), "Invalid TTS rate");
        require(plan.path("beats").isArray() && !plan.path("beats").isEmpty(), "Production needs beats");
        var ids = new HashSet<String>();
        for (JsonNode beat : plan.path("beats")) {
            String id = text(beat, "id");
            require(id.matches("[A-Za-z0-9_-]{1,64}") && ids.add(id), "Unsafe or duplicate beat ID");
            text(beat, "chapter");
            text(beat, "heading");
            String narration = text(beat, "narration");
            require(narration.length() <= 600, "Split long narration into action beats");
            require(VIEWS.contains(text(beat, "view")), "Unsupported view");
            require(beat.path("action").isTextual() && !beat.path("action").asText().isBlank(), "Missing action direction");
            int columns = beat.path("columns").asInt(3);
            JsonNode states = beat.path("states");
            if (!beat.path("view").asText().equals("credits")) {
                require(states.isArray() && !states.isEmpty(), "Visual beat needs states");
                int[] previous = null;
                for (JsonNode state : states) {
                    int[] values = ints(state);
                    PuzzleMath.validate(values, columns);
                    if (previous != null) {
                        if (beat.path("view").asText().equals("swap")) {
                            int differences = 0;
                            for (int i = 0; i < values.length; i++) { if (previous[i] != values[i]) { differences++; } }
                            require(previous.length == values.length && differences == 2, "Expected a single transposition in " + id);
                        } else {
                            require(PuzzleMath.legalMove(previous, values, columns), "Illegal slide in " + id);
                        }
                    }
                    previous = values;
                }
            }
            if (beat.has("goal")) { PuzzleMath.validate(ints(beat.get("goal")), columns); }
            if (beat.has("moveCues")) {
                require(beat.path("moveCues").isArray() && beat.path("moveCues").size() == states.size() - 1, "Action cue count mismatch");
                for (JsonNode cue : beat.path("moveCues")) {
                    require(narration.contains(text(cue, "phrase")), "Action phrase is absent from narration");
                }
            }
        }
    }

    static int[] ints(JsonNode node) {
        require(node.isArray(), "State must be an array");
        int[] result = new int[node.size()];
        for (int i = 0; i < result.length; i++) {
            require(node.get(i).isIntegralNumber(), "State labels must be integers");
            result[i] = node.get(i).asInt();
        }
        return result;
    }

    static String text(JsonNode node, String field) {
        String value = node.path(field).asText("");
        require(!value.isBlank(), "Missing " + field);
        return value;
    }

    static void require(boolean valid, String message) {
        if (!valid) { throw new IllegalArgumentException(message); }
    }
}
