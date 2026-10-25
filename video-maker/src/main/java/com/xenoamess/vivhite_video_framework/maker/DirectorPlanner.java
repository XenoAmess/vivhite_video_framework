package com.xenoamess.vivhite_video_framework.maker;

import static com.xenoamess.vivhite_video_framework.maker.DirectorScript.JSON;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

final class DirectorPlanner {
    private DirectorPlanner() { }

    static void prepare(Path analysisFile, Path directory) throws Exception {
        JsonNode analysis = JSON.readTree(analysisFile.toFile());
        if (!analysis.path("validationStatus").asText().equals("structural_and_evidence_coverage_passed")) {
            throw new IllegalArgumentException("Import and validate content/style review before director planning");
        }
        Files.createDirectories(directory);
        String hash = DirectorScript.fingerprint(analysisFile);
        String prompt = "你是一名数学科普视频导演。用 contentAnalysis 的知识内容重新组织原创完整旁白，"
                + "纠正已发现的数学表述问题，再应用 styleAnalysis 中有证据的表达方法。"
                + "风格来源仅提供表达方式，不能混入其独立主题。旁白不是摘要，要能直接配音。"
                + "为每个镜头给出完整旁白、构图、屏幕文字、操作顺序、声音和停顿。"
                + "所有知识点都要覆盖，逐镜头引用 knowledgePointIds、styleRuleIds 与 sourceSegmentIds。"
                + "合理规划约 10–15 分钟的讲解，镜头从零连续计时，不留时间空洞，"
                + "旁白通常每秒 3–5 个中文字符并留出操作与思考时间。不要宣称已生成动画。"
                + "保留正确前提、定义、必要的证明和反例；不确定内容明确处理。"
                + "只返回符合所提供 schema 的 JSON，analysisSha256 必须为 " + hash + "。";
        ObjectNode context = JSON.createObjectNode();
        for (String field : new String[]{"contentAnalysis", "styleAnalysis", "adaptationNotes", "provenance", "coverage"}) {
            if (analysis.has(field)) {
                context.set(field, analysis.path(field));
            }
        }
        context.put("analysisSha256", hash);
        ObjectNode request = JSON.createObjectNode().put("model", System.getenv().getOrDefault("OPENAI_MODEL", "SET_OPENAI_MODEL"))
                .put("store", false).put("instructions", prompt).put("max_output_tokens", 24000);
        request.putArray("input").addObject().put("role", "user").put("content", context.toString());
        request.putObject("text").putObject("format").put("type", "json_schema").put("name", "director_script")
                .put("strict", true).set("schema", schema());
        Files.writeString(directory.resolve("director-request.json"), request.toPrettyString() + "\n", StandardCharsets.UTF_8);
        Files.writeString(directory.resolve("director-prompt.md"), "# 导演稿生成任务\n\n" + prompt
                + "\n\n## 输入分析\n\n```json\n" + context.toPrettyString() + "\n```\n", StandardCharsets.UTF_8);
    }

    static void generate(Path analysisFile, Path directory) throws Exception {
        String key = System.getenv("OPENAI_API_KEY");
        String model = System.getenv("OPENAI_MODEL");
        if (key == null || key.isBlank() || model == null || model.isBlank()) {
            throw new IllegalArgumentException("Set OPENAI_API_KEY and OPENAI_MODEL locally, or prepare and import an assisted director plan");
        }
        prepare(analysisFile, directory);
        String base = System.getenv().getOrDefault("OPENAI_BASE_URL", "https://api.openai.com/v1");
        HttpRequest request = HttpRequest.newBuilder(URI.create(base.replaceAll("/+$", "") + "/responses"))
                .timeout(Duration.ofMinutes(5)).header("Authorization", "Bearer " + key)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(Files.readString(directory.resolve("director-request.json")))).build();
        HttpResponse<String> response = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(30)).build()
                .send(request, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
        if (response.statusCode() / 100 != 2) {
            throw new IOException("Director model HTTP " + response.statusCode());
        }
        JsonNode body = JSON.readTree(response.body());
        if (!body.path("status").asText().equals("completed")) {
            throw new IOException("Director response incomplete; no validated script was generated");
        }
        StringBuilder text = new StringBuilder();
        for (JsonNode output : body.path("output")) {
            for (JsonNode content : output.path("content")) {
                if (content.path("type").asText().equals("refusal")) {
                    throw new IOException("Director request refused");
                }
                if (content.path("type").asText().equals("output_text")) {
                    text.append(content.path("text").asText());
                }
            }
        }
        JsonNode script = JSON.readTree(text.toString());
        DirectorScript.validate(JSON.readTree(analysisFile.toFile()), script, DirectorScript.fingerprint(analysisFile));
        Files.writeString(directory.resolve("director-response.json"), body.toPrettyString() + "\n", StandardCharsets.UTF_8);
        Path scriptFile = directory.resolve("director-plan.json");
        Files.writeString(scriptFile, script.toPrettyString() + "\n", StandardCharsets.UTF_8);
        DirectorScript.render(analysisFile, scriptFile, directory);
    }

    private static JsonNode schema() throws IOException {
        return JSON.readTree("""
                {"type":"object","additionalProperties":false,
                 "required":["title","audience","learningGoal","durationMs","analysisSha256","scenes"],
                 "properties":{"title":{"type":"string"},"audience":{"type":"string"},"learningGoal":{"type":"string"},
                  "durationMs":{"type":"integer"},"analysisSha256":{"type":"string"},
                  "scenes":{"type":"array","items":{"type":"object","additionalProperties":false,
                   "required":["id","startMs","endMs","narration","visualAction","screenText","animation","audioNotes",
                               "knowledgePointIds","styleRuleIds","sourceSegmentIds"],
                   "properties":{"id":{"type":"string"},"startMs":{"type":"integer"},"endMs":{"type":"integer"},
                    "narration":{"type":"string"},"visualAction":{"type":"string"},"animation":{"type":"string"},
                    "audioNotes":{"type":"string"},"screenText":{"type":"array","items":{"type":"string"}},
                    "knowledgePointIds":{"type":"array","items":{"type":"string"}},
                    "styleRuleIds":{"type":"array","items":{"type":"string"}},
                    "sourceSegmentIds":{"type":"array","items":{"type":"string"}}}}}}}
                """);
    }
}
