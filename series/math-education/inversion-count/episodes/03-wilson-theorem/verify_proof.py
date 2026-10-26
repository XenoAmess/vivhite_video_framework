#!/usr/bin/env python3
"""Reproduce finite certificates used by this episode; Python standard library only.

Permutation products act from left to right. Exhaustive checks below certify the
bounded exceptional cases, not the infinite graph theorem. The latter is proved
in proof.md using explicit identities, triangle gluing, and ear extension.
"""

from collections import deque
from itertools import combinations
import argparse
import json
from pathlib import Path


def identity(size):
    return tuple(range(size))


def compose(first, second):
    return tuple(second[value] for value in first)


def multiply(*items):
    answer = identity(len(items[0]))
    for item in items:
        answer = compose(answer, item)
    return answer


def inverse(item):
    answer = [0] * len(item)
    for source, target in enumerate(item):
        answer[target] = source
    return tuple(answer)


def power(item, exponent):
    if exponent < 0:
        return power(inverse(item), -exponent)
    answer = identity(len(item))
    while exponent:
        if exponent & 1:
            answer = compose(answer, item)
        item = compose(item, item)
        exponent >>= 1
    return answer


def cycle(labels, *names):
    answer = list(identity(len(labels)))
    if len(names) > 1:
        for source, target in zip(names, names[1:] + names[:1]):
            answer[labels.index(source)] = labels.index(target)
    return tuple(answer)


def support(item):
    return {index for index, image in enumerate(item) if index != image}


def closure(generators):
    seen = {identity(len(generators[0]))}
    pending = deque(seen)
    while pending:
        value = pending.popleft()
        for generator in generators:
            image = compose(value, generator)
            if image not in seen:
                seen.add(image)
                pending.append(image)
    return seen


def long_cycles(n, m, extra=()):
    aa = [f'a{i}' for i in range(1, n + 1)]
    bb = [f'b{i}' for i in range(1, m + 1)]
    labels = ['y'] + aa + ['z'] + bb + list(extra)
    return labels, cycle(labels, *(aa + ['z'] + bb)), cycle(labels, *(bb + ['y'] + aa))


def three_cycle_word(n, m):
    labels, pi, rho = long_cycles(n, m)
    if m >= 3 and n in (m, 2 * m):
        k = n - m
        s1 = multiply(inverse(pi), rho)
        s2 = multiply(inverse(pi), s1, pi)
        s3 = multiply(inverse(pi), s2, pi)
        s4 = multiply(power(rho, m), s1, power(rho, -m))
        s5 = multiply(s4, s2)
        s6 = multiply(inverse(pi), s5, pi)
        s7 = multiply(power(rho, m - 1), s1, power(rho, 1 - m))
        s8 = multiply(s3, s7)
        result = multiply(s6, s8)
        expected = [
            multiply(cycle(labels, 'y', 'a1'), cycle(labels, 'z', 'b1')),
            multiply(cycle(labels, 'y', 'a2'), cycle(labels, 'b1', 'b2')),
            multiply(cycle(labels, 'y', 'a3'), cycle(labels, 'b2', 'b3')),
            multiply(cycle(labels, 'b1', 'b2'), cycle(labels, 'z', f'a{k + 1}')),
            multiply(cycle(labels, 'y', 'a2'), cycle(labels, 'z', f'a{k + 1}')),
            multiply(cycle(labels, 'y', 'a3'), cycle(labels, 'b1', f'a{k + 2}')),
            multiply(cycle(labels, 'b2', 'b3'), cycle(labels, 'z', f'a{k + 2}')),
            multiply(cycle(labels, 'y', 'a3'), cycle(labels, 'z', f'a{k + 2}')),
            cycle(labels, 'z', f'a{k + 2}', 'b1'),
        ]
        assert [s1, s2, s3, s4, s5, s6, s7, s8, result] == expected
    elif n > m >= 0 and n != 2 * m:
        t1 = multiply(inverse(pi), rho)
        if m == 0:
            result = t1
        else:
            t2 = multiply(power(rho, -m), t1, power(rho, m))
            t3 = multiply(power(pi, -2 * m), t1, power(pi, 2 * m))
            result = multiply(t2, t3)
            c = labels[power(pi, 2 * m)[labels.index('a1')]]
            assert c not in {'y', 'z', f'a{m}', f'a{m + 1}'}
            assert t2 == multiply(cycle(labels, f'a{m}', f'a{m + 1}'), cycle(labels, 'z', 'y'))
            assert t3 == multiply(cycle(labels, 'y', c), cycle(labels, f'a{m}', f'a{m + 1}'))
            assert result == cycle(labels, 'y', 'z', c)
    elif n == m == 1:
        result = pi
    else:
        return None
    assert len(support(result)) == 3, (n, m, result)
    return result


