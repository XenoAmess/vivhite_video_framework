"""Compile all 28 director scenes into executable, checked proof operations.

The universal proof remains spoken in full. These finite data checks validate
the animation, not the universal theorem. GPL-3.0-only.
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
REPO = next(path for path in EPISODE.parents if (path / "video-maker/pom.xml").is_file())
SPEC = importlib.util.spec_from_file_location("rectangle_certificate", EPISODE / "verify_rectangle.py")
MATH = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MATH)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def grid(rows: int = 3, columns: int = 4, state: list[int] | None = None) -> dict:
    state = list(range(rows * columns)) if state is None else state
    nodes = [{"id": str(r * columns + c), "label": str(r * columns + c),
              "x": 0.10 + c * 0.80 / max(1, columns - 1),
              "y": 0.12 + r * 0.76 / max(1, rows - 1)}
             for r in range(rows) for c in range(columns)]
    edges = []
    for r in range(rows):
        for c in range(columns):
            p = r * columns + c
            if c + 1 < columns:
                edges.append([str(p), str(p + 1)])
            if r + 1 < rows:
                edges.append([str(p), str(p + columns)])
    return {"mode": "graph", "nodes": nodes, "edges": edges,
            "root": "0", "blank": str(state.index(0)),
            "initialTokens": {str(p): str(value) for p, value in enumerate(state)}}


def points(names: str, positions: list[tuple[float, float]] | None = None) -> dict:
    labels = {"a": "甲", "b": "乙", "c": "丙", "d": "丁", "e": "戊", "u": "乌", "v": "维"}
    if positions is None:
        positions = [(0.5 + 0.38 * math.cos(-math.pi / 2 + 2 * math.pi * i / len(names)),
                      0.5 + 0.38 * math.sin(-math.pi / 2 + 2 * math.pi * i / len(names)))
                     for i in range(len(names))]
    return {"mode": "permutation", "nodes": [
        {"id": name, "label": labels.get(name, name), "x": xy[0], "y": xy[1]}
        for name, xy in zip(names, positions)], "edges": [],
        "initialTokens": {name: labels.get(name, name) for name in names}}


def step(cue: str | None = None, text: str = "", rows: list[str] | None = None,
         focus: list[str | int] | None = None, walk: list[int | str] | None = None,
         cycles: list[list[str | int]] | None = None, add: list[list[str | int]] | None = None,
         highlight: int | None = None) -> dict:
    result = {"text": text}
    if cue:
        result["cue"] = cue
    if rows is not None:
        result["rows"] = rows
    if focus is not None:
        result["focus"] = list(map(str, focus))
    if walk is not None:
        result["walk"] = list(map(str, walk))
    if cycles:
        result["cycles"] = [list(map(str, cycle)) for cycle in cycles]
    if add:
        result["addEdges"] = [list(map(str, pair)) for pair in add]
    if highlight is not None:
        result["highlightRow"] = highlight
    return result


def configured(proof: dict, *steps: dict) -> dict:
    proof["steps"] = list(steps)
    return proof


def support(row: int, column: int, columns: int = 4) -> list[int]:
    h = row * columns + column
    return [h + 1, h + columns + 1, h + columns]


def scenes(data: dict) -> dict[int, tuple[dict, str]]:
    opening = data["reachableOpening"]
    goal = data["goal"]
    displaced = list(MATH.apply_walk(tuple(opening), [0, 4, 8], 4))
    configs = {}
    configs[1] = (configured(grid(state=opening),
        step("先看这盘拼图", "同一个判别器，开始读数", ["目标第0行：0 1 2 3", "目标第1行：4 5 6 7", "目标第2行：8 9 10 11", "完整矩形，m,n≥2；一空格", "全部数字互不相同"]),
        step("都是零", "目标与主图：I = 0", ["I = inv(含0) + r₀ + c₀ (mod 2)", "目标 I=0；当前 I=0", "同标记，路线是否一定存在？"], focus=list(range(12))),
        step("再交换这两张数字牌", "直接交换两张牌：不是合法滑动", ["仅交换位置8与9，不移动空格", "当前 I=1，目标 I=0", "不变量不同：一定到不了"], cycles=[[8, 9]]),
        step("把交换撤回", "绿色结果还缺一套合法动作", ["交换撤回，当前 I=0", "必要性已知；充分性现在来证明", "有限完整矩形；至少两行两列"], cycles=[[8, 9]])),
        "I = inv(含0) + r₀ + c₀ (mod 2)")
    configs[2] = (configured(grid(state=opening),
        step("上一期这两个小读数", "不变量挡住红色结果", ["不同标记 → 不可达", "同标记 → 尚未造出路线", "大字是牌；小字是固定位置编号"]),
        step("先把空格送到左上角", "根位置固定为左上角", ["根 o=(0,0)", "需求：动作结束后空格回来"], focus=[0]),
        step("只让三张牌轮流换位", "先造一个只动三点的小工具", ["空格回根；只动三个位置", "再让工具到处安装"], focus=support(0, 0))), "同标记 → 构造合法路线")
    configs[3] = (configured(grid(state=opening),
        step("这里的零就是空格", "含零排列与空格颜色", ["展开时保留0", "初始 inv奇偶=0；r₀+c₀=0", "I=0"], focus=[0]),
        step("零和旁边一张牌交换", "一次合法滑动：两个奇偶都翻转", ["交换0与相邻牌", "inv奇偶=1；r₀+c₀=1", "I=(1+1) mod2=0"], walk=[0, 1]),
        step("整个排列的奇偶会翻转", "滑动已经结束，观察两个读数", ["inv奇偶=1；r₀+c₀=1", "两次翻转相加：I仍为0"], focus=[0, 1]),
        step("为什么隔着几格交换", "排列分析层：对换的奇偶", ["任意两位置相隔d", "对换=先前移d次，再返移d−1次", "总计2d−1次相邻对换，必为奇数", "分析相邻对换不等于棋盘滑动"]),
        step("因此，整张棋盘怎么滑", "两个翻转相加，不变量保留", ["Δinv ≡ 1；Δ(r₀+c₀) ≡ 1", "ΔI ≡ 1+1 ≡ 0 (mod 2)", "这是必要性，尚未证明充分性"])), "ΔI ≡ 0 (mod 2)")
    configs[4] = (configured(grid(state=displaced),
        step("现在把起点和目标的空格", "归根：主图先演示起点S", ["主图：S的空格在位置8", "记录 P_S：8→4→0", "对目标T使用同一构造，独立记P_T"], focus=[8, 4, 0]),
        step("沿行沿列走过去就行", "真实逐步滑动，并保存可倒放的路", ["S沿P_S得到S′", "T沿P_T得到T′", "两条路都可逐步倒放"], walk=[8, 4, 0]),
        step("空格现在又站在同一个位置", "同根同标记：牌的排列差为偶", ["I(S′)=I(T′)", "两局面空格都在o", "数字排列奇偶相同", "待造中段：S′→T′"], focus=[0]),
        step("把这件事做好", "最后连接：P_S、偶重排、倒放P_T", ["S → S′ → T′ → T", "中间只需实现所有偶置换"])), "固定空格后：只需实现任意偶置换")
    four = grid(2, 2)
    for node, label in zip(four["nodes"], ["h", "a", "c", "b"]):
        node["label"] = label
    four["initialTokens"] = {"0": "0", "1": "甲", "2": "丙", "3": "乙"}
    configs[5] = (configured(four,
        step("先只看这四个格子", "入口h是左上角，先盯住三张牌", ["位置：h a / c b", "a=右上；b=右下；c=左下"], focus=[1, 3, 2]),
        step("沿左边下去", "第1步：h→c", ["空格逐边走，牌逐个让位", "本步只交换h与c"], walk=[0, 2]),
        step("再向右", "第2步：c→b", ["本步只交换c与b"], walk=[2, 3]),
        step("向上", "第3步：b→a", ["本步只交换b与a"], walk=[3, 1]),
        step("向左", "第4步：a→h，空格回来", ["本步只交换a与h"], walk=[1, 0]),
        step("盯着另外三个位置", "四步已完成，现在追踪三张牌的去向", ["空格路径h→c→b→a→h", "牌的位置作用：(a b c)"], focus=[1, 3, 2]),
        step("这就是甲到乙", "a→b，b→c，c→a", ["三点轮换，其余位置不动", "空格返回入口"], focus=[1, 3, 2]),
        step("倒着绕一圈", "完整倒放：得到逆三轮换", ["h→a→b→c→h", "位置作用：(a c b)", "正反两个方向均由合法移动得到"], walk=[0, 1, 3, 2, 0]),
        step("正反两个方向", "正反回路都已完成，保留结果观察", ["三轮换与逆三轮换均可实现", "每步都只移动空格旁的一张牌"])), "方格回路 → 纯三轮换")
    configs[6] = (configured(grid(),
        step("这个小三角现在只能在角上转", "把工具搬到远处", ["选右下单位方格", "入口必须是这个方格左上角"], focus=[1, 5, 4]),
        step("我的法杖指这里", "指示位置", ["还需要确认入口"], focus=[7]),
        step("是这个左上角", "入口h=(1,2)，现已修正", ["入口h=6；三点a=7,b=11,c=10", "去程必须避开a,b,c"], focus=[6]),
        step("关键不在路有多长", "去程、绕圈、原路返回", ["P → 四边回路 → reverse(P)", "去程避开三点，返程才能完全撤销"], focus=[7, 11, 10])), "入口 h=(i,j)；P避开a,b,c")
    configs[7] = (configured(grid(),
        step("这条路可以统一画", "同一条一般构造，先看具体入口", ["任意入口 h=(i,j)", "先沿顶行到(0,j)，再下行到(i,j)", "主图实例：i=1,j=2"], focus=[0, 1, 2, 6]),
        step("入口右边的甲和右下的乙", "右侧一列：去程到不了", ["a=(i,j+1)；b=(i+1,j+1)", "去程横段c≤j，竖段c=j", "所以P不碰a,b"], focus=[7, 11]),
        step("入口下面的丙", "同列下方：到入口即停", ["c=(i+1,j)", "去程竖段r≤i，所以不碰c"], focus=[10, 6]),
        step("入口就在最上行时", "边界上允许空路径段", ["i=0：不需要下行段", "j=0：不需要顶行横段", "i=j=0：P为空路径", "0≤i<m−1，0≤j<n−1"])), "P:(0,0) → (0,j) → (i,j)")
    configs[8] = (configured(grid(),
        step("现在真的走一次", "空格沿去程前进，保留每张牌", ["P：0→1→2→6", "原来在0,1,2,6的内容依次让位"], walk=[0, 1, 2, 6]),
        step("到入口后绕一圈", "只让三个角接力", ["回路：6→10→11→7→6", "不碰P上除入口以外的位置"], walk=[6, 10, 11, 7, 6]),
        step("于是原路返回时", "逐步倒放，真实撤销去程", ["reverse(P)：6→2→1→0", "路径内容与绕圈前相同", "每次返程交换撤销对应去程交换"], walk=[6, 2, 1, 0]),
        step("最后空格回到根", "比较起始快照：只有三点不同", ["位置7→11→10→7", "其他9个位置完全恢复", "一般理由是避开三点，不是枚举尺寸"], focus=[7, 11, 10])), "去程 → 方格回路 → 倒放去程")
    configs[9] = (configured(grid(),
        step("把每个单位方格", "检查三角支持有没有漏点", ["T(i,j)是方格除入口外的三个角", "根o不属于任何支持"]),
        step("最上面一行", "顶行每个非根点都是右上角", ["r=0,c≥1：属于T(0,c−1)"], focus=[1, 2, 3]),
        step("最左边一列", "左列每个非根点都是左下角", ["r≥1,c=0：属于T(r−1,0)"], focus=[4, 8]),
        step("剩下同时不在顶行和左列", "其余每点都是右下角", ["r≥1,c≥1：属于T(r−1,c−1)"], focus=[5, 6, 7, 9, 10, 11]),
        step("三种情况把根以外", "三种分类互补，覆盖全部非根点", ["所有T(i,j)的并集=全部非根位置", "还需要：这些支持相接"], focus=list(range(1, 12)))), "覆盖：全部 N−1 个非根位置")
    configs[10] = (configured(grid(),
        step("横着相邻的两个方格", "横邻支持共用一个下方点", ["T(0,0)={1,5,4}", "T(0,1)={2,6,5}", "共同点5"], focus=[1, 5, 4, 2, 6]),
        step("竖着相邻的两个", "竖邻支持也有共同点", ["T(0,0)={1,5,4}", "T(1,0)={5,9,8}", "共同点5"], focus=[1, 5, 4, 9, 8]),
        step("沿着一排方格走", "逐排相接，整张支持网连通", ["单位方格锚点形成(m−1)×(n−1)网", "横、竖相邻支持均相交", "沿相邻网可以到任意单位方格"], focus=list(range(1, 12))),
        step("只有两行时", "最窄的边界仍然相接", ["m=2：横向链", "n=2：纵向链", "m=n=2：只有一个三角，无需接别处"])), "支持交叠网连通；共一个点就够")
    order = [2, 3, 1, 5, 6, 4]
    strip = {"mode": "permutation", "nodes": [
        {"id": str(i), "label": str(i + 1), "x": 0.08 + i * 0.168, "y": 0.5} for i in range(6)],
        "edges": [], "initialTokens": {str(i): str(v) for i, v in enumerate(order)}}
    configs[11] = (configured(strip,
        step("我们造出来的是三张接力", "排列分解层：先数实际逆序", ["2 3 1 5 6 4：inv=4", "这里的对换用于分析，不是滑块动作"]),
        step("反复找一对相邻", "交换一个相邻逆序对", ["交换3、1：inv从4变3"], cycles=[[1, 2]]),
        step("只有这一对逆序被消掉", "外部牌的前后关系不变", ["交换2、1：inv从3变2"], cycles=[[0, 1]]),
        step("所以每换一次", "每次交换恰消去一对逆序", ["交换6、4：inv从2变1"], cycles=[[4, 5]]),
        step("最后逆序数归零", "最后一次相邻逆序交换", ["交换5、4：inv从1变0", "偶数个对换：按顺序两两分组"], cycles=[[3, 4]])), "偶置换 → 偶数个对换 → 两两分组")
    configs[12] = (configured(points("abcd"),
        step("同一对牌交换两遍", "同一对换，第1次", ["(a b)(a b)=id", "排列分析层；a,b,c,d为位置"], cycles=[["a", "b"]]),
        step("直接抵消", "同一对换，第2次：恢复", ["(a b)(a b)=id"], cycles=[["a", "b"]]),
        step("两个交换共有一张牌", "共享一个点：先(b c)", ["(a b)(b c)=(a b c)", "乘积从右到左，队列按时间前进"], cycles=[["b", "c"]]),
        step("就成了三张牌的轮换", "再(a b)：确为三轮换", ["a→b，b→c，c→a"], cycles=[["a", "b"]]),
        step("最麻烦的是", "恢复起始牌，再看不相交双交换", ["倒放刚才的三轮换以恢复演示", "现在研究(a b)(c d)"], cycles=[["a", "c", "b"]]),
        step("先转甲丙丁", "第一段：(a c d)", ["目标：(a b)(c d)", "实际先做(a c d)"], cycles=[["a", "c", "d"]]),
        step("再转甲丙乙", "第二段：(a c b)", ["(a b)(c d)=(a c b)(a c d)", "结果：a↔b，c↔d"], cycles=[["a", "c", "b"]]),
        step("反过来", "三轮换本身是偶置换", ["(a b c)=(a c)(a b)", "所有偶置换都能分解成三轮换", "三轮换也只会生成偶置换"])), "三轮换生成的恰好是全部偶置换")
    configs[13] = (configured(points("abcde"),
        step("不过，刚才说的是任意三个位置", "不能假装远处三点已经会转", ["现有工具只来自方格支持", "需要证明相接工具能够扩张"]),
        step("先点亮第一个三角", "三点起步：全部偶置换都齐了", ["S={a,b,c}", "三点上的偶置换：id,(a b c),(a c b)"], focus=["a", "b", "c"], add=[["a", "b"], ["b", "c"], ["c", "a"]]),
        step("接下来每次只接一个", "归纳假设：已控制S上的全部偶置换", ["接一个与S相交的新三角", "证明扩大区域仍能做全部偶置换", "不能用结论代替扩张证明"])), "基础三点 → 证明相交扩张 → 有限归纳")
    configs[14] = (configured(points("abuvc"),
        step("先接这种容易一点的", "两个旧点a,b，加一个新点c", ["旧集合S含a,b,u,v；c在外", "α=(a b c)，正反均可用", "示例偶接线g=(a u)(b v)"], focus=["a", "b", "c"]),
        step("执行时先倒放接线", "先做g⁻¹，把目标端口搬来", ["时间队列：g⁻¹ → α → g", "c不受接线影响"], cycles=[["a", "u"], ["b", "v"]]),
        step("再转甲乙丙", "再做α=(a b c)", ["中间只调用现成三角工具"], cycles=[["a", "b", "c"]]),
        step("最后正放接线", "最后做g，搬回目标端口", ["gαg⁻¹=(g(a) g(b) c)", "示例结果：(u v c)"], cycles=[["a", "u"], ["b", "v"]]),
        step("所以还得确认", "一般接线必须能选成偶置换", ["只保证旧区域内所有偶动作可用", "下一步解决接线的奇偶问题"])), "共轭：先g⁻¹，再α，最后g")
    configs[15] = (configured(points("abuvc"),
        step("先随便把甲乙接到乌维", "先任取满足无序对条件的双射", ["g({a,b})={u,v}", "这里只是接线图，还没有执行g"], focus=["a", "b", "u", "v"], add=[["a", "u"], ["b", "v"]]),
        step("如果这条接线是偶的", "偶接线直接由旧工具实现", ["若sgn(g)=+1，直接使用"]),
        step("如果是奇的", "输出侧交换u、v，奇偶翻转", ["g′=(u v)g，是偶置换", "无序对的像仍为{u,v}", "只交换端口先后，不损失支持"], focus=["u", "v"], add=[["u", "v"]]),
        step("三轮换的方向也跟着反", "三角正反方向都能做", ["得到(u v c)或其逆", "两个方向都可用"], focus=["u", "v", "c"]),
        step("扩大后的所有三轮换就都齐了", "新集合上的三轮换无遗漏", ["三旧点：原本已会", "两旧点与c：刚才共轭得到", "由分解引理得到A(S∪{c})"])), "A(S) + 两旧一新三角 → A(S∪{c})")
    configs[16] = (configured(grid(),
        step("把刚才两两捆好的交换磁带拿回来", "把抽象分解逐层落到实际工具", ["任意偶置换 → 有限个三轮换"]),
        step("三个都是旧点的", "调用归纳假设中已掌握的动作", ["三旧点 → 旧区域已有工具", "带c → 共轭接线加新三角"]),
        step("每段接线也是旧区域内", "接线仍来自已有的偶动作", ["共轭接线 → 旧区域偶置换", "递归展开，底层都是方格回路"]),
        step("每个最底层三角", "实际播放一个底层合法工具", ["空格去入口 → 绕一圈 → 原路回根", "0→1→5→6→2→1→0"], walk=[0, 1, 5, 6, 2, 1, 0]),
        step("新三角只搭上一个旧点", "还剩一旧两新接口需要证明", ["两旧一新已经完成", "现在不能直接使用尚未证明的接口"])), "偶置换 → 三轮换 → 共轭 → 合法方格路径")
    configs[17] = (configured(points("abcde"),
        step("现在甲是旧点", "一旧两新：旧点a,d,e；新点b,c", ["α=(a b c)", "|S|≥3，能选不同的a,d,e", "g=(a d e)固定b,c"], focus=["a", "d", "e"]),
        step("拿它给新三角重新接线", "共轭第1步：g⁻¹", ["时间顺序：g⁻¹ → α → g"], cycles=[["a", "e", "d"]]),
        step(None, "共轭第2步：α", ["先把旧支点搬来，再转新三角"], cycles=[["a", "b", "c"]]),
        step("就复制出丁乙丙的轮换", "共轭第3步：g", ["β=gαg⁻¹=(d b c)", "新点b,c没有被g碰到"], cycles=[["a", "d", "e"]]),
        step("两只几乎重叠的三角", "现在有α与β：只差旧支点", ["α=(a b c)；β=(d b c)", "下一步先β⁻¹，后α"], focus=["a", "b", "c", "d"])), "g=(a d e)；gαg⁻¹=(d b c)")
    configs[18] = (configured(points("abcd"),
        step("先做丁乙丙的反向", "先执行β⁻¹=(d c b)", ["点 | β⁻¹后 | α后", "a  | a     | b", "b  | d     | d", "d  | c     | a", "c  | b     | c"], cycles=[["d", "c", "b"]]),
        step("再做甲乙丙的正向", "后执行α=(a b c)", cycles=[["a", "b", "c"]]),
        step("甲不受前一步影响", "逐点追踪a：a→a→b", focus=["a", "b"], highlight=1),
        step("乙先去丁", "逐点追踪b：b→d→d", focus=["b", "d"], highlight=2),
        step("丁先去丙", "逐点追踪d：d→c→a", focus=["d", "c", "a"], highlight=3),
        step("最后看丙", "逐点追踪c：c→b→c，固定", focus=["c"], highlight=4),
        step("只有甲、乙、丁在接力", "所得(a b d)：两旧点带一新点", ["αβ⁻¹=(a b d)", "a,d旧；b新；c已抵消"], focus=["a", "b", "d"])), "αβ⁻¹=(a b d)，实际先β⁻¹后α")
    configs[19] = (configured(points("abcde"),
        step("先用这个甲乙丁的三角", "起步旧集合S={a,d,e}", ["新工具(a b d)有两个旧点", "先使用已经证明的两旧一新规则"], focus=["a", "d", "e"], add=[["a", "d"], ["d", "e"], ["e", "a"]]),
        step("把乙接进旧区域", "第1次扩张：纳入b", ["S → S∪{b}", "新集合上全部偶置换可用"], focus=["a", "d", "e", "b"], add=[["a", "b"], ["b", "d"]]),
        step("只剩丙一个新点", "原α现在也变成两旧一新", ["α=(a b c)，a,b现在都旧", "再用同一条已经证明的规则"], focus=["a", "b", "c"]),
        step("丙也接进来了", "第2次扩张：纳入c", ["S∪{b} → S∪{b,c}", "没有同时硬塞两个新点"], focus=list("abcde"), add=[["b", "c"], ["c", "a"]]),
        step("无论重叠两个点", "所有相交接口都处理完毕", ["交2旧点：添1", "交1旧点：先添1，再添1", "交3旧点：无需扩张"])), "S → S∪{b} → S∪{b,c}")
    traversal = [(0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0)]
    covered = set()
    expansion = []
    cues = ["第一只三角点亮三个位置", "沿着相邻的方格", "刚才两种接口", "如果三个点早就亮了", "一个方格一个方格接下去", "最后亮起的就是根以外"]
    for index, ((r, c), cue) in enumerate(zip(traversal, cues), 1):
        triple = support(r, c)
        covered.update(triple)
        expansion.append(step(cue, f"接入第{index}个方格：T({r},{c})", [
            "连通：总有相接的下一只三角", "扩张：相交1点或2点均已证明", "覆盖：最终没有漏掉非根点", f"实例进度：{len(covered)}/11个非根点"],
            focus=sorted(covered), add=[[triple[0], triple[1]], [triple[1], triple[2]], [triple[2], triple[0]]]))
    configs[20] = (configured(grid(), *expansion), "有限 + 连通 + 覆盖 → 全部非根位置")
    # Support triangles contain diagonal links. They describe permutation
    # supports, not additional edges along which the blank is allowed to slide.
    configs[20][0]["mode"] = "permutation"
    configs[21] = (configured(grid(),
        step("这台机器终于装好了", "下界：全部偶置换均有合法做法", ["三角支持覆盖并连通", "相交扩张给出A(全部非根位置)"], focus=list(range(1, 12))),
        step("反过来，空格回到左上角时", "上界：不变量排除全部奇置换", ["空格颜色回原值", "排列奇偶必须回原值", "不能实现奇置换"], focus=[0]),
        step("根上的能力恰好", "两边合起来，能力恰好相等", ["根空格合法闭合动作群=A(N−1)", "下一步接回任意起点和目标"])), "固定根空格：能力恰好是全部偶置换")
    configs[22] = (configured(grid(state=displaced),
        step("把两张归根磁带拿回来", "保持全部局面接口，开始接三段", ["主图S的空格在8", "P_S：8→4→0", "目标T的归根路径P_T独立记录"]),
        step("起点送空格到根", "第1段：S→S′", ["S沿P_S归根", "T沿P_T归根得到T′", "同标记且同根：重排π为偶"], walk=[8, 4, 0]),
        step("它们同标记", "第2段：由工具实现偶重排", ["实例S′→T′调用两个方格工具", "一般局面由三轮换分解给出有限动作", "不保证最短路线"], walk=data["blankWalkFromOpeningToGoal"]),
        step("接着倒放目标那张磁带", "第3段：T′→T", ["主图示例reverse(P_T)：0→1→2→3", "每个接口比对完整牌阵，不只比空格"], walk=[0, 1, 2, 3]),
        step("整个论证没有要求", "三段均有限且每步合法", ["S → S′ → T′ → T", "不依赖具体牌号，也不依赖宽度奇偶"])), "同标记 → 同根偶重排 → 合法路线")
    configs[23] = (configured(grid(state=opening),
        step("看回开场这盘", "用相同两件工具，真实还原开场", ["此处只演示16步实例", "一般证明已经完成，不声称最短"]),
        step("先让空格沿顶行走两步", "去入口：0→1→2→6", ["第1个工具：入口(1,2)", "去程避开7,11,10"], walk=[0, 1, 2, 6]),
        step("然后反着绕这个方格一圈", "方格反向回路：6→7→11→10→6", ["四次相邻滑动", "撤销右下三点的轮换"], walk=[6, 7, 11, 10, 6]),
        step("接着沿去程原路返回", "返程：6→2→1→0", ["去程牌逐一复原", "第1件工具完成，共10步"], walk=[6, 2, 1, 0]),
        step("再看上面这个三角", "第2个工具：先到入口1", ["入口(0,1)", "去程只有一步"], walk=[0, 1]),
        step("沿四条边绕回来", "方格反向回路：1→2→6→5→1", ["又四次相邻滑动", "撤销上面三点的轮换"], walk=[1, 2, 6, 5, 1]),
        step("最后原路归根", "回到根0，整盘与目标完全重合", ["第2件工具6步；累计16步", "此实例路径全部合法", "任意尺寸可达性来自之前的一般构造"], walk=[1, 0]),
        step("整盘就和目标重合", "归根已完成，逐格对照最终目标", ["16次合法滑动全部完成", "牌阵与目标完全一致"], focus=list(range(12))),
        step("绿色标记给的是一定存在路线", "绿色结果：一定存在合法路线", ["目标第0行：0 1 2 3", "目标第1行：4 5 6 7", "目标第2行：8 9 10 11", "当前与目标逐格相同", "I始终为0"], focus=list(range(12)))), "同一个开场 → 同一条16步合法路线 → 同一个目标")
    configs[24] = (configured(grid(1, 4, [0, 2, 3, 1]),
        step("现在故意把棋盘压成一行", "没有单位方格，三角工具失效", ["主图：[0,2,3,1]，inv=2，I=0", "目标：[0,1,2,3]，inv=0，I=0", "同标记仍不可达"]),
        step("数字永远不能越过另一张数字", "空格能移动，数字顺序不能交叉", ["去掉空格，非空牌顺序始终是2,3,1", "目标的顺序是1,2,3"], walk=[0, 1, 2, 3]),
        step("至少两行两列不是装饰条件", "前提确保确实存在方格和接力网", ["本定理要求m,n≥2", "缺格或修改连边也不能直接套用"])), "单行反例：同一个奇偶位仍不够")
    narrow = grid(2, 2)
    for axis in ("h", "v"):
        for index in range(4):
            narrow["nodes"].append({"id": f"{axis}{index}", "label": f"{axis}{index + 1}",
                                    "x": 0.1 + index * 0.25 if axis == "h" else 0.92,
                                    "y": 0.98 if axis == "h" else 0.04 + index * 0.25})
            narrow["initialTokens"][f"{axis}{index}"] = f"{axis}{index + 1}"
            if index:
                narrow["edges"].append([f"{axis}{index - 1}", f"{axis}{index}"])
    # Put the actual 2x2 away from the two support-chain diagrams.
    for node in narrow["nodes"][:4]:
        node["x"] = 0.13 + (int(node["id"]) % 2) * 0.38
        node["y"] = 0.18 + (int(node["id"]) // 2) * 0.38
    configs[25] = (configured(narrow,
        step("那二乘二会不会反而太小", "主图左侧：最小2×2棋盘", ["唯一三角覆盖全部三张牌", "id、正转、反转就是A₃"], focus=[1, 3, 2]),
        step("它的正反轮换", "2×2真实四步回路", ["左侧主图仍为合法滑块动作", "下方h链、右侧v链是支持交叠图"], walk=[0, 2, 3, 1, 0]),
        step("只有两行或两列", "两行和两列：支持网退化为链", ["h1—h2—h3—h4：横向支持链", "v1—v2—v3—v4：纵向支持链", "覆盖与相接依然成立"], focus=["h0", "h1", "h2", "h3", "v0", "v1", "v2", "v3"]),
        step("小棋盘还可以把全部状态", "有限全枚举只用于实例核对", ["2×2：24=12+12个局面", "2×3：720=360+360个局面", "每个分量内I相同"], focus=[0, 1, 2, 3]),
        step("真正让任意有限尺寸成立的", "一般结论依赖构造与归纳", ["有限枚举不证明所有大棋盘", "全尺寸依据：方格工具+相交扩张"])), "2×2、2×n、m×2均在同一证明内")
    configs[26] = (configured(grid(state=opening),
        step("把这盘再交换两张数字牌", "直接换两数字，I从0变成1", ["对换位置8、9：不是合法滑动", "目标I=0，当前I=1"], cycles=[[8, 9]]),
        step("把交换撤回", "I恢复0，不再有隐藏障碍", ["对换撤回，当前I=0", "必要性与充分性均已完成"], cycles=[[8, 9]]),
        step("当且仅当", "完整定理：可达当且仅当标记相同", ["S↔T ⇔ I(S)=I(T)", "I=inv(含0)+r₀+c₀ (mod 2)", "有限完整矩形；m,n≥2", "一空格；牌互异；正交相邻滑动"])), "S↔T ⇔ I(S)=I(T)")
    configs[27] = (configured(grid(),
        step("以后遇到这类矩形拼图", "判定可达性，再优化具体路线", ["I不同 → 停止无效搜索", "I相同 → 一定可达，继续规划好走的路"]),
        step("空格去远处借一次位置", "同一件小工具，去程绕圈返程", ["工具从合法空格行走产生", "实例：左上单位方格"], walk=[0, 4, 5, 1, 0]),
        step("三角之间借一个支点", "同一张网逐步扩张", ["方格回路 → 三轮换", "相交扩张 → 全部偶置换"], focus=list(range(1, 12))),
        step("我的这套三角接力", "三角接力，全部接通", ["完整矩形的可达性结论已闭合", "具体路线还可以继续优化"])), "判定可达性 → 规划与优化路线")
    ring = {"mode": "graph", "nodes": [
        {"id": str(i), "label": str(i), "x": 0.5 + 0.38 * math.cos(2 * math.pi * i / 7 - math.pi / 2),
         "y": 0.5 + 0.38 * math.sin(2 * math.pi * i / 7 - math.pi / 2)} for i in range(7)],
        "edges": [[str(i), str((i + 1) % 7)] for i in range(7)], "root": "0", "blank": "0",
        "initialTokens": {str(i): str(i) for i in range(7)}}
    configs[28] = (configured(ring,
        step("如果把格子换成任意的点和边", "换成一般图，方格工具未必存在", ["合法一步仍是空格与相邻牌交换", "但图上可能根本没有四边回路"]),
        step("比如只剩一个大圆环", "空格绕环回来，数字循环顺序仍保留", ["主图C₇：空格走完一周", "牌的循环顺序保留，约束多于奇偶"], walk=list(range(7)) + [0]),
        step("下一期，我们从这些回路", "下一期：从头证明威尔逊一般图定理", ["范围、条件和例外都需要重做", "并非任意图都只由奇偶决定"]),
        step("今天先把这块矩形拼好", "本期：完整矩形自含构造证明", ["Richard M. Wilson，1974", "Graph Puzzles, Homotopy,", "and the Alternating Group", "DOI:10.1016/0095-8956(74)90098-7", "本片图形原创；人物图片暂为占位"])), "没有方格时，怎样生成足够多的合法动作？")
    return configs


def parse_director() -> list[dict]:
    text = (EPISODE / "director.md").read_text(encoding="utf-8")
    result = []
    for scene in re.split(r"(?m)^### ", text)[1:]:
        header = scene.splitlines()[0]
        match = re.fullmatch(r"(\d{2})｜(\d{2}:\d{2})–(\d{2}:\d{2})｜(.+)", header)
        assert match, header
        narration = scene.split("**旁白：**", 1)[1].split("**动作：**", 1)[0].strip()
        action = scene.split("**动作：**", 1)[1].split("**屏幕：**", 1)[0].strip()
        result.append({"id": f"r{match[1]}", "heading": match[4], "narration": narration.replace("Wilson", "威尔逊"),
                       "action": action})
    assert len(result) == 28
    return result


def validate_data(plan: dict) -> dict:
    operations = 0
    walk_moves = 0
    for beat in plan["beats"]:
        proof = beat["proof"]
        nodes = {node["id"] for node in proof.get("nodes", [])}
        edges = {frozenset(pair) for pair in proof.get("edges", [])}
        tokens = dict(proof.get("initialTokens", {}))
        blank = proof.get("blank")
        cursor = 0
        for operation in proof["steps"]:
            cue = operation.get("cue")
            if cue:
                found = beat["narration"].find(cue, cursor)
                assert found >= cursor, (beat["id"], cue, cursor)
                cursor = found + len(cue)
            assert len(operation.get("text", "")) <= 50, (beat["id"], operation)
            rows = operation.get("rows", [])
            assert len(rows) <= 5 and all(len(row) <= 34 for row in rows), (beat["id"], rows)
            for pair in operation.get("addEdges", []):
                assert set(pair) <= nodes
                edges.add(frozenset(pair))
            walk = operation.get("walk")
            if walk:
                assert walk[0] == blank, (beat["id"], walk, blank)
                for before, after in zip(walk, walk[1:]):
                    assert frozenset([before, after]) in edges
                    assert tokens[before] == "0"
                    tokens[before], tokens[after] = tokens[after], tokens[before]
                    blank = after
                    walk_moves += 1
            for cycle in operation.get("cycles", []):
                old = dict(tokens)
                for before, after in zip(cycle, cycle[1:] + cycle[:1]):
                    tokens[after] = old[before]
            operations += 1
        if beat["id"] == "r08":
            assert [tokens[str(i)] for i in range(12)] == list(map(str, MATH.apply_walk(tuple(range(12)), MATH.face_walk(4, 1, 2), 4)))
        if beat["id"] == "r14":
            assert tokens == {"a": "甲", "b": "乙", "u": "丙", "v": "乌", "c": "维"}, tokens
        if beat["id"] == "r12":
            assert tokens == {"a": "乙", "b": "甲", "c": "丁", "d": "丙"}, tokens
        if beat["id"] == "r17":
            assert tokens == {"a": "甲", "b": "丁", "c": "乙", "d": "丙", "e": "戊"}, tokens
        if beat["id"] == "r18":
            assert tokens == {"a": "丁", "b": "甲", "c": "丙", "d": "乙"}, tokens
        if beat["id"] == "r23":
            assert [tokens[str(i)] for i in range(12)] == list(map(str, range(12)))
    return {"schemaVersion": "vivhite-rectangle-production-data-check-1", "passed": True,
            "sceneCount": len(plan["beats"]), "proofSteps": operations,
            "actualLegalBlankMoves": walk_moves, "allCuesInSpokenOrder": True,
            "allRowsFitContract": True, "corePositionActionsVerified": ["r08", "r12", "r14", "r17", "r18", "r23"],
            "universalProofSource": "../proof.md", "finiteChecksAreNotUniversalProof": True}


def build() -> tuple[dict, dict]:
    verified = json.loads((EPISODE / "verification.json").read_text(encoding="utf-8"))
    pacing = json.loads((EPISODE / "pacing.json").read_text(encoding="utf-8"))
    beats = parse_director()
    # These two adaptations align the deictic narration with a single main graph
    # and give each of the sixteen real swaps a clearly described screen event.
    beats[0]["narration"] = (
        "先看这盘拼图，目标是右边这一串数字。把空格也排进去，数一下逆序的奇偶，再加上空格的行号和列号。"
        "当前和目标一样，都是零。再交换这两张数字牌，读数变成一，这一盘就到不了。把交换撤回，绿色的结果呢？"
        "今天，我要给它补上一套动作。只要棋盘是完整的矩形，而且至少两行两列，标记相同，就一定能拼到。"
        "不是只试这张棋盘。我们把棋盘拉长、加宽以后，理由也得继续管用。")
    beats[22]["narration"] = (
        "看回开场这盘。先让空格沿顶行走两步，再下一步，到右下方格的入口。然后反着绕这个方格一圈，四次相邻滑动，"
        "让这里的三张牌回到各自的位置。接着沿去程原路返回，路上的牌一张一张复原。再看上面这个三角，先走到入口。"
        "沿四条边绕回来，让上面的三张牌也各自归位。最后原路归根，整盘就和目标重合了。"
        "这一例只用了两次工具，总共十六步；一般局面的分解可能长得多，我们没有在证明里保证最短。"
        "绿色标记给的是一定存在路线，刚才的装配过程解释了为什么一定存在。至于怎样把路线再压短，那是另一台机器要干的活。")
    configs = scenes(verified["openingAndClosing"])
    for index, (beat, pace) in enumerate(zip(beats, pacing["scenes"]), 1):
        proof, formula = configs[index]
        if index == 6:
            proof["pointer"] = True
        beat.update({"view": "proof", "chapter": ("01  必要性与方格工具" if index <= 10 else
                    "02  三角接力的完整证明" if index <= 20 else "03  接回任意局面与定理边界"),
                     "seriesLabel": "逆序数 · 完整矩形证明",
                     "action": "；".join(operation["text"] for operation in proof["steps"]) + "。按实际词边界推进，牌的身份连续保留；人物使用图片占位。",
                     "proof": proof, "formula": formula,
                     "note": "有限实例核对不代替任意尺寸的一般证明。" if index in (20, 25) else "",
                     "reaction": ("三角接力，全部接通。" if index == 27 else
                                  "三角接力，启动。" if index == 5 else ""),
                     "minDurationSeconds": pace["endSeconds"] - pace["startSeconds"],
                     "tailSeconds": pace["additionalObservationSeconds"],
                     "observationTask": pace["observationTask"],
                     "sourceDirectorScene": f"{index:02d}"})
    plan = {"schemaVersion": "vivhite-production-1", "caseId": "rectangle-proof", "revision": 1,
            "title": "任意大的矩形拼图，为什么只差一个奇偶位？", "width": 1920, "height": 1080, "fps": 30,
            "fontFamily": "Microsoft YaHei UI", "videoCodec": "h264_nvenc",
            "voice": {"provider": "edge-tts", "name": "zh-CN-XiaoxiaoNeural", "rate": "+8%", "pitch": "+0Hz", "volume": "+0%"},
            "presenter": {"source": "supplied_separately", "role": "teaching_pointer", "replacement": "image_or_prerendered_video"},
            "provenance": {"directorSha256": digest(EPISODE / "director.md"), "proofSha256": digest(EPISODE / "proof.md"),
                           "mathVerificationSha256": digest(EPISODE / "verification.json"),
                           "pacingSha256": digest(EPISODE / "pacing.json"),
                           "styleProfile": "series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-transfer-v2.json",
                           "authoring": "assistant_authored_rectangle_proof_v1",
                           "narrationAdaptations": ["r01:单主图逐次比较，未删数学内容", "r23:为16次真实滑动扩展动作解说", "Wilson读作威尔逊"],
                           "styleSimilarity": "pending_viewer_feedback"}, "beats": beats}
    return plan, validate_data(plan)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EPISODE / "authoring/production-plan-v1.json")
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+8%")
    parser.add_argument("--video-codec", default="h264_nvenc")
    args = parser.parse_args()
    plan, checks = build()
    plan["voice"].update({"name": args.voice, "rate": args.rate})
    plan["videoCodec"] = args.video_codec
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    checks["productionPlanSha256"] = digest(args.output)
    (args.output.parent / "production-data-check-v1.json").write_text(
        json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Compiled {len(plan['beats'])} complete proof scenes; checked {checks['actualLegalBlankMoves']} legal blank moves")


if __name__ == "__main__":
    main()
