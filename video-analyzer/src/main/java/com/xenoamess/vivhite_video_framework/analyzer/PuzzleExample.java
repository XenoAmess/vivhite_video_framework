package com.xenoamess.vivhite_video_framework.analyzer;

import static com.xenoamess.vivhite_video_framework.analyzer.JsonFiles.JSON;

import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;

/** Reproducible numerical evidence for the first real-world case. */
public final class PuzzleExample {
    private PuzzleExample() { }

    public static void write(Path output) throws Exception {
        int[] start = {2, 3, 1, 4, 5, 0};
        int[] goal = {1, 2, 3, 4, 5, 0};
        var path = SlidingPuzzle.shortestPath(start, goal, 2, 3);
        var report = JSON.createObjectNode().put("schemaVersion", "1.0").put("rows", 2).put("columns", 3)
                .put("coordinateConvention", "zero-based row and column; permutation includes blank 0")
                .put("startInversions", SlidingPuzzle.inversionsIncludingBlank(start))
                .put("goalInversions", SlidingPuzzle.inversionsIncludingBlank(goal))
                .put("signature", SlidingPuzzle.signature(start, 2, 3)).put("moveCount", path.size() - 1);
        report.set("start", JSON.valueToTree(start));
        report.set("goal", JSON.valueToTree(goal));
        var states = report.putArray("states");
        for (int[] board : path) {
            if (SlidingPuzzle.signature(board, 2, 3) != report.path("signature").asInt()) {
                throw new IllegalStateException("Invariant failed");
            }
            states.add(JSON.valueToTree(board));
        }
        var rowEnd = List.of(new int[]{1, 0, 2, 4, 5, 3, 7, 8, 6},
                new int[]{1, 2, 0, 4, 5, 3, 7, 8, 6}, new int[]{1, 2, 3, 4, 5, 0, 7, 8, 6});
        for (int i = 1; i < rowEnd.size(); i++) {
            int[] next = rowEnd.get(i);
            if (SlidingPuzzle.neighbors(rowEnd.get(i - 1), 3, 3).stream()
                    .noneMatch(candidate -> Arrays.equals(candidate, next))) {
                throw new IllegalStateException("Illegal row-end demonstration");
            }
        }
        report.set("rowEndDemonstration", JSON.valueToTree(rowEnd));
        var checks = report.putArray("exhaustiveVerification");
        for (int columns : new int[]{2, 3}) {
            int[] board = new int[2 * columns];
            for (int i = 0; i < board.length - 1; i++) {
                board[i] = i + 1;
            }
            var all = new ArrayList<int[]>();
            permutations(board, 0, all);
            var reachable = new HashSet<String>();
            var queue = new ArrayDeque<int[]>();
            queue.add(board.clone());
            reachable.add(Arrays.toString(board));
            while (!queue.isEmpty()) {
                for (int[] next : SlidingPuzzle.neighbors(queue.removeFirst(), 2, columns)) {
                    if (reachable.add(Arrays.toString(next))) {
                        queue.addLast(next);
                    }
                }
            }
            int goalSignature = SlidingPuzzle.signature(board, 2, columns);
            var graph = JSON.createObjectNode().put("rows", 2).put("columns", columns);
            var nodes = graph.putArray("nodes");
            for (int[] candidate : all) {
                int signature = SlidingPuzzle.signature(candidate, 2, columns);
                if (reachable.contains(Arrays.toString(candidate)) != (signature == goalSignature)) {
                    throw new IllegalStateException("Parity/reachability mismatch");
                }
                var node = nodes.addObject().put("signature", signature);
                node.set("board", JSON.valueToTree(candidate));
                node.set("neighbors", JSON.valueToTree(SlidingPuzzle.neighbors(candidate, 2, columns)));
            }
            String file = "puzzle-2x" + columns + "-graph.json";
            JsonFiles.write(output.resolveSibling(file), graph);
            checks.addObject().put("rows", 2).put("columns", columns).put("totalStates", all.size())
                    .put("reachableStates", reachable.size()).put("otherComponentStates", all.size() - reachable.size())
                    .put("signatureMatchesReachability", true).put("graphFile", file);
        }
        JsonFiles.write(output, report);
        System.out.println("Verified shortest legal sequence: " + (path.size() - 1) + " moves");
    }

    private static void permutations(int[] board, int index, List<int[]> result) {
        if (index == board.length) {
            result.add(board.clone());
            return;
        }
        for (int i = index; i < board.length; i++) {
            int swap = board[index]; board[index] = board[i]; board[i] = swap;
            permutations(board, index + 1, result);
            swap = board[index]; board[index] = board[i]; board[i] = swap;
        }
    }
}