def walk_permutation(labels, walk, adjacency=None):
    answer = identity(len(labels))
    for source, target in zip(walk, walk[1:]):
        if adjacency is not None:
            assert target in adjacency[source], (source, target)
        answer = compose(answer, cycle(labels, source, target))
    return answer


def connected_conjugate_supports(labels, generators, seed):
    """All conjugate supports have size 3; overlapping supports must cover X."""
    initial = frozenset(support(seed))
    seen = {initial}
    pending = deque(seen)
    while pending:
        old = pending.popleft()
        for generator in generators:
            new = frozenset(generator[index] for index in old)
            if new not in seen:
                seen.add(new)
                pending.append(new)
    covered = set(initial)
    while True:
        new = covered.union(*(triple for triple in seen if triple & covered))
        if new == covered:
            break
        covered = new
    assert covered == set(range(len(labels)))
    return len(seen)


def special_theta_certificates():
    results = []
    for n, m in [(2, 2), (4, 2)]:
        labels, pi, rho = long_cycles(n, m, ['c1'])
        # Root x lies on y-c1-x-z. The walk x-z-b1-...-bm-y-c1-x
        # induces the inverse cycle below; reversing that legal walk gives tau.
        tau = cycle(labels, *(['z'] + [f'b{i}' for i in range(1, m + 1)] + ['y', 'c1']))
        if n == 2:
            seed = multiply(power(pi, 2), rho, power(pi, 2), tau, inverse(pi), rho, inverse(tau))
            assert seed == cycle(labels, 'z', 'y', 'c1'), seed
            orbit_size = connected_conjugate_supports(labels, [pi, rho, tau], seed)
        else:
            seed = multiply(rho, inverse(pi), power(tau, -2), inverse(pi), rho, power(tau, 2))
            assert seed == cycle(labels, 'z', 'a4', 'a1'), seed
            orbit_size = connected_conjugate_supports(labels, [pi, rho, tau], seed)
        results.append({'internalArmLengths': [n, 2, m], 'threeCycleSupport': [labels[index] for index in sorted(support(seed))], 'conjugateSupports': orbit_size, 'connected': True})
    return results


def legal_theta_words():
    cases = 0
    for n in range(1, 7):
        for m in range(n + 1):
            for s in range(3):
                for t in range(3):
                    aa = [f'a{i}' for i in range(1, n + 1)]
                    bb = [f'b{i}' for i in range(1, m + 1)]
                    cc = [f'c{i}' for i in range(1, s + 1)]
                    dd = [f'd{i}' for i in range(1, t + 1)]
                    labels = ['x', 'y', 'z'] + aa + bb + cc + dd
                    adjacency = {name: set() for name in labels}
                    arms = [['y'] + aa + ['z'], ['y'] + bb[::-1] + ['z'], ['y'] + cc[::-1] + ['x'] + dd + ['z']]
                    for arm in arms:
                        for source, target in zip(arm, arm[1:]):
                            adjacency[source].add(target)
                            adjacency[target].add(source)
                    q = ['x'] + cc + ['y']
                    r = ['x'] + dd + ['z']
                    p1 = ['z'] + aa[::-1] + ['y']
                    p2 = ['y'] + bb[::-1] + ['z']
                    pi = walk_permutation(labels, q + p2[1:] + p1[1:] + q[::-1][1:], adjacency)
                    rho = walk_permutation(labels, r + p1[1:] + p2[1:] + r[::-1][1:], adjacency)
                    tau = walk_permutation(labels, q + p2[1:] + r[::-1][1:], adjacency)
                    assert pi == cycle(labels, *(aa + ['z'] + bb))
                    assert rho == cycle(labels, *(bb + ['y'] + aa))
                    assert tau == cycle(labels, *(dd + ['z'] + bb + ['y'] + cc[::-1]))
                    assert pi[0] == rho[0] == tau[0] == 0
                    cases += 1
    return cases


def theta_zero():
    arms = [['inf', '0', '1', '2'], ['inf', '4', '3', '2'], ['inf', 'x', '2']]
    adjacency = {name: set() for name in ['x', 'inf', '0', '1', '2', '3', '4']}
    for arm in arms:
        for source, target in zip(arm, arm[1:]):
            adjacency[source].add(target)
            adjacency[target].add(source)
    return adjacency


def simple_paths(adjacency, source, target):
    def visit(path):
        if path[-1] == target:
            yield path
        else:
            for neighbor in sorted(adjacency[path[-1]]):
                if neighbor not in path:
                    yield from visit(path + [neighbor])
    return list(visit([source]))


