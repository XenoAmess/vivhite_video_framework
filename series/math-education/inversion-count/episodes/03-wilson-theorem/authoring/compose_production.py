#!/usr/bin/env python3
"""Compile the complete Wilson proof into the Java maker's proof animation contract.

This adapter owns episode data, not a parallel renderer. Every graph walk and
algebraic permutation is checked before exporting the production plan.
GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

EPISODE = Path(__file__).resolve().parents[1]
ROOT = next(p for p in EPISODE.parents if (p / "video-maker/pom.xml").is_file())
SPEC = importlib.util.spec_from_file_location("wilson_proof", EPISODE / "verify_proof.py")
MATH = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MATH)


def step(text, rows=(), **kwargs):
    return {"text": text, "rows": list(rows), **kwargs}


def circle(names):
    return [{"id": name, "label": display(name),
             "x": round(.5 + .43 * math.cos(2 * math.pi * i / len(names) - math.pi / 2), 5),
             "y": round(.5 + .40 * math.sin(2 * math.pi * i / len(names) - math.pi / 2), 5)}
            for i, name in enumerate(names)]


def display(name):
    if name == "inf":
        return "∞"
    return re.sub(r"([abcdest])(\d+)$", lambda m: m[1] + m[2].translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")), name)


def graph(arms, root=None, extra=()):
    nodes = {}
    for index, arm in enumerate(arms):
        for i, name in enumerate(arm):
            x = .06 + .88 * i / (len(arm) - 1)
            y = .5 if i in (0, len(arm) - 1) else (.10, .88, .5)[index % 3]
            nodes.setdefault(name, {"id": name, "label": display(name), "x": x, "y": y})
    for name, x, y in extra:
        nodes[name] = {"id": name, "label": display(name), "x": x, "y": y}
    edges = list(dict.fromkeys(tuple(sorted(pair)) for arm in arms for pair in zip(arm, arm[1:])))
    result = {"mode": "graph", "nodes": list(nodes.values()), "edges": [list(e) for e in edges]}
    if root:
        result.update(root=root, blank=root)
        symbols = iter("①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳")
        result["initialTokens"] = {name: "0" if name == root else next(symbols) for name in nodes}
    return result


def theta(n=3, m=3, s=1, t=1):
    aa, bb = [f"a{i}" for i in range(1, n + 1)], [f"b{i}" for i in range(1, m + 1)]
    cc, dd = [f"c{i}" for i in range(1, s + 1)], [f"d{i}" for i in range(1, t + 1)]
    arms = [["y"] + aa + ["z"], ["y"] + bb[::-1] + ["z"], ["y"] + cc[::-1] + ["x"] + dd + ["z"]]
    result = graph(arms, "x")
    q, r = ["x"] + cc + ["y"], ["x"] + dd + ["z"]
    pa, pb = ["z"] + aa[::-1] + ["y"], ["y"] + bb[::-1] + ["z"]
    walks = {"pi": q + pb[1:] + pa[1:] + q[::-1][1:],
             "rho": r + pa[1:] + pb[1:] + r[::-1][1:],
             "tau": q + pb[1:] + r[::-1][1:]}
    return result, walks


def theta_zero(extra=()):
    return graph([["inf", "0", "1", "2"], ["inf", "4", "3", "2"], ["inf", "x", "2"]], "x", extra)


def rectangle():
    names = list("abcdef")
    return {"mode": "graph", "nodes": [{"id": name, "label": name, "x": .08 + .42 * (i % 3), "y": .22 + .54 * (i // 3)} for i, name in enumerate(names)],
            "edges": [["a", "b"], ["b", "c"], ["d", "e"], ["e", "f"], ["a", "d"], ["b", "e"], ["c", "f"]],
            "root": "a", "blank": "a", "initialTokens": dict(zip(names, ["0", "①", "②", "③", "④", "⑤"]))}


def perm(names):
    return {"mode": "permutation", "nodes": circle(names), "edges": []}


def table(rows=(), mode="table"):
    return {"mode": mode, "rows": list(rows), "nodes": [], "edges": []}


def cycles_of(labels, item):
    result, seen = [], set()
    for index, image in enumerate(item):
        if index in seen or image == index:
            continue
        cycle, current = [], index
        while current not in seen:
            seen.add(current)
            cycle.append(labels[current])
            current = item[current]
        result.append(cycle)
    return result


def invert_cycles(cycles):
    return [list(reversed(c)) for c in cycles]


def card(text, rows, labels, item, **kwargs):
    return step(text, rows, cycles=cycles_of(labels, item), **kwargs)


def check_graph(proof):
    nodes = [n["id"] for n in proof["nodes"]]
    assert len(nodes) == len(set(nodes))
    edges = {frozenset(e) for e in proof["edges"]}
    blank = proof.get("blank")
    state = dict(proof.get("initialTokens", {n["id"]: n["label"] for n in proof["nodes"]}))
    for item in proof["steps"]:
        assert len(item.get("rows", [])) <= (5 if proof["mode"] in ("graph", "permutation") else 7)
        for row in item.get("rows", []):
            assert len(row) <= (34 if proof["mode"] in ("graph", "permutation") else 68), row
        assert len(item.get("text", "")) <= 50
        edges.update(frozenset(e) for e in item.get("addEdges", []))
        assert not (item.get("walk") and item.get("cycles"))
        if item.get("walk"):
            walk = item["walk"]
            assert walk[0] == blank, (blank, walk)
            for a, b in zip(walk, walk[1:]):
                assert frozenset([a, b]) in edges, (a, b)
                state[a], state[b] = state[b], state[a]
            blank = walk[-1]
        moved = set()
        for cycle in item.get("cycles", []):
            assert len(cycle) >= 2 and len(set(cycle)) == len(cycle)
            assert not moved.intersection(cycle)
            moved.update(cycle)
            values = [state[a] for a in cycle]
            for a, value in zip(cycle[1:] + cycle[:1], values):
                state[a] = value
        assert all(v in nodes for v in item.get("focus", []))
    return state


def read_scenes():
    text = (EPISODE / "director.md").read_text(encoding="utf-8")
    parts = re.split(r"(?m)^## (\d\d)｜([^｜]+)｜([^\n]+)\n", text)
    result = []
    for offset in range(1, len(parts), 4):
        number, timing, heading, body = parts[offset:offset + 4]
        narration = re.search(r"\*\*旁白\*\*：“(.*?)”", body, re.S)[1]
        if number == "19":
            narration += "是这个点。接上。"
        if number == "01":
            narration = "法阵展开。今天把判别器的最后一组零件装上。" + narration
        if number == "07":
            narration = "把三角卡召来。" + narration
        if number == "18":
            narration = narration.replace("执行完，", "先看去路借过的牌，又沿逆路回到原处。一个动作卡走完，才接下一张；负一次就是把刚才那整圈倒着走。不要只盯住三块亮牌，其他位置也要对照初态，确认没有额外的交换留在图上。执行完，")
        for before, after in (("Wilson", "威尔逊"), ("theta", "西塔"),
                              ("pi", "派"), ("rho", "柔"), ("tau", "陶"),
                              ("PGL 二，五", "P、G、L，二，五")):
            narration = narration.replace(before, after)
        # All formulas remain on screen, while narration uses speakable Chinese.
        times = re.split("—", timing)
        seconds = lambda value: sum(int(p) * (60 ** i) for i, p in enumerate(reversed(value.split(":"))))
        result.append({"sceneId": f"s{number}", "heading": heading, "narration": narration,
                       "budget": seconds(times[1]) - seconds(times[0])})
    assert len(result) == 38
    return result


def join_walks(walks):
    result = list(walks[0])
    for walk in walks[1:]:
        assert result[-1] == walk[0]
        result.extend(walk[1:])
    return result


def visuals():
    result = {}
    def add(n, proof, steps, formula="", reaction=""):
        proof["steps"] = steps
        check_graph(proof)
        result[n] = {"proof": proof, "formula": formula, "reaction": reaction}

    p = theta_zero()
    add(1, p, [step("同一个规则：空格与邻点交换", ["有限图上的滑块", "圆环：保留循环次序", "普通图：1类或2类", "七点图：六类？", "三臂边长3、3、2"], focus=["x"]),
        step("沿短臂与上臂，先走一个合法圈", ["规则没有变化", "只有空格相邻的牌能滑入"], walk=["x", "inf", "0", "1", "2", "x"]),
        step("逆向撤回，七个位置全部保留", ["不是六边形加一条边", "短臂内部还有空格x"], walk=["x", "2", "1", "0", "inf", "x"])], "从矩形出发：有限简单二连通图")
    add(2, theta_zero(), [step("有限、简单、互异标号、唯一空格", ["无自环、无重边", "q≥3；数字彼此不同", "2连通：删任一点仍连通"], focus=["x"]),
        step("删去x时，两条长臂仍连接", ["剩余路径：∞–0–1–2", "另一长臂：∞–4–3–2", "删x后剩余图连通"], focus=["inf", "0", "1", "2", "3", "4"]),
        step("删去分支点∞时，仍能经2相接", ["0–1–2–3–4", "x–2接入同一部分", "割点图不能套用本定理"], focus=["0", "1", "2", "3", "4", "x"])], "每个被删除的点，都必须能绕开")
    p, w = theta(2, 1, 0, 0)
    add(3, p, [step("根在x，出门后必须回根", ["根群 ΓG(x)", "闭路卡可以串接与撤回"], focus=["x"]),
        step("第一张卡：合法闭路", ["位置置换只记录最终牌的位置"], walk=w["pi"]),
        step("逆路撤回，整张卡作废", ["空动作是单位元", "正向卡·逆向卡=单位元"], walk=w["pi"][::-1]),
        step("所有动作队列从左到右执行", ["v(αβ)=(vα)β", "(ab)(ac)=(abc)", "a→b→c→a"], focus=["a1", "y", "z"])], "动作顺序：左边先做，右边后做")
    p, w = theta(2, 1, 0, 0)
    add(4, p, [step("沿x→y换根，再沿逆路返回", ["ΓG(x)与ΓG(y)共轭", "换根不改变群的大小"], walk=["x", "y", "x"]),
        step("互异牌：不同置换给出不同状态", ["空格固定：共(q−1)!种", "每个分量恰含|ΓG(x)|种根状态"]),
        step("每个分量都有一个固定根状态", ["分量数=(q−1)! / |ΓG(x)|", "只要把空格沿路径搬回x"], walk=w["rho"])], "分量数 = (q−1)! ÷ |ΓG(x)|")
    add(5, theta_zero(), [step("二染色时：空格回根必走偶数步", ["一步对换使全部标号奇偶翻转", "二分图闭路只有偶数步", "所以Γ⊆A"]),
        step("两条异奇偶根路径会拼成奇闭路", ["根路径奇偶定义两色", "若奇偶不唯一，就产生奇闭路", "无奇闭路 ⇒ 二分图"]),
        step("七点图有五步奇闭路", ["x–2–1–0–∞–x", "奇闭路诱导奇置换", "但有奇置换还不保证全部可达"], walk=["x", "2", "1", "0", "inf", "x"])], "还要证明：非例外图含全部偶置换")
    names = list("abcd")
    add(6, perm(names), [step("代数层：先执行两次不相交对换", ["(ab)(cd)"], cycles=[["a", "b"], ["c", "d"]]),
        step("撤回，改走三轮换分解", ["比较同一组互异标号"], cycles=[["a", "b"], ["c", "d"]]),
        step("第一张三角卡", ["(abc)：a→b→c→a"], cycles=[["a", "b", "c"]]),
        step("第二张三角卡", ["(adc)：a→d→c→a", "合成结果仍为(ab)(cd)"], cycles=[["a", "d", "c"]]),
        step("偶数张对换两两配对", ["相同：抵消", "共享一点：一个三轮换", "不相交：两个三轮换", "所以A由三轮换生成"])], "(ab)(cd) = (abc)(adc)")
    add(7, perm(list("abcdef")), [step("旧区S中已有全部偶置换", ["旧点a、b；新点c", "先按h搬运一对旧支点"], focus=["a", "b", "d", "e", "f"]),
        step("先做h的逆", ["例h=(ade)，固定b、c", "队列：h⁻¹→α→h"], cycles=[["a", "e", "d"]]),
        step("原三角卡α", ["α=(abc)"], cycles=[["a", "b", "c"]]),
        step("再做h，支点变为d、b、c", ["h⁻¹αh=(dbc)", "接线h固定新点c", "旧支点按h迁移"], cycles=[["a", "d", "e"]]),
        step("无序旧点对总能用偶置换搬运", ["任取双射；若奇就交换输出对", "无序对不变，奇偶翻转", "方向不合：取三角卡的逆", "S∪{c}上全部偶置换可做"])], "两个旧点接一个新点：共轭三角卡")
    add(8, perm(list("abcde")), [step("α搭一个旧点a，b、c在外面", ["旧区还有d、e", "α=(abc)，β=(dbc)"], focus=["a", "d", "e"]),
        step("先执行α", ["位置作用从左到右"], cycles=[["a", "b", "c"]]),
        step("再执行β的逆，b恢复", ["αβ⁻¹=(adc)", "只动a、d、c"], cycles=[["d", "c", "b"]]),
        step("a、d为旧点，先接入c", ["再用原α接入b", "只需共享一点就能接力", "每张卡为偶，故生成群恰为A"], focus=["a", "d", "c", "b"])], "(abc)(dbc)⁻¹ = (adc)")
    add(9, perm(list("abcde")), [step("二重传递：指定两个不同点的像", ["K内全部三轮换生成H", "共轭仍是三轮换，所以H◁K"], focus=["a", "b"]),
        step("H的轨道被K整块搬运", ["轨道块要么相等，要么不交", "假设一块含a、b却缺c"], focus=["a", "b"]),
        step("固定a，把b送到c", ["像块与原块在a相交", "却含c而原块不含c：矛盾"], cycles=[["b", "c"]], focus=["a", "c"]),
        step("非平凡轨道只能有一块", ["三角卡使轨道不是全为单点", "H传递 ⇒ 三角卡连通", "三角接力给出H=A⊆K"])], "二重传递 + 一张三轮换 ⇒ 全部偶置换")
    p, w = theta()
    add(10, p, [step("三臂内部不相交，根在第三臂", ["A₁：y–a₁–…–aₙ–z", "A₃：y–bₘ–…–b₁–z", "A₂：y–cₛ–…–x–…–dₜ–z"], focus=["x", "y", "z"]),
        step("参数数内部点，不数边", ["n≥m≥0，n≥1", "臂内部2点，就有3条边", "θ(2,2,1)的边长是3,3,2"]),
        step("同一图上的第一次合法绕行", ["接下来固定这些位置记号"], walk=w["pi"])], "theta = 两端点之间三条内部不交路径")
    p, w = theta()
    add(11, p, [step("从x到y，经b臂到z，沿a臂回来", ["π=(a₁…aₙ z b₁…bₘ)", "去路与逆回路的牌恢复"], walk=w["pi"]),
        step("先逆向撤回π，再单独看ρ", ["每张卡从相同初态检验"], walk=w["pi"][::-1]),
        step("从x到z，沿a到y，经b返回", ["ρ=(b₁…bₘ y a₁…aₙ)", "π固定y；ρ固定z"], walk=w["rho"])], "两个错开一个固定点的长循环")
    names, pi, rho = MATH.long_cycles(3, 3)
    add(12, perm(names), [card("ρ固定z，循环其余所有点", ["固定z的稳定子已传递其余点"], names, rho, focus=["z"]),
        card("π把z送入可活动的区域", ["ρ与π生成的群在X上传递"], names, pi),
        step("先对齐第一点，再固定它调第二点", ["传递+单点稳定子传递", "⇒ 二重传递", "只需再造一张三轮换"])], "ρ固定z、π移动z ⇒ 二重传递")
    # The displayed identities are symbolic. The animated disc uses n=m=3.
    labels, pi, rho = MATH.long_cycles(3, 3)
    mul, inv, power = MATH.multiply, MATH.inverse, MATH.power
    s1 = mul(inv(pi), rho)
    sigmas = [s1]
    sigmas += [mul(inv(pi), sigmas[-1], pi)]
    sigmas += [mul(inv(pi), sigmas[-1], pi)]
    sigmas += [mul(power(rho, 3), s1, power(rho, -3))]
    sigmas += [mul(sigmas[3], sigmas[1])]
    sigmas += [mul(inv(pi), sigmas[4], pi)]
    sigmas += [mul(power(rho, 2), s1, power(rho, -2))]
    sigmas += [mul(sigmas[2], sigmas[6])]
    sigmas += [mul(sigmas[5], sigmas[7])]
    definitions = ["σ₁=π⁻¹ρ", "σ₂=π⁻¹σ₁π", "σ₃=π⁻¹σ₂π", "σ₄=ρᵐσ₁ρ⁻ᵐ", "σ₅=σ₄σ₂", "σ₆=π⁻¹σ₅π", "σ₇=ρ^(m−1)σ₁ρ^(1−m)", "σ₈=σ₃σ₇", "σ₉=σ₆σ₈"]
    effects = ["(y a₁)(z b₁)", "(y a₂)(b₁ b₂)", "(y a₃)(b₂ b₃)", "(b₁ b₂)(z aₖ₊₁)", "(y a₂)(z aₖ₊₁)", "(y a₃)(b₁ aₖ₊₂)", "(b₂ b₃)(z aₖ₊₂)", "(y a₃)(z aₖ₊₂)", "(z aₖ₊₂ b₁)"]
    for scene, indices in [(13, range(4)), (14, range(4, 9))]:
        steps = [step("符号式证明任意参数，转盘示例n=m=3", ["仅限n=m或n=2m，m≥3", "k=n−m，k=0或k≥3"])]
        for index in indices:
            steps += [card(f"第{index + 1}行：逐个追踪支点", [definitions[index], "= " + effects[index], "转盘取k=0；通式保留k"], labels, sigmas[index]),
                      card("撤回此卡，下一行单独核验", [definitions[index], "= " + effects[index]], labels, inv(sigmas[index]))]
        steps += [step("共有对换抵消，末行三个点互异", ["0≤k≤n−3；涉及下标均存在", "k=1不属于本路线", "另一族改走τ恒等式"])]
        add(scene, perm(labels), steps, "σ₉ = (z aₖ₊₂ b₁)  ｜  任意长的两族")
    labels, pi, rho = MATH.long_cycles(5, 2)
    t1 = mul(inv(pi), rho)
    t2, t3 = mul(power(rho, -2), t1, power(rho, 2)), mul(power(pi, -4), t1, power(pi, 4))
    c = labels[power(pi, 4)[labels.index("a1")]]
    add(15, perm(labels), [step("n>m且n≠2m；这里示例n=5,m=2", ["m=0：π⁻¹ρ=(a₁ z y)", "以下m>0"]),
        card("τ₂：按ρ搬运双对换", ["τ₁=π⁻¹ρ=(y a₁)(z b₁)", "τ₂=ρ⁻ᵐτ₁ρᵐ", "=(aₘ aₘ₊₁)(z y)"], labels, t2),
        card("再做τ₃，共有那一对抵消", ["τ₃=π⁻²ᵐτ₁π²ᵐ", "=(y c)(aₘ aₘ₊₁)", "c=a₁π²ᵐ；τ₂τ₃=(y z c)"], labels, t3),
        step("把a₁的位置记作0，c位于2m", ["循环长度n+m+1", "0<2m<n+m+1，不绕回", "2m≠m−1、m", "2m=n恰是排除的n=2m", "π固定y，c永不等于y"], focus=["y", "z", c])], "碰撞检查完成，三支点互不相同")
    add(16, table(), [step("参数域n≥m≥0，n≥1", ["n=m,m≥3：σ九行路线", "n=2m,m≥3：σ九行路线", "n>m,n≠2m：τ三行路线", "m=0,n≥1：直接三轮换", "n=m=1：π本身是三轮换"]),
        step("无限参数域分区，不是有限枚举", ["只剩(2,1)、(2,2)、(4,2)", "这是双长循环的缺口", "完整theta还有第三张合法卡", "先把普通臂接通，再修缺口"])], "仅余三对参数，第三条臂尚未使用")
    p, w = theta(3, 1, 1, 1)
    add(17, p, [step("A₁与A₃上已有全部偶置换", ["取一张(a₁ y z)三角卡", "第三张卡τ不经过a₁"], focus=["a1", "y", "z"]),
        step("第三条根闭路生成τ", ["τ=(d₁…dₜ z b₁…bₘ y cₛ…c₁)", "根x恢复，a₁固定"], walk=w["tau"]),
        step("τ共轭搬运：卡总挂在a₁", ["第三臂全部非根位置被覆盖", "三角卡共享a₁，接力连通"], focus=["a1", "d1", "c1"]),
        step("哪些三臂不能换选一对好参数？", ["有0就配0，立即走好路线", "坏无序对仅{1,2},{2,2},{2,4}", "三臂全坏仅{1,2,2}", "或{2,2,2}、{2,2,4}"])], "普通theta：三角卡覆盖每个非根位置")
    for scene, n in [(18, 2), (19, 4)]:
        p, walks = theta(n, 2, 1, 0)
        words = [("pi", 2), ("rho", 1), ("pi", 2), ("tau", 1), ("pi", -1), ("rho", 1), ("tau", -1)] if n == 2 else [("rho", 1), ("pi", -1), ("tau", -2), ("pi", -1), ("rho", 1), ("tau", 2)]
        steps = [step("每张长循环卡都由合法根闭路实现", ["根臂：y–c₁–x–z", "下列队列从左到右执行"])]
        for name, exponent in words:
            route = walks[name] if exponent > 0 else walks[name][::-1]
            walk = route + sum([route[1:] for _ in range(abs(exponent) - 1)], [])
            steps.append(step(f"执行{dict(pi='π', rho='ρ', tau='τ')[name]}的{exponent}次", ["π、ρ、τ均是先前的合法闭路", "跟踪所有牌，根x保持复原"], walk=walk))
        seed_walk = join_walks([steps[i]["walk"] for i in range(1, len(steps))])
        labels = [node["id"] for node in p["nodes"]]
        seed = MATH.walk_permutation(labels, seed_walk)
        expected = MATH.cycle(labels, "z", "y", "c1") if n == 2 else MATH.cycle(labels, "z", "a4", "a1")
        assert seed == expected
        if n == 2:
            steps += [step("只剩z、y、c₁三点轮换", ["π²ρπ²τπ⁻¹ρτ⁻¹=(z y c₁)", "π共轭：y、c₁固定", "第三角扫过五个点，覆盖全部"], focus=["z", "y", "c1"])]
        else:
            steps += [step("得到(z a₄ a₁)，ρ搬运先铺七点", ["ρπ⁻¹τ⁻²π⁻¹ρτ²=(z a₄ a₁)", "ρ固定z，循环其余七个旧点"], focus=["z", "a4", "a1"]),
                      step("先撤回种子卡，再演示完整共轭", ["不能只在种子卡后接τ⁴", "必须τ⁻⁴→种子卡→τ⁴"], walk=seed_walk[::-1])]
            tau_four = walks["tau"] + walks["tau"][1:] * 3
            conjugate = join_walks([tau_four[::-1], seed_walk, tau_four])
            conjugate_permutation = MATH.walk_permutation(labels, conjugate)
            assert {labels[i] for i in MATH.support(conjugate_permutation)} == {"c1", "a4", "a1"}
            steps += [step("τ⁴共轭把支点z搬到c₁", ["新卡支点{c₁,a₄,a₁}", "所有三角卡仍连成一片", "是这个点。接上。"], walk=conjugate, focus=["c1", "a4", "a1"])]
        add(scene, p, steps, "θ(2,2,2)与θ(4,2,2)都不是最终例外")
    base = [["x", "a", "y"], ["x", "b", "y"], ["x", "c", "y"]]
    p = graph(base, "x", [("e1", .30, .28), ("e2", .70, .28)])
    add(20, p, [step("新点先在图外待命", ["旧图H二连通", "耳端点x、y不同且在H内", "内部e₁、e₂全在H外"]),
        step("接上新耳x–e₁–e₂–y", ["新耳内部不准使用旧点", "新增边后仍二连通"], addEdges=[["x", "e1"], ["e1", "e2"], ["e2", "y"]], focus=["e1", "e2"]),
        step("删新内部点：两截仍分别接旧图", ["删e₁：e₂仍经y接H", "删x：耳仍经y接H", "删其他旧点：H余下仍连通"]),
        step("没有内部点的耳，就是一条新弦", ["不能重复已有边", "两种耳都保持二连通"])], "加耳只增加路径，且保持定理前提")
    p = graph([["x", "a", "y"], ["x", "b", "y"]], "x", [("e1", .30, .27), ("e2", .70, .27), ("f", .5, .68)])
    add(21, p, [step("最长简单路的末端邻点均已在路上", ["最小度≥2，所以有另一邻点", "该邻点闭出第一个环"]),
        step("外部分量至少有两个不同附着点", ["若仅一个，删它就断开", "这会违反目标图的2连通性"], focus=["x", "y"]),
        step("取穿过外部分量的简单路径", ["加入第一耳：环变成theta", "新增至少一条边"], addEdges=[["x", "e1"], ["e1", "e2"], ["e2", "y"]]),
        step("继续加耳直到没有外部点", ["从任何2连通H都可继续", "每步至少加入一条目标边"], addEdges=[["a", "f"], ["f", "b"]]),
        step("最后补缺边，有限终止", ["有限量：尚缺目标边数", "严格下降，不能无限施工"], addEdges=[["a", "b"]])], "环 → 第一耳给theta → 有限次耳扩张")
    add(22, theta_zero(), [step("若目标就是θ₀，留待精确计算", ["若目标更大，则还能加一耳", "不能凭图变大断言缺口消失"]),
        step("F交换两条长臂", ["F=(0 4)(1 3)", "无序端点对被整体搬运"], focus=["0", "4", "1", "3"]),
        step("R同时反转三条臂", ["R=(∞ 2)(0 1)(4 3)", "二者及FR不改变旧图"], focus=["inf", "2"]),
        step("21个端点对恰分成八类", ["类别数：2+4+2+2+4+4+1+2", "总计21，无重复无遗漏", "新耳长L仍是任意正整数"])], "八类端点 × 任意耳长L")
    pairs = [("0,1", "3,4", "0–1", "0–∞–4–3–2–1", "1,5,L"),
             ("0,2", "1,∞;2,4;3,∞", "0–1–2", "0–∞–4–3–2", "2,4,L"),
             ("0,3", "1,4", "0–1–2–3", "0–∞–4–3", "3,3,L"),
             ("0,4", "1,3", "0–1–2–3–4", "0–∞–4", "4,2,L"),
             ("0,∞", "1,2;2,3;4,∞", "0–∞", "0–1–2–3–4–∞", "1,5,L"),
             ("0,x", "1,x;3,x;4,x", "0–1–2–x", "0–∞–x", "3,2,L"),
             ("2,∞", "无", "2–1–0–∞", "2–3–4–∞", "3,3,L"),
             ("2,x", "∞,x", "2–x", "2–1–0–∞–x", "1,4,L")]
    steps = []
    for ends, same, path1, path2, lengths in pairs:
        steps.append(step(f"代表端点{ends}；新耳E长L", ["同类：" + same, "旧路一：" + path1, "旧路二：" + path2, "三臂边长：" + lengths, "例外恰须{2,3,3}"], focus=["inf" if v == "∞" else v for v in ends.split(",")]))
    steps += [step("只剩三格需要改路", ["0,3且L=2；0,x且L=3", "2,∞且L=2", "长度1且已有边时，不允许重复", "其余所有正整数L已排除例外"])]
    add(23, theta_zero(), steps, "八类完整旧路径表：可逐边暂停核对")
    p = theta_zero([("e", .25, .32), ("f", .55, .32), ("g", .82, .32)])
    add(24, p, [step("第一格：0到3，耳长2", ["改分支点为0、∞", "0–∞；0–1–2–x–∞", "0–e–3–4–∞", "内部{},{1,2,x},{e,3,4}", "边长1,4,4"], addEdges=[["0", "e"], ["e", "3"]], focus=["0", "inf"]),
        step("第二格：0到x，耳长3", ["改分支点为0、2", "0–1–2；0–∞–4–3–2", "0–f–g–x–2", "内部{1},{∞,4,3},{f,g,x}", "边长2,4,4"], addEdges=[["0", "f"], ["f", "g"], ["g", "x"]], focus=["0", "2"]),
        step("第三格：2到∞，耳长2", ["旧路2–1–0–∞", "旧路2–x–∞；新耳2–e–∞", "内部{1,0},{x},{e}", "边长3,2,2", "三例内部不交，且全避开{2,3,3}"], addEdges=[["2", "e"], ["e", "inf"]], focus=["2", "inf"]),
        step("八类参数表加三次改路，穷尽所有耳", ["分支点可以改选", "没有把有限试验当作任意耳长证明"])], "θ₀加任何允许新耳，必含普通theta")
    add(25, table(), [step("好底盘已有A，再用奇偶给等号", ["非二分H：Γ=Sᵣ，r≥3", "二分非环H：Γ=Aᵣ，r≥4", "这里r=|V(H)|−1"]),
        step("为什么规模下限足够", ["简单二连通非环图至少4点", "4点二分二连通图只能是四环", "故二分非环图至少5点"]),
        step("指定两点像后，修正剩余奇偶", ["r≥4时还有另外两输出点可交换", "不改指定两点像，却能翻转奇偶", "所以Aᵣ也二重传递", "A₃并不是二重传递，本处未使用它"])], "最小规模已检查：旧群确实二重传递")
    p = graph([["x", "z", "y"], ["x", "a", "y"], ["x", "b", "y"]], "x", [("e1", .3, .28), ("e2", .7, .28)])
    add(26, p, [step("另选旧点z，与耳端点x、y不同", ["H−z连通", "取避开z的旧路Q：y–a–x"], focus=["z"]),
        step("新耳出去，经旧路Q返回", ["空格闭路x–e₁–e₂–y–a–x", "循环含所有新点，却固定z"], addEdges=[["x", "e1"], ["e1", "e2"], ["e2", "y"]], walk=["x", "e1", "e2", "y", "a", "x"]),
        step("固定z，旧稳定子已传递旧非根点", ["旧轨道含y；循环幂纳入每个新点", "所以Γ新,z传递其余非根位置"], walk=["x", "e1", "e2", "y", "a", "x"], focus=["y", "e1", "e2"]),
        step("旧群还能把z送到y", ["全体传递+固定z后传递", "⇒ 新根群二重传递", "旧图提供一张三轮换", "自动开关给出全部偶置换"])], "新耳的每个新点，都进入同一轨道")
    p, _ = theta(2, 1, 0, 0)
    add(27, p, [step("长度1的耳：没有新顶点", ["旧根群已在全部相同位置含A", "无需重做轨道扩张", "这里是普通theta，非七点例外"]),
        step("仍二分：奇置换不能进来", ["A⊆Γ⊆A，所以Γ=A"]),
        step("产生奇闭路：另一半也补齐", ["Γ含全部偶置换与一个奇置换", "奇×偶覆盖全部奇置换", "所以Γ=S"], walk=["x", "y", "a1", "a2", "z", "x"]),
        step("按耳存在性有限扩张到目标图", ["好theta→逐耳保留A", "每步用奇偶得到完整根群", "现在只剩θ₀与环需要计数"])], "普通图主体证明完成：每一耳都保留A")
    add(28, theta_zero(), [step("p：x∞43210∞x，∞经过两次", ["逐边交换，不跳过重复顶点", "T=(0 1 2 3 4)"], walk=["x", "inf", "4", "3", "2", "1", "0", "inf", "x"]),
        step("先逆p撤回，再独立核对q", ["对同一初态比较两张卡"], walk=["x", "inf", "0", "1", "2", "3", "4", "inf", "x"]),
        step("q：x210∞x", ["Q=(∞ 0 1 2)", "已有奇置换，但未必全部可达"], walk=["x", "2", "1", "0", "inf", "x"])], "T与Q是两条真实合法闭路的最终作用")
    add(29, theta_zero(), [step("选生成树，剩余恰为两条弦", ["树：x∞、∞0、01、12、23、34", "弦：∞4、x2"], focus=["x", "inf", "0", "1", "2", "3", "4"]),
        step("树路往返不改动作", ["每次跨弦，插入树路去回", "同一交换连做两次抵掉"], walk=["x", "inf", "0", "1", "0", "inf", "x"]),
        step("长闭路被拆成一张张基本卡", ["树内闭路删立即折返，最终为空", "故所有根闭路由p、q及逆生成"], walk=["x", "2", "1", "0", "inf", "x"]),
        step("不是只求出一个小子群", ["Γ=〈T,Q〉，没有漏掉其他闭路", "下一步精确求它的上、下界"])], "生成树 + 两条弦 ⇒ Γ = 〈T,Q〉")
    add(30, table(mode="matrix"), [step("模5运算，再添一个位置∞", ["F₅={0,1,2,3,4}", "4+1=0；2×3=1", "非零数均可除"]),
        step("可逆矩阵诱导分式变换", ["M = [ a  b ; c  d ]，ad−bc≠0", "z ↦ (az+b)/(cz+d)", "分母为0→∞；∞→a/c", "c=0时∞→∞；M与λM同作用", "矩阵乘法/逆矩阵给合成/逆变换"]),
        step("T逐点计算：加一", ["T=[1 1;0 1]，T(z)=z+1", "0→1→2→3→4→0，∞固定"]),
        step("Q逐点计算：分母为0去∞", ["Q=[0 3;1 3]，Q(z)=3/(z+3)", "∞→0；0→1；1→2；2→∞", "3→3；4→4", "Γ=〈T,Q〉⊆PGL₂(F₅)"])], "合法卡与分式变换逐点一致")
    add(31, table(mode="matrix"), [step("第一列非零：25−1=24种", ["M=[a b;c d]，det M≠0", "第一列(a,c)不能是(0,0)", "第二列排除第一列的5个倍数", "于是可逆矩阵24×20=480个"]),
        step("每四个非零标量倍数作用相同", ["λ∈{1,2,3,4}：M与λM同作用", "候选变换数480/4=120"]),
        step("固定∞、0、1只可能是标量矩阵", ["固定∞ ⇒ c=0", "再固定0 ⇒ b=0", "再固定1 ⇒ a=d", "所以没有其他作用重合", "|PGL₂(F₅)|=120，|Γ|≤120"])], "24 × 20 ÷ 4 = 120（确无额外重复）")
    add(32, table(mode="matrix"), [step("动作队列T⁻³→Q，得到自逆R", ["Q(z−3)=3/z，R=[0 3;1 0]", "R(R(z))=z"]),
        step("动作队列R→Tᵏ→R，逐式化简", ["z → 3/z → 3/z+k → 3/(3/z+k)", "=3z/(3+kz)=z/(1+2kz)", "因为3⁻¹=2（模5）"]),
        step("k遍历模5，2k也遍历模5", ["k：  0  1  2  3  4", "2k： 0  2  4  1  3", "U(t)=[1 t;0 1]：直接由Tᵗ得到", "L(t)=[1 0;t 1]：由R Tᵏ R得到", "t∈F₅，所有参数都已可执行"]),
        step("矩阵乘法另用通常顺序", ["动作队列左到右；矩阵左乘右作用", "不可把队列排版直接当矩阵乘积"])], "全部上、下三角初等矩阵已从T、Q造出")
    add(33, table(mode="matrix"), [step("任意det=1矩阵，先保证a≠0", ["M=[a b;c d]，ad−bc=1", "若a=0，则c≠0，先左乘U(1)", "这就是第二行加到第一行"]),
        step("左乘L(−c/a)，消掉左下角", ["L(−c/a)M=[a b;0 a⁻¹]", "再左乘U(−ab)，消掉右上角", "得到diag(a,a⁻¹)"]),
        step("对角矩阵也由现有三张卡生成", ["W(a)=U(a)L(−a⁻¹)U(a)", "=[0 a;−a⁻¹ 0]", "W(−1)=[0 −1;1 0]", "W(a)W(−1)=[a 0;0 a⁻¹]"]),
        step("所有消元步骤可逆，反过来造出M", ["因此〈U(t),L(t)〉=SL₂(F₅)", "行列式平方那一半的射影作用", "已经全部生成，不引用群论黑箱"])], "消元 + W(a)因子：生成全部det=1矩阵")
    add(34, table(mode="matrix"), [step("模5非零平方只有1、4", ["非平方是2、3", "det(λM)=λ²det M", "故平方/非平方类别与代表无关"]),
        step("平方行列式可缩放为1", ["det M=s²时，det(s⁻¹M)=1", "这一类已由U、L全部生成"]),
        step("R的行列式为非平方2", ["det[0 3;1 0]=−3=2", "乘R把平方类与非平方类互换", "已有的一半乘R，补齐另一半"]),
        step("上下界相合，精确得到120", ["Γ=PGL₂(F₅)，|Γ|=120", "分量数6!/120=720/120=6", "每分量7×120=840个状态", "总计7!=5040个状态"])], "七点例外：有奇闭路，仍然恰有六类")
    names = ["x", "a", "b", "c", "d"]
    p = {"mode": "graph", "nodes": circle(names), "edges": [[names[i], names[(i + 1) % 5]] for i in range(5)], "root": "x", "blank": "x", "initialTokens": {"x": "0", "a": "①", "b": "②", "c": "③", "d": "④"}}
    add(35, p, [step("环上先删立即折返", ["同一个交换连做两次等于单位元"], walk=["x", "a", "x"]),
        step("删完后只能持续同一方向", ["每个顶点只有两个邻点", "无折返就不能中途掉头"], walk=["x", "a", "b", "c", "d", "x"]),
        step("一整圈让其余q−1块循环一次", ["Γ(Cq)=C(q−1)", "阶为q−1，保留沿环循环次序"], walk=["x", "a", "b", "c", "d", "x"]),
        step("五环实际得到六类", ["分量=(q−1)!/(q−1)=(q−2)!", "q=5：3!=6", "C₃、C₄同样按此公式"])], "单环的限制是循环次序，不只是奇偶")
    add(36, table(), [step("完整可达判定，四种入口", ["普通二分：Γ=A(q−1)，两类", "普通非二分：Γ=S(q−1)，一类", "环Cq：Γ=C(q−1)，(q−2)!类", "七点θ₀：Γ=PGL₂(F₅)，六类"]),
        step("普通二分：先算完整不变量", ["ε：包含空格的全部标号奇偶", "χ：空格顶点的二染色", "I=ε+χ(blank) mod 2", "一步两者同时翻转，所以I不变"]),
        step("同标记为何真的足够", ["沿路径把两状态的空格对齐", "剩余相对置换必为偶", "根群已有全部偶置换，所以可达", "异标记则绝不相通"]),
        step("其他入口也具备充分性", ["普通非二分：任意剩余置换可做", "环：比较沿环循环次序", "θ₀：比较相对置换是否在120卡中"])], "必要性与充分性都已接回具体局面")
    p = rectangle()
    add(37, p, [step("完整矩形，两维都至少为2", ["m,n≥2：二分、2连通", "除2×2外，都不是单环"], walk=["a", "b", "e", "d", "a"]),
        step("2×2虽为四环，仍恰有两类", ["C₃=A₃；根群阶3", "分量3!/3=2"]),
        step("第二期格子接力，第三期图上接力", ["两种证明得到同一矩形结论", "环保留次序，θ₀只允许120动作", "其余图把三角卡传遍全图"], walk=["a", "b", "c", "f", "e", "b", "a"])], "判别器完成：矩形与一般图接成同一套工具", "判别器，这次装完了。")
    add(38, table(), [step("Wilson · Graph Puzzles · 1974", ["有限、简单、2连通；q≥3", "环Cq：(q−2)!类", "七点θ₀边长3,3,2：六类", "其余二分图两类，非二分图一类"]),
        step("证明、完整公式与校验程序随工程保留", ["vivhite_video_framework · GPL-3.0-only", "数学教育／逆序数／第三期", "原创Java图形；晓晓配音；图片占位", "完整证明：proof.md；程序：verify_proof.py"])], "从合法滑动出发，逐步接出完整分类")
    assert sorted(result) == list(range(1, 39))
    return result


def build(voice="zh-CN-XiaoxiaoNeural", rate="+8%", codec="h264_nvenc"):
    pictures = visuals()
    beats = []
    for scene in read_scenes():
        number = int(scene["sceneId"][1:])
        item = pictures[number]
        beat = {"id": f"w{number:02d}", "sceneId": scene["sceneId"],
                "seriesLabel": "逆序数 · Wilson定理", "chapter": f"第三期  ·  第{number:02d}场 / 38",
                "heading": scene["heading"], "narration": scene["narration"], "view": "proof",
                "action": "逐步执行本场proof.steps；路径沿实边交换牌，代数卡另标作用层；保留完整公式与条件。",
                "minDurationSeconds": scene["budget"], "tailSeconds": 8,
                "formula": item["formula"], "note": "动作队列从左到右；矩阵乘法采用通常顺序。",
                "reaction": item["reaction"], "proof": item["proof"]}
        assert len(beat["narration"]) <= 600
        if number == 1:
            # These are distinct puzzles, not a fictitious legal move across tile sets.
            opening = [
                ("a", "法阵展开。今天把判别器的最后一组零件装上。把格子之间能滑动的地方画成线，棋盘就变成了一张图。这个二乘三棋盘一共六个位置，放五块数字和一个空格。", rectangle(),
                 [step("六个位置，五块数字，一个空格", ["原来的完整2×3矩形", "画边只是记录哪些位置相邻"], walk=["a", "b", "e", "d", "a"])]),
                ("b", "再换成五个位置的圆环。它放四块数字和一个空格。移动规则没变，只有挨着空格的数字能滑进去。注意，我们换了图和牌数，没有把两张不同的棋盘冒充成同一局滑动。", None, None),
                ("c", "最后拿出这张七点图，六块数字，加一个空格。原来分成两类的世界，可以变成一类，也可以变成六类。今天把这个判别器继续装完，直到能看着一张图，说清楚它的全部局面分成几块。这张七点图先留在这里，它会是唯一一块有点挑剔的零件。", item["proof"], item["proof"]["steps"])]
            ring_names = ["x", "a", "b", "c", "d"]
            ring = {"mode": "graph", "nodes": circle(ring_names), "edges": [[ring_names[i], ring_names[(i + 1) % 5]] for i in range(5)], "root": "x", "blank": "x", "initialTokens": {"x": "0", "a": "①", "b": "②", "c": "③", "d": "④"}}
            opening[1] = (*opening[1][:2], ring, [step("五个位置，四块数字，一个空格", ["不同图用对应的牌集", "同一条规则：空格只与邻点换位"], walk=["x", "a", "b", "c", "d", "x"])])
            for suffix, narration, proof, steps in opening:
                part = {**beat, "id": "w01" + suffix, "narration": narration, "minDurationSeconds": scene["budget"] / 3, "tailSeconds": 3}
                part["proof"] = {**proof, "steps": steps}
                check_graph(part["proof"])
                beats.append(part)
        elif number == 24:
            # Each case starts with a fresh theta_0. Ears from different cases must
            # never accumulate on screen and suggest a different hypothesis.
            narration = beat["narration"]
            fragments = re.split(r"(?=第二个，|第三个，)", narration)
            assert len(fragments) == 3
            cases = [
                ([("e", .42, .31)], [["0", "e"], ["e", "3"]], ["0", "inf"], ["分支点0、∞", "0–∞；0–1–2–x–∞", "0–e–3–4–∞", "内部{},{1,2,x},{e,3,4}", "边长1,4,4"]),
                ([("f", .42, .31), ("g", .62, .35)], [["0", "f"], ["f", "g"], ["g", "x"]], ["0", "2"], ["分支点0、2", "0–1–2；0–∞–4–3–2", "0–f–g–x–2", "内部{1},{∞,4,3},{f,g,x}", "边长2,4,4"]),
                ([("e", .53, .70)], [["2", "e"], ["e", "inf"]], ["2", "inf"], ["分支点2、∞", "2–1–0–∞；2–x–∞", "新耳2–e–∞", "内部{1,0},{x},{e}", "边长3,2,2"])]
            for i, (extra, edges, focus, rows) in enumerate(cases):
                proof = theta_zero(extra)
                proof["steps"] = [step("本例从原七点图独立开始", ["新点在图外；没有其他新耳"]),
                                  step("只接本例的新耳", rows, addEdges=edges, focus=focus),
                                  step("逐个内部集合核对：两两不交", rows, focus=focus),
                                  step("边长不等于{2,3,3}，所以是好theta", rows[-2:])]
                part = {**beat, "id": "w24" + "abc"[i], "narration": fragments[i], "proof": proof,
                        "minDurationSeconds": scene["budget"] / 3, "tailSeconds": 4}
                check_graph(proof)
                beats.append(part)
        elif number == 19:
            # A full legal conjugate has 116 edge swaps. Give it its own spoken
            # demonstration instead of rushing it through the original 80s slot.
            seed_steps = item["proof"]["steps"][:8]
            seed_walk = join_walks([s["walk"] for s in seed_steps if "walk" in s])
            proof, walks = theta(4, 2, 1, 0)
            tau_four = walks["tau"] + walks["tau"][1:] * 3
            first = {**beat, "id": "w19a", "minDurationSeconds": 60,
                     "narration": "四二二也沿用刚才三个圈。按这条队列走：柔，派的逆，陶的负二次，派的逆，再接柔和陶的二次。每张卡都要走完合法闭路，再接下一张。画面把经过的边和每块数字都保留下来，可以跟着空格检查。跟踪最终结果，只有 z、a 四、a 一三点轮换。柔固定 z，又循环另外七个旧点；用它不断共轭搬运，这些三角卡都挂在 z 上，先把这一圈接通。现在还缺 c 一，下一张卡把它接进来。",
                     "proof": {**item["proof"], "steps": seed_steps}}
            second = {**beat, "id": "w19b", "minDurationSeconds": 90,
                      "narration": "最后一个点不能靠瞬移塞进去。重新从独立初态，验证整张共轭卡。先把陶四次倒着走。每一次都从根出门绕圈，再回到根，四次走完，旧牌只是临时借位。先确认空格已经回到了根。再执行刚才的种子卡。它仍由柔、派的逆、陶的负二次、派的逆、柔和陶的二次组成。这里要保持刚才规定的左到右顺序，负次数就沿整条闭路反向走，重复经过的边也不能跳过。注意，卡执行时暂时换位的牌不等于它最后的支点；要一直检查到回根，才读最终排列。这些来回路段虽然不改变根，也仍然需要逐边执行。最后正着走四次陶。它撤回最初借用的位置，但把中间种子卡的支点按陶的四次搬了过去。回到根后，暂时借位的牌才能全部对齐。现在检查结果：原来的 z 变成 c 一，a 四和 a 一不动，其余所有位置恢复，所以新的三角卡只有这三个支点。它和旧卡共享两个点，最后一点也接上了。是这个点。接上。四二二通过，二二一暂时封存，后面单独拆开。",
                      "proof": {**proof, "steps": [step("独立初态检验，不把重置当合法滑动", ["完整共轭：τ⁻⁴→种子卡→τ⁴"]),
                                 step("先沿τ的逆闭路走四次", ["根x每圈都恢复", "只是借位，尚不读取最终支点"], walk=tau_four[::-1], cue="先把陶四次倒着走"),
                                 step("执行完整种子卡", ["ρπ⁻¹τ⁻²π⁻¹ρτ²", "种子卡作用=(z a₄ a₁)"], walk=seed_walk, cue="再执行刚才的种子卡"),
                                 step("再沿τ正向闭路走四次", ["撤回借位，支点按τ⁴搬运"], walk=tau_four, cue="最后正着走四次陶"),
                                 step("现在只有c₁、a₄、a₁移动", ["与旧卡共享两个支点", "三角接力纳入最后一点"], focus=["c1", "a4", "a1"], cue="现在检查结果")]}}
            for part in (first, second):
                check_graph(part["proof"])
                beats.append(part)
        else:
            beats.append(beat)
    cues = {
        "w02": {1: "删掉任意一个点", 2: "二连通不要求"},
        "w03": {1: "出门绕路", 2: "整张倒着撤回", 3: "这里先约定记号"},
        "w04": {1: "现在只数", 2: "于是"},
        "w05": {1: "反过来", 2: "不能二染色"},
        "w06": {2: "完全不相交的交换", 4: "每张三角卡本身"},
        "w07": {1: "先倒着做 h", 2: "再做新卡", 3: "最后正着做 h", 4: "任意一对都能换过去"},
        "w08": {1: "第一张正着做", 2: "第二张倒着做", 3: "先接进 c"},
        "w09": {1: "整块搬动", 2: "固定 a", 3: "所有点只能连成一块"},
        "w10": {1: "参数数的是内部顶点", 2: "真正的三条路"},
        "w11": {2: "从 z 沿 a 路到 y"},
        "w12": {1: "派 又能把 z", 2: "先把指定的第一个点"},
        "w13": {1: "两个长循环抵掉之后", 3: "得到第二行", 7: "另一方面"},
        "w14": {1: "把第四行和第二行接起来", 3: "得到第六行", 5: "少搬一次", 7: "它和第三行接上", 9: "最后把第六、第八行相接", 11: "k 至多是"},
        "w15": {1: "就把那张双对换", 2: "得到这两张卡", 3: "这里不能忘记检查"},
        "w16": {1: "这样真正留下的只有"},
        "w17": {1: "现在让空格走第三个圈", 2: "把这张三角卡用", 3: "剩下只要"},
        "w18": {1: "按这条队列执行", 8: "所有三角卡共用两个角"},
        "w20": {1: "内部点全是新的", 2: "删新点", 3: "这样每次施工"},
        "w21": {1: "看外面任意一个连通分量", 2: "就是下一条耳", 3: "外部点加完", 4: "目标图边数有限"},
        "w22": {1: "交换上下两条长臂", 2: "把三条臂同时反向", 3: "二十一个无序端点对"},
        "w23": {1: "零和二得到", 2: "零和三得到", 3: "零和四", 5: "零和 x 得到", 6: "二和无穷得到", 7: "二和 x 得到", 8: "只有三个位置需要改路"},
        "w25": {1: "需要检查最小规模", 2: "指定两点的像之后"},
        "w26": {1: "空格沿新耳出去", 2: "旧群固定 z 时", 3: "大群还可以把 z 搬到 y"},
        "w27": {1: "仍能二染色", 2: "出现奇闭路", 3: "按前面的耳存在性"},
        "w28": {1: "注意无穷路过了两次", 2: "另一条路走"},
        "w29": {1: "每跨一条弦时", 2: "这样长闭路被拆成", 3: "所以整个根群只由"},
        "w30": {1: "考虑这样的分式变换", 2: "现在 T 恰好是", 3: "Q 是三除以"},
        "w31": {1: "每四个非零标量倍数", 2: "还要保证没有别的重复"},
        "w32": {1: "现在夹一张", 2: "k 遍历模五", 3: "矩阵展示采用通常矩阵乘法"},
        "w33": {1: "接着消掉两个非对角元", 2: "这个对角矩阵也不用额外购买", 3: "消元步骤全部能倒着做"},
        "w34": {1: "平方那一类都能缩放成", 2: "而 R 的矩阵行列式", 3: "于是根群恰好是"},
        "w35": {1: "删完折返之后", 2: "每绕一圈", 3: "五环于是有六类"},
        "w36": {1: "普通二分图里", 2: "标记相同", 3: "普通非二分图更直接"},
        "w37": {1: "四环的根群", 2: "上一期我们用格子"},
        "w38": {1: "证明与校验程序放在简介"}}
    for beat in beats:
        if beat["id"] in ("w13", "w14"):
            # Keep proved identities visible while later cards execute. Short
            # narrated transitions must not erase an equation before it is read.
            summary = []
            for index, stage in enumerate(beat["proof"]["steps"]):
                if index == 0:
                    continue
                if index == len(beat["proof"]["steps"]) - 1:
                    stage["rows"] = (summary + ["n=m或n=2m，m≥3；k=n−m"] if beat["id"] == "w13"
                                     else summary[:4] + ["0≤k≤n−3；三个末支点互异"])
                    continue
                if index % 2 == 1:
                    identity = "".join(stage["rows"][:2]).replace("ρ^(m−1)", "ρᵐ⁻¹").replace("ρ^(1−m)", "ρ¹⁻ᵐ")
                    assert len(identity) <= 34, identity
                    summary.append(identity)
                stage["rows"] = summary.copy()
        for index, phrase in cues.get(beat["id"], {}).items():
            assert phrase in beat["narration"], (beat["id"], phrase)
            beat["proof"]["steps"][index]["cue"] = phrase
        needed = sum(max(2 / 30, (len(s.get("walk", [])) - 1) * .4,
                         .8 if s.get("cycles") else 0) for s in beat["proof"]["steps"])
        beat["plannedBudgetSeconds"] = beat["minDurationSeconds"]
        # A rehearsal budget is not a duration floor: forcing 49:30 left many
        # finished formulas silently on screen for 30-50 seconds. The worker
        # retains full measured speech, each real operation, and the short tail.
        beat["minDurationSeconds"] = math.ceil(needed + 6)
    return {"schemaVersion": "vivhite-production-1", "caseId": "inversion-count-wilson-theorem",
            "revision": 1, "title": "把棋盘拆成图：从头证明Wilson滑块定理",
            "width": 1920, "height": 1080, "fps": 30, "fontFamily": "Microsoft YaHei UI", "videoCodec": codec,
            "voice": {"provider": "edge-tts", "name": voice, "rate": rate, "pitch": "+0Hz", "volume": "+0%"},
            "presenter": {"source": "supplied_separately", "role": "teaching_pointer", "replacement": "image_or_prerendered_video"},
            "provenance": {"authoring": "assistant-authored-full-proof", "directorSha256": hashlib.sha256((EPISODE / "director.md").read_bytes()).hexdigest(),
                           "proofSha256": hashlib.sha256((EPISODE / "proof.md").read_bytes()).hexdigest(),
                           "verificationSha256": hashlib.sha256((EPISODE / "verification.json").read_bytes()).hexdigest(),
                           "mathematicalConvention": "position-action-left-to-right; matrices-usual-order",
                           "originalRehearsalBudgetSeconds": 2970,
                           "schedulingPolicy": "measured-speech-plus-observation-tail-and-operation-minima; never-pad-to-rehearsal-budget",
                           "styleSimilarity": "pending-viewer-feedback"}, "beats": beats}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("production-plan-v1.json"))
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+8%")
    parser.add_argument("--codec", choices=("h264_nvenc", "libx264"), default="h264_nvenc")
    args = parser.parse_args()
    plan = build(args.voice, args.rate, args.codec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output), "scenes": 38, "beats": len(plan["beats"]),
                      "steps": sum(len(b["proof"]["steps"]) for b in plan["beats"]),
                      "minimumSeconds": sum(b["minDurationSeconds"] for b in plan["beats"]),
                      "narrationCharacters": sum(len(b["narration"]) for b in plan["beats"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
