package com.xenoamess.vivhite_video_framework.maker;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.Set;

public final class DirectorScript {
    public static final ObjectMapper JSON = new ObjectMapper()
            .enable(com.fasterxml.jackson.core.JsonParser.Feature.STRICT_DUPLICATE_DETECTION);

    private DirectorScript() { }

    public static String fingerprint(Path path) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(path)));
    }

    public static void render(Path analysisFile, Path scriptFile, Path directory) throws Exception {
        JsonNode analysis = JSON.readTree(analysisFile.toFile());
        JsonNode script = JSON.readTree(scriptFile.toFile());
        validate(analysis, script, fingerprint(analysisFile));
        Files.createDirectories(directory);
        Files.writeString(directory.resolve("director.json"), JSON.writerWithDefaultPrettyPrinter()
                .writeValueAsString(script) + "\n", StandardCharsets.UTF_8);
        Files.writeString(directory.resolve("director.md"), markdown(script), StandardCharsets.UTF_8);
        ObjectNode validation = JSON.createObjectNode().put("schemaVersion", "1.0")
                .put("status", "passed").put("analysisSha256", fingerprint(analysisFile))
                .put("sceneCount", script.path("scenes").size()).put("durationMs", script.path("durationMs").asLong())
                .put("renderedVideo", false).put("contentStatus", "director_draft");
        Files.writeString(directory.resolve("director-validation.json"), validation.toPrettyString() + "\n", StandardCharsets.UTF_8);
        System.out.println("Director script: " + directory.resolve("director.md"));
    }

    public static void validate(JsonNode analysis, JsonNode script, String analysisHash) {
        if (!analysis.path("validationStatus").asText().equals("structural_and_evidence_coverage_passed")) {
            throw new IllegalArgumentException("Analysis must pass source and review coverage validation first");
        }
        if (!text(script, "analysisSha256").equals(analysisHash)) {
            throw new IllegalArgumentException("Director plan was created from different analysis results");
        }
        text(script, "title");
        text(script, "audience");
        text(script, "learningGoal");
        if (!script.path("scenes").isArray() || script.path("scenes").isEmpty()) {
            throw new IllegalArgumentException("Director plan has no scenes");
        }
        Set<String> validPoints = new HashSet<>();
        Set<String> validRules = new HashSet<>();
        Set<String> validSegments = new HashSet<>();
        for (JsonNode point : analysis.path("contentAnalysis").path("knowledgePoints")) {
            validPoints.add(text(point, "id"));
            point.path("sourceSegmentIds").forEach(item -> validSegments.add(item.asText()));
        }
        analysis.path("styleAnalysis").path("rules").forEach(rule -> validRules.add(text(rule, "id")));
        Set<String> usedPoints = new HashSet<>();
        Set<String> seenScenes = new HashSet<>();
        long previousEnd = 0;
        for (JsonNode scene : script.path("scenes")) {
            if (!seenScenes.add(text(scene, "id"))) {
                throw new IllegalArgumentException("Duplicate scene ID");
            }
            long start = scene.path("startMs").asLong(-1);
            long end = scene.path("endMs").asLong(-1);
            if (start != previousEnd || end <= start) {
                throw new IllegalArgumentException("Scene timeline must be contiguous, positive and start at zero");
            }
            previousEnd = end;
            String narration = text(scene, "narration");
            text(scene, "visualAction");
            text(scene, "animation");
            text(scene, "audioNotes");
            if (!scene.path("screenText").isArray()) {
                throw new IllegalArgumentException("screenText must be an array");
            }
            Set<String> points = references(scene, "knowledgePointIds", validPoints);
            usedPoints.addAll(points);
            if (references(scene, "styleRuleIds", validRules).isEmpty()) {
                throw new IllegalArgumentException("Scene has no applied style rule");
            }
            if (references(scene, "sourceSegmentIds", validSegments).isEmpty()) {
                throw new IllegalArgumentException("Scene narration has no content source reference");
            }
            long spokenCharacters = narration.codePoints().filter(Character::isLetterOrDigit).count();
            if (spokenCharacters * 1000.0 / (end - start) > 6.5) {
                throw new IllegalArgumentException("Narration is overbooked in scene " + scene.path("id").asText());
            }
        }
        if (previousEnd != script.path("durationMs").asLong() || !usedPoints.equals(validPoints)) {
            throw new IllegalArgumentException("Duration mismatch or content knowledge points omitted");
        }
    }

    private static Set<String> references(JsonNode scene, String field, Set<String> valid) {
        if (!scene.path(field).isArray()) {
            throw new IllegalArgumentException("Required reference array: " + field);
        }
        Set<String> values = new HashSet<>();
        for (JsonNode item : scene.path(field)) {
            if (!item.isTextual() || !valid.contains(item.asText())) {
                throw new IllegalArgumentException("Unknown " + field + " reference: " + item);
            }
            values.add(item.asText());
        }
        return values;
    }

    static String text(JsonNode node, String name) {
        if (!node.path(name).isTextual() || node.path(name).asText().isBlank()) {
            throw new IllegalArgumentException("Missing nonempty text: " + name);
        }
        return node.path(name).asText();
    }

    private static String time(long milliseconds) {
        return "%02d:%02d".formatted(milliseconds / 60000, milliseconds / 1000 % 60);
    }

    static String markdown(JsonNode script) {
        StringBuilder text = new StringBuilder("# " + script.path("title").asText() + "\n\n");
        text.append("受众：").append(script.path("audience").asText()).append("\n\n学习目标：")
                .append(script.path("learningGoal").asText()).append("\n\n计划时长：")
                .append(time(script.path("durationMs").asLong())).append("；阶段：导演稿。\n\n")
                .append("内容来源与风格来源见分析结果；以下旁白为重新组织的创作稿。\n\n");
        if (script.path("productionDesign").isObject()) {
            text.append("## 全片制作设定\n\n");
            script.path("productionDesign").properties().forEach(entry -> text.append("- ")
                    .append(entry.getKey()).append("：")
                    .append(entry.getValue().isTextual() ? entry.getValue().asText() : entry.getValue().toString())
                    .append("\n"));
            text.append("\n");
        }
        for (JsonNode scene : script.path("scenes")) {
            text.append("## ").append(scene.path("id").asText()).append(" · ")
                    .append(time(scene.path("startMs").asLong())).append("–")
                    .append(time(scene.path("endMs").asLong())).append("\n\n")
                    .append("**旁白**\n\n").append(scene.path("narration").asText()).append("\n\n")
                    .append("**画面与构图**\n\n").append(scene.path("visualAction").asText()).append("\n\n")
                    .append("**屏幕文字**\n\n");
            scene.path("screenText").forEach(item -> text.append("- ").append(item.asText()).append("\n"));
            text.append("\n**动画与操作顺序**\n\n").append(scene.path("animation").asText())
                    .append("\n\n**声音、停顿与节奏**\n\n").append(scene.path("audioNotes").asText())
                    .append("\n\n知识点：").append(scene.path("knowledgePointIds"))
                    .append("；风格规则：").append(scene.path("styleRuleIds"))
                    .append("；内容来源语音段：").append(scene.path("sourceSegmentIds")).append("\n\n");
        }
        return text.toString().stripTrailing() + "\n";
    }
}
