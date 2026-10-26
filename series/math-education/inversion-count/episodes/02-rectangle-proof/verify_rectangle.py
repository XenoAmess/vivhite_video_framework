"""Check the finite certificates used by episode 2; not a proof by sampling."""

from __future__ import annotations

import argparse
from collections import deque
import itertools
import json
from pathlib import Path
import re


def compose(left: tuple[int, ...], right: tuple[int, ...]) -> tuple[int, ...]:
    """Act on positions; left * right applies right first."""
    return tuple(left[right[index]] for index in range(len(left)))


def cycle(size: int, *points: int) -> tuple[int, ...]:
    result = list(range(size))
    for before, after in zip(points, points[1:] + points[:1]):
        result[before] = after
    return tuple(result)


def inverse(permutation: tuple[int, ...]) -> tuple[int, ...]:
    result = list(range(len(permutation)))
    for before, after in enumerate(permutation):
        result[after] = before
    return tuple(result)


def face_walk(columns: int, row: int, column: int) -> list[int]:
    """Root path, reverse face circuit, reverse root path; starts at root."""
    path = list(range(column + 1))
    path += [level * columns + column for level in range(1, row + 1)]
    anchor = row * columns + column
    a, b, c = anchor + 1, anchor + columns + 1, anchor + columns
    return path + [c, b, a, anchor] + list(reversed(path[:-1]))


def apply_walk(state: tuple[int, ...], walk: list[int], columns: int) -> tuple[int, ...]:
    result = list(state)
    assert result[walk[0]] == 0, "The walk must begin at the blank."
    for before, after in zip(walk, walk[1:]):
        assert 0 <= after < len(result), "Move leaves the board."
        before_row, before_column = divmod(before, columns)
        after_row, after_column = divmod(after, columns)
        assert abs(before_row - after_row) + abs(before_column - after_column) == 1
        assert result[before] == 0
        result[before], result[after] = result[after], result[before]
    return tuple(result)


def invariant(state: tuple[int, ...], columns: int) -> int:
    inversions = sum(left > right for index, left in enumerate(state) for right in state[index + 1:])
    row, column = divmod(state.index(0), columns)
    return (inversions + row + column) % 2


def neighbors(state: tuple[int, ...], columns: int) -> list[tuple[int, ...]]:
    zero = state.index(0)
    row, column = divmod(zero, columns)
    rows = len(state) // columns
    next_positions = []
    if row:
        next_positions.append(zero - columns)
    if row + 1 < rows:
        next_positions.append(zero + columns)
    if column:
        next_positions.append(zero - 1)
    if column + 1 < columns:
        next_positions.append(zero + 1)
    return [apply_walk(state, [zero, after], columns) for after in next_positions]


def check_small_board(rows: int, columns: int) -> dict[str, object]:
    states = set(itertools.permutations(range(rows * columns)))
    all_states = list(states)
    components = []
    directed_edges = 0
    while states:
        start = min(states)
        queue = deque([start])
        states.remove(start)
        component = {start}
        while queue:
            current = queue.popleft()
            for after in neighbors(current, columns):
                directed_edges += 1
                assert invariant(current, columns) == invariant(after, columns)
                if after in states:
                    states.remove(after)
                    component.add(after)
                    queue.append(after)
        values = {invariant(state, columns) for state in component}
        assert len(values) == 1
        components.append({"states": len(component), "invariant": values.pop()})
    assert len(components) == 2
    assert {entry["invariant"] for entry in components} == {0, 1}
    histogram = {str(value): sum(invariant(state, columns) == value for state in all_states) for value in (0, 1)}
    assert all(entry["states"] == histogram[str(entry["invariant"])] for entry in components)
    return {
        "rows": rows,
        "columns": columns,
        "allStates": len(all_states),
        "allDirectedLegalEdges": directed_edges,
        "components": components,
        "invariantHistogram": histogram,
        "reachabilityIffInvariantEqual": True,
    }


def generated_group_order(size: int, generators: list[tuple[int, ...]]) -> int:
    identity = tuple(range(size))
    seen = {identity}
    queue = deque([identity])
    while queue:
        current = queue.popleft()
        for generator in generators:
            after = compose(generator, current)
            if after not in seen:
                seen.add(after)
                queue.append(after)
    return len(seen)


def check_director() -> dict[str, object]:
    directory = Path(__file__).resolve().parent
    director = (directory / "director.md").read_text(encoding="utf-8")
    pacing = json.loads((directory / "pacing.json").read_text(encoding="utf-8"))
    scenes = re.split(r"(?m)^### ", director)[1:]
    assert len(scenes) == pacing["sceneCount"] == len(pacing["scenes"]) == 28
    previous_end = 0
    narration_characters = 0
    for index, (scene, record) in enumerate(zip(scenes, pacing["scenes"]), 1):
        title = scene.splitlines()[0]
        match = re.match(r"(\d{2})｜(\d{2}):(\d{2})–(\d{2}):(\d{2})｜", title)
        assert match is not None
        scene_id, start_minute, start_second, end_minute, end_second = map(int, match.groups())
        assert scene_id == index
        start = start_minute * 60 + start_second
        end = end_minute * 60 + end_second
        assert start == previous_end == record["startSeconds"]
        assert end == record["endSeconds"] > start
        assert end - start == record["speechBudgetSeconds"] + record["additionalObservationSeconds"]
        narration = scene.split("**旁白：**", 1)[1].split("**动作：**", 1)[0]
        characters = sum(character.isalpha() or character.isdecimal() for character in narration)
        assert characters == record["narrationCharacters"]
        assert "**屏幕：**" in scene
        assert record["observationTask"]
        narration_characters += characters
        previous_end = end
    assert previous_end == pacing["budgetDurationSeconds"]
    assert narration_characters == pacing["narrationCharacters"]
    for path in directory.glob("*.md"):
        for target in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if "://" not in target and not target.startswith("#"):
                assert (path.parent / target.split("#", 1)[0]).is_file(), (path, target)
    return {
        "sceneCount": len(scenes),
        "narrationCharacters": narration_characters,
        "budgetDurationSeconds": previous_end,
        "measuredAudio": False,
        "continuousTimelineAndMatchingPacing": True,
        "localMarkdownLinksExist": True,
    }


