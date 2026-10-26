package com.xenoamess.vivhite_video_framework.maker;

import static org.junit.jupiter.api.Assertions.*;

import com.fasterxml.jackson.databind.node.ObjectNode;
import java.time.Duration;
import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import org.junit.jupiter.api.Test;

class ProductionTest {
    @Test
    void everyReachableSixCellStatePreservesRenderedSignature() {
        int[] root = {1, 2, 3, 4, 5, 0};
        var seen = new HashSet<String>();
        var queue = new ArrayDeque<int[]>();
        queue.add(root);
        seen.add(Arrays.toString(root));
        while (!queue.isEmpty()) {
            int[] state = queue.remove();
            for (int[] next : PuzzleMath.neighbors(state, 3)) {
                assertTrue(PuzzleMath.legalMove(state, next, 3));
                assertEquals(PuzzleMath.signature(state, 3), PuzzleMath.signature(next, 3));
                assertEquals(1, (PuzzleMath.inversions(state) + PuzzleMath.inversions(next)) & 1);
                if (seen.add(Arrays.toString(next))) { queue.add(next); }
            }
        }
        assertEquals(360, seen.size());
        List<int[]> path = PuzzleMath.shortestPath(new int[]{2, 3, 1, 4, 5, 0}, root, 3);
        assertEquals(15, path.size());
        assertTrue(PuzzleMath.shortestPath(new int[]{2, 1, 3, 4, 5, 0}, root, 3).isEmpty());
    }

    @Test
    void rejectTeleportAndDuplicateLabels() throws Exception {
        ObjectNode plan = (ObjectNode) DirectorScript.JSON.readTree("""
                {"schemaVersion":"vivhite-production-1","title":"test","width":1280,"height":720,"fps":30,
                 "voice":{"provider":"edge-tts","name":"zh-CN-XiaoxiaoNeural","rate":"+0%"},
                 "beats":[{"id":"b01","chapter":"a","heading":"a","narration":"test","view":"board",
                    "action":"move","states":[[1,2,3,4,5,0],[0,2,3,4,5,1]]}]}
                """);
        assertThrows(IllegalArgumentException.class, () -> ProductionPlan.validate(plan));
        ((ObjectNode) plan.path("beats").get(0)).set("states", DirectorScript.JSON.readTree("[[1,2,3,4,5,0],[1,2,3,4,0,5]]"));
        assertDoesNotThrow(() -> ProductionPlan.validate(plan));
        assertThrows(IllegalArgumentException.class, () -> PuzzleMath.validate(new int[]{1, 2, 3, 4, 5, 5}, 3));
    }

    @Test
    void cycleHasTwelveActualStatesAndClosesLegally() {
        List<int[]> states = MathCanvas.cycleStates(new int[]{1, 2, 3, 0});
        assertEquals(12, states.size());
        for (int i = 0; i < states.size(); i++) {
            assertTrue(PuzzleMath.legalMove(states.get(i), states.get((i + 1) % states.size()), 2));
        }
    }

    @Test
    void blockedEncoderInputIsCancelledOnTimeout() {
        String javaExecutable = java.nio.file.Path.of(System.getProperty("java.home"), "bin", "java").toString();
        assertTimeoutPreemptively(Duration.ofSeconds(8), () -> assertThrows(Exception.class, () ->
                MediaProcess.run(List.of(javaExecutable, "-cp", System.getProperty("java.class.path"), SleepingProcess.class.getName()),
                        Duration.ofMillis(500), stream -> { while (true) { stream.write(new byte[65536]); } })));
    }

    public static class SleepingProcess {
        public static void main(String[] args) throws Exception { Thread.sleep(60_000); }
    }
}
