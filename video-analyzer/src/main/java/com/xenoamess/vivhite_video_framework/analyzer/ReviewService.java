package com.xenoamess.vivhite_video_framework.analyzer;

import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.JSON;
import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.requiredText;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

public final class ReviewService {
    private ReviewService() { }

    public static void importReview(Path directory, Path reviewFile) throws Exception {
        JsonNode workspace = JsonFiles.read(directory.resolve("workspace.json"));
        JsonNode review = JsonFiles.read(reviewFile);
        Map<String, JsonNode> packets = new HashMap<>();
        for (JsonNode entry : workspace.path("packets")) {
            packets.put(entry.path("id").asText(), JsonFiles.read(directory.resolve(entry.path("path").asText())));
        }
        validate(workspace, packets, review);
        ObjectNode report = review.deepCopy();
        report.put("validationStatus", "structural_and_evidence_coverage_passed");
        report.put("factualCorrectnessGuarantee", false);
        report.set("sources", workspace.path("sources"));
        ObjectNode coverage = report.putObject("coverage");
        coverage.put("expectedWindows", packets.size());
        coverage.put("reviewedWindows", review.path("windowReviews").size());
        coverage.put("manualFullPlayback", false);
        coverage.put("secondaryAsr", "not_run");
        coverage.put("ocrCompleteness", "not_certified");
        coverage.put("semanticVisualInput", "selected_frames_across_all_windows");
        ObjectNode measurements = coverage.putObject("sourceMeasurements");
        for (String role : new String[]{"content", "style"}) {
            JsonNode source = workspace.path("sources").path(role);
            ObjectNode measured = measurements.putObject(role);
            for (String field : new String[]{"durationMs", "transcriptSegments", "decodedFrames", "selectedFrames", "ocrObservations", "asrQuality", "ocrCompleteness"}) {
                measured.set(field, source.path(field));
            }
        }
        JsonFiles.write(directory.resolve("analysis-report.json"), report);
        JsonFiles.writeText(directory.resolve("analysis-report.md"), render(report));
        ObjectNode updatedWorkspace = workspace.deepCopy();
        updatedWorkspace.put("semanticReviewStatus", review.path("provenance").path("semanticReviewStatus")
                .asText(review.path("provenance").path("mode").asText() + "_reviewed"));
        updatedWorkspace.put("analysisReport", "analysis-report.json");
        JsonFiles.write(directory.resolve("workspace.json"), updatedWorkspace);
        System.out.println("Validated analysis report: " + directory.resolve("analysis-report.md"));
    }

    public static void validate(JsonNode workspace, Map<String, JsonNode> packets, JsonNode review) {
        if (!requiredText(review, "caseId").equals(requiredText(workspace, "caseId"))) {
            throw new IllegalArgumentException("Review belongs to a different case");
        }
        if (!Set.of("assisted", "openai").contains(requiredText(review.path("provenance"), "mode"))) {
            throw new IllegalArgumentException("Review provenance mode must be assisted or openai");
        }
        requiredText(review.path("provenance"), "reviewer");
        for (String role : Set.of("content", "style")) {
            if (!requiredText(review.path("sourceHashes"), role)
                    .equals(workspace.path("sources").path(role).path("sha256").asText())) {
                throw new IllegalArgumentException("Review source fingerprint mismatch: " + role);
            }
        }
        Set<String> seen = new HashSet<>();
        Set<String> contentUnits = new HashSet<>();
        Set<String> styleWindows = new HashSet<>();
        Set<String> styleFrames = new HashSet<>();
        requireArray(review, "windowReviews");
        for (JsonNode window : review.path("windowReviews")) {
            String id = requiredText(window, "windowId");
            if (!seen.add(id) || !packets.containsKey(id)) {
                throw new IllegalArgumentException("Duplicate or unknown review window: " + id);
            }
            JsonNode packet = packets.get(id);
            validateWindow(packet, window);
            if (packet.path("role").asText().equals("content")) {
                packet.path("units").forEach(unit -> contentUnits.add(unit.path("id").asText()));
            } else {
                styleWindows.add(id);
                packet.path("frames").forEach(frame -> styleFrames.add(frame.path("id").asText()));
            }
        }
        if (!seen.equals(packets.keySet())) {
            Set<String> missing = new HashSet<>(packets.keySet());
            missing.removeAll(seen);
            throw new IllegalArgumentException("Unreviewed windows: " + missing);
        }
        JsonNode content = review.path("contentAnalysis");
        requiredText(content, "title");
        requiredText(content, "thesis");
        requireArray(content, "knowledgePoints");
        Set<String> pointIds = new HashSet<>();
        for (JsonNode point : content.path("knowledgePoints")) {
            if (!pointIds.add(requiredText(point, "id"))) {
                throw new IllegalArgumentException("Duplicate knowledge point");
            }
            requiredText(point, "title");
            requiredText(point, "explanation");
            requireReferences(point, "sourceSegmentIds", contentUnits);
        }
        if (pointIds.isEmpty()) {
            throw new IllegalArgumentException("No content knowledge points");
        }
        Set<String> ruleIds = new HashSet<>();
        requireArray(review.path("styleAnalysis"), "rules");
        for (JsonNode rule : review.path("styleAnalysis").path("rules")) {
            if (!ruleIds.add(requiredText(rule, "id"))) {
                throw new IllegalArgumentException("Duplicate style rule");
            }
            requiredText(rule, "dimension");
            requiredText(rule, "observation");
            requiredText(rule, "reuseInstruction");
            requireReferences(rule, "evidenceWindowIds", styleWindows);
            requireReferences(rule, "evidenceFrameIds", styleFrames);
        }
        if (ruleIds.isEmpty()) {
            throw new IllegalArgumentException("No evidenced style rules");
        }
    }

