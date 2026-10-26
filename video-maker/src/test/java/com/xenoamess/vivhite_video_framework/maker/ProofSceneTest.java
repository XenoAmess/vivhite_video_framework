package com.xenoamess.vivhite_video_framework.maker;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.nio.file.Path;
import java.util.Map;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

class ProofSceneTest {
    @TempDir Path directory;

    private static ObjectNode square() throws Exception {
        return (ObjectNode) DirectorScript.JSON.readTree("""
                {"mode":"graph","nodes":[{"id":"a","label":"a","x":0,"y":0},
                 {"id":"b","label":"b","x":1,"y":0},{"id":"c","label":"c","x":1,"y":1},
                 {"id":"d","label":"d","x":0,"y":1}],
                 "edges":[["a","b"],["b","c"],["c","d"],["d","a"]],"root":"a","blank":"a",
                 "initialTokens":{"a":"0","b":"1","c":"2","d":"3"},
                 "steps":[{"text":"Around the square","walk":["a","b","c","d","a"]}]}
                """);
    }

    @Test
    void legalClosedWalkReallyCyclesThreeTilesAndReturnsTheBlank() throws Exception {
        ProofScene scene = ProofScene.parse(square(), "Around the square");
        assertEquals(Map.of("a", "0", "b", "2", "c", "3", "d", "1"), scene.finalTokens());
        assertEquals(5, scene.steps.getFirst().states().size());
        for (int i = 1; i < scene.steps.getFirst().states().size(); i++) {
            int differences = 0;
            int[] before = scene.steps.getFirst().states().get(i - 1);
            int[] after = scene.steps.getFirst().states().get(i);
            for (int j = 0; j < before.length; j++) { if (before[j] != after[j]) { differences++; } }
            assertEquals(2, differences);
        }
    }

