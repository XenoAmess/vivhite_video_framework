package com.xenoamess.vivhite_video_framework.maker;

import static com.xenoamess.vivhite_video_framework.maker.DirectorScript.JSON;
import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.node.ObjectNode;
import org.junit.jupiter.api.Test;

class DirectorScriptTest {
    private ObjectNode analysis() throws Exception {
        return (ObjectNode) JSON.readTree("""
                {"validationStatus":"structural_and_evidence_coverage_passed",
                 "contentAnalysis":{"knowledgePoints":[{"id":"K1","sourceSegmentIds":["c1"]}]},
                 "styleAnalysis":{"rules":[{"id":"S1"}]}}
                """);
    }

    private ObjectNode script() throws Exception {
        return (ObjectNode) JSON.readTree("""
                {"analysisSha256":"hash","title":"test","audience":"general","learningGoal":"parity","durationMs":10000,
                 "scenes":[{"id":"01","startMs":0,"endMs":10000,"narration":"Count inversions.","visualAction":"board",
                  "animation":"slide","audioNotes":"pause","screenText":["parity"],"knowledgePointIds":["K1"],
                  "styleRuleIds":["S1"],"sourceSegmentIds":["c1"]}]}
                """);
    }

    @Test
    void rejectsBrokenTimelinesOmittedContentAndUnknownEvidence() throws Exception {
        DirectorScript.validate(analysis(), script(), "hash");
        ObjectNode gap = script();
        ((ObjectNode) gap.at("/scenes/0")).put("startMs", 1);
        assertThrows(IllegalArgumentException.class, () -> DirectorScript.validate(analysis(), gap, "hash"));
        ObjectNode omission = script();
        ((ObjectNode) omission.at("/scenes/0")).withArray("knowledgePointIds").removeAll();
        assertThrows(IllegalArgumentException.class, () -> DirectorScript.validate(analysis(), omission, "hash"));
        ObjectNode evidence = script();
        ((ObjectNode) evidence.at("/scenes/0")).putArray("sourceSegmentIds").add("invented");
        assertThrows(IllegalArgumentException.class, () -> DirectorScript.validate(analysis(), evidence, "hash"));
        assertThrows(IllegalArgumentException.class, () -> DirectorScript.validate(analysis(), script(), "changed"));
    }

    @Test
    void rejectsImpossibleNarrationTiming() throws Exception {
        ObjectNode crowded = script();
        ((ObjectNode) crowded.at("/scenes/0")).put("endMs", 100);
        crowded.put("durationMs", 100);
        assertThrows(IllegalArgumentException.class, () -> DirectorScript.validate(analysis(), crowded, "hash"));
    }

    @Test
    void preparedApiSchemaIsValidJson(@org.junit.jupiter.api.io.TempDir java.nio.file.Path directory) throws Exception {
        var input = directory.resolve("analysis.json");
        JSON.writeValue(input.toFile(), analysis());
        DirectorPlanner.prepare(input, directory);
        assertEquals("object", JSON.readTree(directory.resolve("director-request.json").toFile())
                .at("/text/format/schema/type").asText());
    }
}