    static void validateWindow(JsonNode packet, JsonNode review) {
        if (!requiredText(review, "windowId").equals(requiredText(packet, "id"))) {
            throw new IllegalArgumentException("Review window ID mismatch");
        }
        requiredText(review, "summary");
        Set<String> expected = new HashSet<>();
        packet.path("units").forEach(unit -> expected.add(unit.path("id").asText()));
        Set<String> actual = new HashSet<>();
        requireArray(review, "unitReviews");
        for (JsonNode unit : review.path("unitReviews")) {
            if (!actual.add(requiredText(unit, "segmentId"))) {
                throw new IllegalArgumentException("Duplicate unit review");
            }
            requiredText(unit, "meaning");
            requireArray(unit, "issues");
        }
        if (!actual.equals(expected)) {
            throw new IllegalArgumentException("Sentence coverage mismatch in " + packet.path("id"));
        }
        Set<String> frameIds = new HashSet<>();
        packet.path("frames").forEach(frame -> frameIds.add(frame.path("id").asText()));
        requireArray(review, "visualFindings");
        for (JsonNode finding : review.path("visualFindings")) {
            if (!frameIds.contains(requiredText(finding, "frameId"))) {
                throw new IllegalArgumentException("Visual finding cites an unavailable frame");
            }
            requiredText(finding, "observation");
        }
        if (!frameIds.isEmpty() && review.path("visualFindings").isEmpty()) {
            throw new IllegalArgumentException("No visual review for " + packet.path("id"));
        }
    }

    private static void requireReferences(JsonNode parent, String name, Set<String> valid) {
        requireArray(parent, name);
        if (parent.path(name).isEmpty()) {
            throw new IllegalArgumentException("Empty evidence references: " + name);
        }
        for (JsonNode reference : parent.path(name)) {
            if (!reference.isTextual() || !valid.contains(reference.asText())) {
                throw new IllegalArgumentException("Unknown evidence reference: " + reference);
            }
        }
    }

    private static void requireArray(JsonNode parent, String name) {
        if (!parent.path(name).isArray()) {
            throw new IllegalArgumentException("Required array: " + name);
        }
    }

    private static String render(JsonNode report) {
        StringBuilder text = new StringBuilder("# 内容与风格分析\n\n");
        text.append("案例：").append(report.path("caseId").asText()).append("\n\n");
        text.append("审查方式：").append(report.path("provenance").path("mode").asText())
                .append("；审查者：").append(report.path("provenance").path("reviewer").asText()).append("\n\n");
        text.append("## 内容来源：").append(report.path("contentAnalysis").path("title").asText()).append("\n\n")
                .append(report.path("contentAnalysis").path("thesis").asText()).append("\n\n");
        for (JsonNode point : report.path("contentAnalysis").path("knowledgePoints")) {
            text.append("### ").append(point.path("id").asText()).append(" ")
                    .append(point.path("title").asText()).append("\n\n")
                    .append(point.path("explanation").asText()).append("\n\n来源语音段：")
                    .append(point.path("sourceSegmentIds")).append("\n\n");
        }
        text.append("## 风格来源与改编方法\n\n");
        for (JsonNode rule : report.path("styleAnalysis").path("rules")) {
            text.append("### ").append(rule.path("id").asText()).append(" ")
                    .append(rule.path("dimension").asText()).append("\n\n观察：")
                    .append(rule.path("observation").asText()).append("\n\n应用：")
                    .append(rule.path("reuseInstruction").asText()).append("\n\n依据：")
                    .append(rule.path("evidenceWindowIds")).append(" / ")
                    .append(rule.path("evidenceFrameIds")).append("\n\n");
        }
        text.append("## 全部窗口审查记录\n\n");
        if (report.path("adaptationNotes").isArray()) {
            text.append("改编与校正：\n\n");
            report.path("adaptationNotes").forEach(note -> text.append("- ").append(note.asText()).append("\n"));
            text.append("\n");
        }
        for (JsonNode window : report.path("windowReviews")) {
            text.append("### ").append(window.path("windowId").asText()).append("\n\n")
                    .append(window.path("summary").asText()).append("\n\n");
            for (JsonNode unit : window.path("unitReviews")) {
                text.append("- ").append(unit.path("segmentId").asText()).append("：")
                        .append(unit.path("meaning").asText());
                if (!unit.path("issues").isEmpty()) {
                    text.append("；待核对：").append(unit.path("issues"));
                }
                text.append("\n");
            }
            text.append("\n");
            for (JsonNode finding : window.path("visualFindings")) {
                text.append("- 画面 ").append(finding.path("frameId").asText()).append("：")
                        .append(finding.path("observation").asText()).append("\n");
            }
            text.append("\n");
        }
        text.append("## 质量与范围\n\n").append(report.path("coverage").toPrettyString())
                .append("\n\n结构和引用校验通过不代表事实无误；机器识别和选帧语义分析保留各自局限。\n");
        if (report.path("provenance").path("limitations").isArray()) {
            text.append("\n");
            report.path("provenance").path("limitations").forEach(item ->
                    text.append("- ").append(item.asText()).append("\n"));
        }
        return text.toString();
    }
}