    @Test
    void rejectTeleportAndWalkThatDoesNotContinueFromTheBlank() throws Exception {
        ObjectNode proof = square();
        ObjectNode step = (ObjectNode) proof.path("steps").get(0);
        step.set("walk", DirectorScript.JSON.readTree("[\"a\",\"c\"]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
        step.set("walk", DirectorScript.JSON.readTree("[\"b\",\"c\"]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
    }

    @Test
    void incrementalEarCreatesTheEdgeBeforeItsLegalSlide() throws Exception {
        ObjectNode proof = square();
        ((ObjectNode) proof.path("steps").get(0)).set("walk", DirectorScript.JSON.readTree("[\"a\",\"b\"]"));
        ((com.fasterxml.jackson.databind.node.ArrayNode) proof.path("steps")).addObject()
                .set("addEdges", DirectorScript.JSON.readTree("[[\"b\",\"d\"]]"));
        ((ObjectNode) proof.path("steps").get(1)).set("walk", DirectorScript.JSON.readTree("[\"b\",\"d\"]"));
        assertEquals(Map.of("a", "1", "b", "3", "c", "2", "d", "0"), ProofScene.parse(proof, "test").finalTokens());
    }

    @Test
    void cyclesArePositionPermutationsWithExplicitSequentialComposition() throws Exception {
        ObjectNode proof = square();
        proof.put("mode", "permutation");
        proof.set("steps", DirectorScript.JSON.readTree("""
                [{"cycles":[["b","c","d"]]},{"cycles":[["b","d"]]}]
                """));
        ProofScene scene = ProofScene.parse(proof, "test");
        assertEquals(Map.of("a", "0", "b", "2", "c", "1", "d", "3"), scene.finalTokens());
        assertTrue(scene.hasAlgebra);
        proof.set("steps", DirectorScript.JSON.readTree("[{\"cycles\":[[\"a\",\"b\"],[\"b\",\"c\"]]}]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
    }

    @Test
    void rejectUnknownNodesOutOfBoundsCoordinatesAndDuplicateBlank() throws Exception {
        ObjectNode proof = square();
        ((ObjectNode) proof.path("nodes").get(0)).put("x", 1.01);
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
        ((ObjectNode) proof.path("nodes").get(0)).put("x", 0);
        ((ObjectNode) proof.path("initialTokens")).put("b", "0");
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
        ((ObjectNode) proof.path("initialTokens")).put("b", "1");
        ((ObjectNode) proof.path("steps").get(0)).set("focus", DirectorScript.JSON.readTree("[\"unknown\"]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
    }

    @Test
    void tablesRejectOverflowUnknownHighlightAndNonStringRows() throws Exception {
        ObjectNode proof = (ObjectNode) DirectorScript.JSON.readTree("""
                {"mode":"matrix","rows":["A = [ 1 0 ; 0 1 ]"],"steps":[{"highlightRow":0}]}
                """);
        assertDoesNotThrow(() -> ProofScene.parse(proof, "test"));
        ((ObjectNode) proof.path("steps").get(0)).put("highlightRow", 1);
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
        ((ObjectNode) proof.path("steps").get(0)).put("highlightRow", 0);
        proof.set("rows", DirectorScript.JSON.readTree("[1]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
        proof.set("rows", DirectorScript.JSON.readTree("[\"1\",\"2\",\"3\",\"4\",\"5\",\"6\",\"7\",\"8\"]"));
        assertThrows(IllegalArgumentException.class, () -> ProofScene.parse(proof, "test"));
    }

    @Test
    void timingKeepsTheStartingPositionUntilTheFirstSpokenCue() throws Exception {
        ProofScene scene = ProofScene.parse(square(), "test");
        JsonNode timing = DirectorScript.JSON.readTree("{\"visualTimes\":[2],\"frames\":300,\"fps\":30}");
        assertArrayEquals(new int[]{0, 1, 2, 3}, scene.frame(timing, 1, 0.1).before());
        assertEquals(0, scene.frame(timing, 1, 0.1).fraction());
        assertArrayEquals(new int[]{0, 2, 3, 1}, scene.frame(timing, 9, 0.9).after());
        JsonNode wrong = DirectorScript.JSON.readTree("{\"visualTimes\":[0,1],\"frames\":300,\"fps\":30}");
        assertThrows(IllegalArgumentException.class, () -> scene.frame(wrong, 1, 0.1));
    }

    @Test
    void everySlideHasASettledObservationWindowBeforeTheNextSlide() throws Exception {
        ProofScene scene = ProofScene.parse(square(), "test");
        JsonNode timing = DirectorScript.JSON.readTree("{\"visualTimes\":[0],\"frames\":300,\"fps\":30}");
        // Four movements occupy the first 7.5s; sample at 90% of the first sub-window.
        ProofScene.Frame frame = scene.frame(timing, 7.5 / 4 * 0.9, 0.1);
        assertEquals(1, frame.fraction());
        assertArrayEquals(new int[]{1, 0, 2, 3}, frame.after());
    }

    @Test
    void mathematicalGlyphsUseTheConfiguredOrFallbackFont() {
        BufferedImage image = new BufferedImage(600, 80, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = image.createGraphics();
        try {
            graphics.setFont(new java.awt.Font("Microsoft YaHei UI", java.awt.Font.PLAIN, 25));
            assertDoesNotThrow(() -> MathText.draw(graphics, "β⁻¹ → α", 5, 40));
            assertTrue(MathText.width(graphics, "β⁻¹") > 0);
        } finally { graphics.dispose(); }
    }

    @Test
    void proofRenderingIsDeterministicAndMovesLabelsBetweenFrames() throws Exception {
        Path avatar = directory.resolve("avatar.png");
        BufferedImage placeholder = new BufferedImage(32, 32, BufferedImage.TYPE_INT_RGB);
        Graphics2D graphics = placeholder.createGraphics();
        graphics.setColor(Color.WHITE);
        graphics.fillRect(0, 0, 32, 32);
        graphics.dispose();
        ImageIO.write(placeholder, "png", avatar.toFile());
        PresenterAsset presenter = PresenterAsset.open(avatar, directory, "unused");
        var canvas = new MathCanvas(1280, 720, presenter, "Dialog");
        ObjectNode beat = DirectorScript.JSON.createObjectNode().put("view", "proof").put("chapter", "test")
                .put("heading", "test").put("narration", "test");
        beat.set("proof", square());
        JsonNode timing = DirectorScript.JSON.readTree("{\"visualTimes\":[0],\"frames\":300,\"fps\":30}");
        int[] first = canvas.render(beat, timing, 0, 0, 0, 1).getRGB(60, 160, 970, 380, null, 0, 970);
        int[] again = canvas.render(beat, timing, 0, 0, 0, 1).getRGB(60, 160, 970, 380, null, 0, 970);
        assertArrayEquals(first, again);
        int[] moving = canvas.render(beat, timing, 1, 1, 0, 1).getRGB(60, 160, 970, 380, null, 0, 970);
        assertFalse(java.util.Arrays.equals(first, moving));
    }
}