def verify() -> dict[str, object]:
    faces_checked = 0
    moves_checked = 0
    for rows in range(2, 9):
        for columns in range(2, 9):
            size = rows * columns
            supports = []
            for row in range(rows - 1):
                for column in range(columns - 1):
                    anchor = row * columns + column
                    a, b, c = anchor + 1, anchor + columns + 1, anchor + columns
                    walk = face_walk(columns, row, column)
                    state = apply_walk(tuple(range(size)), walk, columns)
                    position_action = inverse(state)
                    assert position_action == cycle(size, a, b, c)
                    assert apply_walk(state, list(reversed(walk)), columns) == tuple(range(size))
                    assert invariant(state, columns) == invariant(tuple(range(size)), columns)
                    supports.append({a, b, c})
                    faces_checked += 1
                    moves_checked += len(walk) - 1
            assert set.union(*supports) == set(range(1, size))
            for row in range(rows - 1):
                for column in range(columns - 1):
                    index = row * (columns - 1) + column
                    if column + 1 < columns - 1:
                        assert supports[index] & supports[index + 1]
                    if row + 1 < rows - 1:
                        assert supports[index] & supports[index + columns - 1]

    # Independently verify the algebraic identities shown on screen.
    a, b, c, d = 0, 1, 2, 3
    alpha = cycle(5, a, b, c)
    beta = cycle(5, d, b, c)
    assert compose(alpha, inverse(beta)) == cycle(5, a, b, d)
    assert compose(cycle(5, a, b), cycle(5, c, d)) == compose(cycle(5, a, c, b), cycle(5, a, c, d))
    assert compose(cycle(5, a, b), cycle(5, b, c)) == cycle(5, a, b, c)
    overlap_two_order = generated_group_order(4, [cycle(4, 0, 1, 2), cycle(4, 1, 2, 3)])
    overlap_one_order = generated_group_order(5, [cycle(5, 0, 1, 2), cycle(5, 2, 3, 4)])
    assert overlap_two_order == 12
    assert overlap_one_order == 60

    # The opening board is produced by two genuine face tools, never teleporting tiles.
    columns = 4
    goal = tuple(range(12))
    first = face_walk(columns, 0, 1)
    second = face_walk(columns, 1, 2)
    production_walk = first + second[1:]
    opening = apply_walk(goal, production_walk, columns)
    wrong = list(opening)
    wrong[8], wrong[9] = wrong[9], wrong[8]
    closing_walk = list(reversed(production_walk))
    assert invariant(opening, columns) == invariant(goal, columns)
    assert invariant(tuple(wrong), columns) != invariant(goal, columns)
    assert apply_walk(opening, closing_walk, columns) == goal

    # Every row-order permutation admits a bubble-sort decomposition into inv swaps.
    permutations_checked = 0
    for size in range(2, 8):
        for state in itertools.permutations(range(size)):
            work = list(state)
            swaps = 0
            for upper in range(size - 1, 0, -1):
                for index in range(upper):
                    if work[index] > work[index + 1]:
                        work[index], work[index + 1] = work[index + 1], work[index]
                        swaps += 1
            inversion_count = sum(left > right for index, left in enumerate(state) for right in state[index + 1:])
            assert swaps == inversion_count
            permutations_checked += 1

    return {
        "schemaVersion": "vivhite-rectangle-verification-1",
        "passed": True,
        "proofScope": "The universal result is proved in proof.md. Finite checks validate identities and production data only.",
        "geometry": {"rows": [2, 8], "columns": [2, 8], "boardsChecked": 49, "facesChecked": faces_checked, "movesChecked": moves_checked, "allPositionActionsAndSupportsCorrect": True},
        "algebra": {"composition": "right-to-left", "threeCycleGluingIdentity": True, "disjointTranspositionPairIdentity": True, "overlappingTranspositionPairIdentity": True, "bubbleSortPermutationsChecked": permutations_checked, "twoTriangleOverlapTwoGeneratedGroupOrder": overlap_two_order, "twoTriangleOverlapOneGeneratedGroupOrder": overlap_one_order},
        "smallBoards": [check_small_board(2, 2), check_small_board(2, 3), check_small_board(3, 2)],
        "openingAndClosing": {"rows": 3, "columns": 4, "goal": goal, "reachableOpening": opening, "unreachableOpening": wrong, "blankWalkFromGoalToOpening": production_walk, "blankWalkFromOpeningToGoal": closing_walk, "legalMoveCount": len(production_walk) - 1, "goalInvariant": invariant(goal, columns), "reachableInvariant": invariant(opening, columns), "unreachableInvariant": invariant(tuple(wrong), columns)},
        "director": check_director(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(verify(), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(report, encoding="utf-8", newline="\n")
        print(f"Rectangle certificates passed; report: {args.output}")
    else:
        print(report, end="")


if __name__ == "__main__":
    main()