def ear_certificates():
    adjacency = theta_zero()
    answer = []
    for source, target in combinations(sorted(adjacency), 2):
        for length in [1, 2, 3]:
            if length == 1 and target in adjacency[source]:
                continue  # A simple graph cannot add an existing edge again.
            extended = {vertex: set(neighbors) for vertex, neighbors in adjacency.items()}
            new_ear = [source] + [f'e{i}' for i in range(1, length)] + [target]
            for vertex in new_ear:
                extended.setdefault(vertex, set())
            for first, second in zip(new_ear, new_ear[1:]):
                extended[first].add(second)
                extended[second].add(first)
            witness = None
            branch_pairs = [(source, target)] + [pair for pair in combinations(sorted(extended), 2) if pair != (source, target)]
            for branch_source, branch_target in branch_pairs:
                paths = simple_paths(extended, branch_source, branch_target)
                for triple in combinations(paths, 3):
                    interiors = [set(path[1:-1]) for path in triple]
                    if any(interiors[i] & interiors[j] for i, j in combinations(range(3), 2)):
                        continue
                    lengths = [len(path) - 1 for path in triple]
                    if sorted(lengths) != [2, 3, 3]:
                        witness = {'ends': [source, target], 'earEdges': length, 'newEar': new_ear, 'thetaBranches': [branch_source, branch_target], 'thetaPaths': triple, 'thetaArmEdges': lengths}
                        break
                if witness is not None:
                    break
            assert witness is not None, (source, target, length)
            answer.append(witness)
    return answer


def mobius_permutations():
    labels = list(range(5)) + ['inf']
    result = set()
    for a in range(5):
        for b in range(5):
            for c in range(5):
                for d in range(5):
                    if (a * d - b * c) % 5 == 0:
                        continue
                    images = []
                    for value in labels:
                        if value == 'inf':
                            image = 'inf' if c == 0 else (a * pow(c, -1, 5)) % 5
                        else:
                            denominator = (c * value + d) % 5
                            image = 'inf' if denominator == 0 else ((a * value + b) * pow(denominator, -1, 5)) % 5
                        images.append(labels.index(image))
                    result.add(tuple(images))
    assert len(result) == 120
    return labels, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()

    word_cases = 0
    for n in range(1, 17):
        for m in range(n + 1):
            result = three_cycle_word(n, m)
            if result is not None:
                word_cases += 1
            else:
                assert (n, m) in [(2, 1), (2, 2), (4, 2)]

    exception_orders = []
    for n, m, expected in [(2, 1, 20), (2, 2, 60), (4, 2, 1344)]:
        labels, pi, rho = long_cycles(n, m)
        elements = closure([pi, rho])
        assert len(elements) == expected
        assert not any(len(support(item)) == 3 for item in elements)
        exception_orders.append({'n': n, 'm': m, 'order': expected, 'threeCycles': 0})

    adjacency = theta_zero()
    labels = ['x', '0', '1', '2', '3', '4', 'inf']
    pp = walk_permutation(labels, ['x', 'inf', '4', '3', '2', '1', '0', 'inf', 'x'], adjacency)
    qq = walk_permutation(labels, ['x', '2', '1', '0', 'inf', 'x'], adjacency)
    assert pp == cycle(labels, '0', '1', '2', '3', '4')
    assert qq == cycle(labels, 'inf', '0', '1', '2')
    root_group = closure([pp, qq])
    _, mobius = mobius_permutations()
    projected = {tuple(item[index + 1] - 1 for index in range(6)) for item in root_group}
    assert projected == mobius
    triples = {tuple(item[index] for index in [1, 2, 3]) for item in root_group}
    assert len(triples) == 120

    ears = ear_certificates()
    legal_word_cases = legal_theta_words()
    result = {
        'schemaVersion': 'vivhite-wilson-proof-certificate-1',
        'permutationConvention': 'left-to-right',
        'generalIdentitySpotChecks': {'maximumN': 16, 'cases': word_cases, 'provesInfiniteFamily': False},
        'longCycleExceptionalGroups': exception_orders,
        'legalThetaWordSpotChecks': {'cases': legal_word_cases, 'allThreeLoopsLegalAndMatchStatedCycles': True, 'provesInfiniteFamily': False},
        'specialThetaGraphs': special_theta_certificates(),
        'thetaZero': {'vertices': 7, 'armEdges': [3, 3, 2], 'rootGroupOrder': len(root_group), 'equalsPgl2F5': projected == mobius, 'orderedTripleOrbit': len(triples), 'puzzleComponents': 6, 'statesPerComponent': 840},
        'thetaZeroShortEarCases': ears,
        'mathematicalProof': 'proof.md',
        'scope': 'Finite certificate for bounded cases; general proof is symbolic, not inferred from spot checks.'
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'passed': True, 'identitySpotChecks': word_cases, 'legalThetaLoopCases': legal_word_cases, 'shortEarCases': len(ears), 'thetaZeroGroup': len(root_group), 'exceptionalLongCycleOrders': [20, 60, 1344]}, ensure_ascii=False))


if __name__ == '__main__':
    main()
