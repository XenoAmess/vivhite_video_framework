package com.xenoamess.vivhite_video_framework.analyzer;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayDeque;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.junit.jupiter.api.Test;

class SlidingPuzzleTest {
    @Test
    void invariantMatchesEveryPermutationOfSmallRectangles() {
        exhaustivelyCheck(2, 2, 12);
        exhaustivelyCheck(2, 3, 360);
    }

    private void exhaustivelyCheck(int rows, int columns, int reachableCount) {
        int[] goal = new int[rows * columns];
        for (int i = 0; i < goal.length - 1; i++) {
            goal[i] = i + 1;
        }
        Set<String> reachable = new HashSet<>();
        ArrayDeque<int[]> queue = new ArrayDeque<>();
        queue.add(goal);
        reachable.add(Arrays.toString(goal));
        int signature = SlidingPuzzle.signature(goal, rows, columns);
        while (!queue.isEmpty()) {
            int[] current = queue.removeFirst();
            assertEquals(signature, SlidingPuzzle.signature(current, rows, columns));
            for (int[] next : SlidingPuzzle.neighbors(current, rows, columns)) {
                if (reachable.add(Arrays.toString(next))) {
                    queue.addLast(next);
                }
            }
        }
        assertEquals(reachableCount, reachable.size());
        checkPermutations(goal, 0, rows, columns, signature, reachable);
    }

    private void checkPermutations(int[] board, int index, int rows, int columns,
                                   int goalSignature, Set<String> reachable) {
        if (index == board.length) {
            assertEquals(reachable.contains(Arrays.toString(board)),
                    SlidingPuzzle.signature(board, rows, columns) == goalSignature);
            return;
        }
        for (int i = index; i < board.length; i++) {
            int temporary = board[index]; board[index] = board[i]; board[i] = temporary;
            checkPermutations(board, index + 1, rows, columns, goalSignature, reachable);
            temporary = board[index]; board[index] = board[i]; board[i] = temporary;
        }
    }

    @Test
    void originalVideoExampleHasARealLegalSolution() {
        int[] start = {2, 3, 1, 4, 5, 0};
        int[] goal = {1, 2, 3, 4, 5, 0};
        assertEquals(7, SlidingPuzzle.inversionsIncludingBlank(start));
        assertEquals(5, SlidingPuzzle.inversionsIncludingBlank(goal));
        var path = SlidingPuzzle.shortestPath(start, goal, 2, 3);
        assertFalse(path.isEmpty());
        assertArrayEquals(start, path.getFirst());
        assertArrayEquals(goal, path.getLast());
        for (int i = 1; i < path.size(); i++) {
            int[] next = path.get(i);
            assertTrue(SlidingPuzzle.neighbors(path.get(i - 1), 2, 3).stream()
                    .anyMatch(candidate -> Arrays.equals(candidate, next)));
        }
    }

    @Test
    void swappingTwoNonblankTilesCannotBeSolved() {
        assertTrue(SlidingPuzzle.shortestPath(new int[]{2, 1, 3, 4, 5, 0},
                new int[]{1, 2, 3, 4, 5, 0}, 2, 3).isEmpty());
        assertThrows(IllegalArgumentException.class,
                () -> SlidingPuzzle.signature(new int[]{1, 2, 0}, 1, 3));
        assertThrows(IllegalArgumentException.class,
                () -> SlidingPuzzle.signature(new int[]{1, 1, 2, 0}, 2, 2));
    }
}
