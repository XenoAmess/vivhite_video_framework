package com.xenoamess.vivhite_video_framework.analyzer;

import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.JSON;
import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.Map;
import org.junit.jupiter.api.Test;

class ReviewServiceTest {
    private ObjectNode workspace() throws Exception {
        return (ObjectNode) JSON.readTree("""
                {"caseId":"test","sources":{"content":{"sha256":"c"},"style":{"sha256":"s"}}}
                """);
    }

    private Map<String, com.fasterxml.jackson.databind.JsonNode> packets() throws Exception {
        return Map.of("content-w0001", JSON.readTree("""
                {"id":"content-w0001","role":"content","units":[{"id":"c1"}],"frames":[{"id":"cf"}]}
                """), "style-w0001", JSON.readTree("""
                {"id":"style-w0001","role":"style","units":[{"id":"s1"}],"frames":[{"id":"sf"}]}
                """));
    }

    private ObjectNode review() throws Exception {
        return (ObjectNode) JSON.readTree("""
                {"caseId":"test","provenance":{"mode":"assisted","reviewer":"test"},
                 "sourceHashes":{"content":"c","style":"s"},"windowReviews":[
                 {"windowId":"content-w0001","summary":"content","unitReviews":[{"segmentId":"c1","meaning":"claim","issues":[]}],
                  "visualFindings":[{"frameId":"cf","observation":"board"}]},
                 {"windowId":"style-w0001","summary":"style","unitReviews":[{"segmentId":"s1","meaning":"style","issues":[]}],
                  "visualFindings":[{"frameId":"sf","observation":"color"}]}],
                 "contentAnalysis":{"title":"puzzle","thesis":"invariant","knowledgePoints":[
                  {"id":"K1","title":"parity","explanation":"invariant","sourceSegmentIds":["c1"]}]},
                 "styleAnalysis":{"rules":[{"id":"S1","dimension":"color","observation":"cream","reuseInstruction":"apply",
                  "evidenceWindowIds":["style-w0001"],"evidenceFrameIds":["sf"]}]}}
                """);
    }

    @Test
    void acceptsFullReviewButRejectsOmissionsWrongSourcesAndCrossRoleEvidence() throws Exception {
        ReviewService.validate(workspace(), packets(), review());
        ObjectNode missingWindow = review();
        missingWindow.withArray("windowReviews").remove(1);
        assertThrows(IllegalArgumentException.class, () -> ReviewService.validate(workspace(), packets(), missingWindow));
        ObjectNode missingSentence = review();
        ((ObjectNode) missingSentence.path("windowReviews").get(0)).withArray("unitReviews").removeAll();
        assertThrows(IllegalArgumentException.class, () -> ReviewService.validate(workspace(), packets(), missingSentence));
        ObjectNode wrongSource = review();
        ((ObjectNode) wrongSource.path("sourceHashes")).put("content", "changed");
        assertThrows(IllegalArgumentException.class, () -> ReviewService.validate(workspace(), packets(), wrongSource));
        ObjectNode crossRole = review();
        ((ObjectNode) crossRole.at("/contentAnalysis/knowledgePoints/0")).putArray("sourceSegmentIds").add("s1");
        assertThrows(IllegalArgumentException.class, () -> ReviewService.validate(workspace(), packets(), crossRole));
    }

    @Test
    void rejectsIncompleteRefusedAndNonObjectModelResponses() throws Exception {
        assertThrows(java.io.IOException.class, () -> OpenAiReviewer.parseResponse(JSON.readTree("{\"status\":\"incomplete\"}")));
        assertThrows(java.io.IOException.class, () -> OpenAiReviewer.parseResponse(JSON.readTree("""
                {"status":"completed","output":[{"content":[{"type":"refusal"}]}]}
                """)));
        assertThrows(java.io.IOException.class, () -> OpenAiReviewer.parseResponse(JSON.readTree("""
                {"status":"completed","output":[{"content":[{"type":"output_text","text":"null"}]}]}
                """)));
        assertEquals(1, OpenAiReviewer.parseResponse(JSON.readTree("""
                {"status":"completed","output":[{"content":[{"type":"output_text","text":"{\\"x\\":1}"}]}]}
                """)).path("x").asInt());
    }

    @Test
    void detectsDecodeGapsInsteadOfDeclaringFullCoverage() throws Exception {
        var transcript = JSON.readTree("""
                {"durationMs":1000,"segments":[{"id":"c1","startMs":0,"endMs":1000}]}
                """);
        ObjectNode vision = (ObjectNode) JSON.readTree("""
                {"decodedEndMs":1000,"decodedFrames":30,"decodeGaps":[],"nonMonotonicPts":[]}
                """);
        AnalysisPipeline.validateMediaCoverage(transcript, vision, 1000);
        vision.withArray("decodeGaps").addObject().put("startMs", 100).put("endMs", 500);
        assertThrows(IllegalArgumentException.class, () -> AnalysisPipeline.validateMediaCoverage(transcript, vision, 1000));
    }
}
