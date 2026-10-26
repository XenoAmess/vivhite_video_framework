package com.xenoamess.vivhite_video_framework.maker;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Independent production-side checks; the maker consumes no analyzer classes. */
public final class PuzzleMath {
    private PuzzleMath() { }

    public static void validate(int[] state, int columns) {
        if (columns < 2 || state.length % columns != 0 || state.length / columns < 2) {
            throw new IllegalArgumentException("A rectangular board needs at least two rows and columns");
        }
        boolean[] found = new boolean[state.length];
        for (int value : state) {
            if (value < 0 || value >= state.length || found[value]) {
                throw new IllegalArgumentException("Board must contain each label 0..n-1 exactly once");
            }
            found[value] = true;
        }
    }

    public static int inversions(int[] state) {
        int count = 0;
        for (int i = 0; i < state.length; i++) {
            for (int j = i + 1; j < state.length; j++) {
                if (state[i] > state[j]) { count++; }
            }
        }
        return count;
    }

    public static int blank(int[] state) {
        for (int i = 0; i < state.length; i++) { if (state[i] == 0) { return i; } }
        throw new IllegalArgumentException("Missing blank");
    }

    public static int signature(int[] state, int columns) {
        int zero = blank(state);
        return (inversions(state) + zero / columns + zero % columns) & 1;
    }

    public static boolean legalMove(int[] before, int[] after, int columns) {
        if (before.length != after.length) { return false; }
        int a = blank(before);
        int b = blank(after);
        if (Math.abs(a / columns - b / columns) + Math.abs(a % columns - b % columns) != 1) { return false; }
        for (int i = 0; i < before.length; i++) {
            if (after[i] != (i == a ? before[b] : i == b ? 0 : before[i])) { return false; }
        }
        return true;
    }

    public static List<int[]> neighbors(int[] state, int columns) {
        var result = new ArrayList<int[]>();
        int zero = blank(state);
        for (int i = 0; i < state.length; i++) {
            if (Math.abs(i / columns - zero / columns) + Math.abs(i % columns - zero % columns) == 1) {
                int[] next = state.clone();
                next[zero] = state[i];
                next[i] = 0;
                result.add(next);
            }
        }
        return result;
    }

    public static List<int[]> shortestPath(int[] start, int[] goal, int columns) {
        validate(start, columns);
        validate(goal, columns);
        if (start.length > 9 || start.length != goal.length) {
            throw new IllegalArgumentException("Finite demo search supports equal boards with at most 9 cells");
        }
        String target = Arrays.toString(goal);
        var queue = new ArrayDeque<int[]>();
        Map<String, int[]> parents = new HashMap<>();
        queue.add(start);
        parents.put(Arrays.toString(start), null);
        while (!queue.isEmpty()) {
            int[] current = queue.remove();
            if (Arrays.toString(current).equals(target)) {
                var path = new ArrayList<int[]>();
                for (int[] cursor = current; cursor != null; cursor = parents.get(Arrays.toString(cursor))) { path.add(cursor); }
                Collections.reverse(path);
                return path;
            }
            for (int[] next : neighbors(current, columns)) {
                String key = Arrays.toString(next);
                if (!parents.containsKey(key)) { parents.put(key, current); queue.add(next); }
            }
        }
        return List.of();
    }
}
