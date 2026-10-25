package com.xenoamess.vivhite_video_framework.analyzer;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Case-specific mathematical checks, independent of language-model judgments. */
public final class SlidingPuzzle {
    private SlidingPuzzle() { }

    public static int inversionsIncludingBlank(int[] board) {
        int result = 0;
        for (int i = 0; i < board.length; i++) {
            for (int j = i + 1; j < board.length; j++) {
                if (board[i] > board[j]) {
                    result++;
                }
            }
        }
        return result;
    }

    public static int signature(int[] board, int rows, int columns) {
        validate(board, rows, columns);
        int blank = 0;
        while (board[blank] != 0) {
            blank++;
        }
        return (inversionsIncludingBlank(board) + blank / columns + blank % columns) & 1;
    }

    public static List<int[]> neighbors(int[] board, int rows, int columns) {
        validate(board, rows, columns);
        int blank = 0;
        while (board[blank] != 0) {
            blank++;
        }
        List<int[]> result = new ArrayList<>();
        for (int other : new int[]{blank - columns, blank + columns, blank - 1, blank + 1}) {
            if (other < 0 || other >= board.length || (Math.abs(other - blank) == 1
                    && other / columns != blank / columns)) {
                continue;
            }
            int[] next = board.clone();
            next[blank] = board[other];
            next[other] = 0;
            result.add(next);
        }
        return result;
    }

    public static List<int[]> shortestPath(int[] start, int[] goal, int rows, int columns) {
        validate(start, rows, columns);
        validate(goal, rows, columns);
        if (start.length > 9) {
            throw new IllegalArgumentException("Exhaustive demonstration solver is limited to at most nine cells");
        }
        Map<String, int[]> states = new HashMap<>();
        Map<String, String> parents = new HashMap<>();
        ArrayDeque<int[]> queue = new ArrayDeque<>();
        String first = Arrays.toString(start);
        states.put(first, start.clone());
        parents.put(first, null);
        queue.add(start.clone());
        String target = Arrays.toString(goal);
        while (!queue.isEmpty()) {
            int[] current = queue.removeFirst();
            String currentKey = Arrays.toString(current);
            if (currentKey.equals(target)) {
                List<int[]> path = new ArrayList<>();
                for (String key = target; key != null; key = parents.get(key)) {
                    path.add(states.get(key).clone());
                }
                Collections.reverse(path);
                return path;
            }
            for (int[] next : neighbors(current, rows, columns)) {
                String key = Arrays.toString(next);
                if (!parents.containsKey(key)) {
                    parents.put(key, currentKey);
                    states.put(key, next);
                    queue.addLast(next);
                }
            }
        }
        return List.of();
    }

    private static void validate(int[] board, int rows, int columns) {
        if (rows < 2 || columns < 2 || board.length != rows * columns) {
            throw new IllegalArgumentException("Use a rectangular board with at least two rows and two columns");
        }
        boolean[] seen = new boolean[board.length];
        for (int tile : board) {
            if (tile < 0 || tile >= board.length || seen[tile]) {
                throw new IllegalArgumentException("Board must be a permutation of 0 through rows*columns-1");
            }
            seen[tile] = true;
        }
    }
}
