"""Case adapter: authored v2 story + verified mathematical data -> maker contract.

This does not analyze arbitrary videos. It deliberately refuses different evidence.
GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def find_repository_root() -> Path:
    for candidate in Path(__file__).resolve().parents:
        if ((candidate / "video-maker/pom.xml").is_file()
                and (candidate / "video-analyzer/pom.xml").is_file()):
            return candidate
    raise RuntimeError("Cannot locate the video framework repository root")


ROOT = find_repository_root()
START = [2, 3, 1, 4, 5, 0]
GOAL = [1, 2, 3, 4, 5, 0]
BAD = [2, 1, 3, 4, 5, 0]
LOOP = [[1, 2, 3, 0], [1, 2, 0, 3], [0, 2, 1, 3], [2, 0, 1, 3], [2, 3, 1, 0]]


def compose(analysis_path: Path, math_path: Path, voice: str = "zh-CN-XiaoxiaoNeural",
            rate: str = "+8%", video_codec: str = "h264_nvenc") -> dict:
    analysis_bytes = analysis_path.read_bytes()
    analysis = json.loads(analysis_bytes)
    if analysis.get("validationStatus") != "structural_and_evidence_coverage_passed":
        raise ValueError("Analysis coverage must be validated first")
    expected = {"c0ee37461026f0c23254c57b85f2858592f03a2fa89db75e81102ad5102eec3d",
                "0aac566c037a04aff4d6e2a7f499ed198982d9b20f8d62863bfbd7b19186fd02"}
    if not expected.issubset(set(find_hashes(analysis))):
        raise ValueError("This authored story belongs to a different pair of videos")
    math = json.loads(math_path.read_text(encoding="utf-8"))
    if math["start"] != START or math["goal"] != GOAL or math["moveCount"] != 14:
        raise ValueError("Unexpected mathematical verification")
    style_file = ROOT / "series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-transfer-v2.json"
    beats = []

    def add(chapter, heading, narration, view="board", states=None, **kwargs):
        beat = {"id": f"b{len(beats) + 1:02}", "chapter": chapter, "heading": heading,
                "narration": narration, "view": view, "columns": 3, "states": states or [START],
                "action": kwargs.pop("action", "保持当前数学对象，执行所列状态或连线操作；字幕使用配音词边界。"),
                "formula": "", "note": "", "reaction": "", "knowledgePointIds": [],
                "styleMechanismIds": ["SR02", "SR03", "SR04"]}
        beat.update(kwargs)
        beats.append(beat)

    c = "00  先借用一台判别器"
    add(c, "这块拼图，真的拼得回去吗？",
        "假设我们想把左边这块滑块拼图，拼成右边的样子。每次只能把空格旁边的一块滑进去，不能拿起来交换。你可能已经准备动手试了，不过，我们先借一台小机器。",
        goal=GOAL, states=[START, [2, 3, 0, 4, 5, 1], START],
        reaction="先别急着拼", knowledgePointIds=["K01"],
        action="开场即给出真实待解棋盘与目标；1滑入空格再滑回，明确合法操作；角色把注意力引向工具。")
    add(c, "输入棋盘，读取一个 0 或 1",
        "机器先数一数，展开后的连线有多少对交叉，再看空格落在哪种颜色上。把这两个读数合在一起，只留下奇偶，左边读出零，目标也读出零。至于它为什么有用，我们马上拆开来看。",
        "parity", [START], formula="当前：τ = 7，r+c = 3 → I = 0    ｜    目标：5 + 3 → I = 0",
        note="功能预告；交叉图与合成规则将在后文构造。坐标从 0 开始。", reaction="同类，可以继续",
        knowledgePointIds=["K07", "K09"], action="实际显示棋盘、交叉奇偶、空格颜色和合成读数；保留数字7、3、0的对应关系。")
    add(c, "只是交换两块，结果就不一样",
        "换一块看起来更整齐的，只有一和二的位置倒过来了。它却读出一，和目标的零不同。这次机器可以直接告诉你：正常滑动到不了。看起来更接近，反而根本没法拼好。",
        "parity", [BAD], formula="反例：6 + 3 → I = 1    ≠    目标 I = 0", reaction="整齐也不管用？",
        knowledgePointIds=["K08"], action="在同一判别器中切换反例输入，交叉计数变6，空格色不变，输出由0变1。")
    add(c, "不看过程，怎么知道结果？",
        "这台机器既不记你走过哪些路，也不替你排好数字，却能先排除一半局面。它凭什么这么省事？我们把棋盘缩小，从只有四格的拼图开始，亲手把这台机器造出来。",
        states=[[1, 2, 3, 0]], columns=2,
        labels=["一个问题", "滑动时，有什么一直没变？"], reaction="拆开研究一下",
        action="保留片头判别器的需求，切换四格棋盘；这次重置由研究不变量的需要驱动。")

    c = "01  小棋盘：把顺序露出来"
    add(c, "绕一圈，空格回来了",
        "这里是三个数字和一个空格。让三滑过来，一再跟上，然后是二，最后让三回来。空格绕了一圈，回到原位，三个数字却轮换了位置。你没把任何一块拿起来，它们就完成了一次接力。",
        states=LOOP, columns=2, labels=["4 次合法滑动", "空格回原位", "三个数字循环换位"],
        moveCues=[{"phrase": "让三滑过来"}, {"phrase": "一再跟上"}, {"phrase": "然后是二"}, {"phrase": "最后让三回来"}],
        knowledgePointIds=["K04"], action="按真实四步数据播放，不跳帧替换数字；空格归位后停留，让观众读出数字位置变化。")
    add(c, "位置变了，绕圈次序没变",
        "把四个格子沿外圈读出来，就得到一个环。忽略空格，只盯住一、二、三的先后关系。你可以让它们接着绕，但一后面还是二，二后面还是三。滑动改变的是位置，不是这个循环次序。",
        "cycle", LOOP, columns=2, formula="沿外圈读取：1 → 2 → 3 → 1", reaction="跟着数字走",
        knowledgePointIds=["K04"], action="棋盘与外圈节点同时保留；环上数字跟随同一状态数据变化，忽略0后读出循环次序。")
    add(c, "另一种次序，绕不到这里",
        "要是把一和二对调，沿环读到的次序就反了。四个位置一共有二十四种排列，但不是一个大家庭，而是两个互不相通的小圈子。每个圈子里各有十二种局面，只能在自己的圈子里转。",
        "cycle", [LOOP[0]], columns=2, components=True,
        formula="24 个排列 = 12 个可达局面 + 另外 12 个", reaction="真有两个圈",
        knowledgePointIds=["K04"], action="从合法邻接生成两个完整12态环，逐个高亮节点；不把四步回路误说成全部12态。")
    add(c, "大棋盘，先把问题缩小",
        "大棋盘当然复杂一些，不过也能利用这种接力。通常先把上边一行、左边一列送回去，再保护已经排好的部分，让活动区域一圈圈缩小。最后留下的小棋盘，就更容易看清该怎么转。",
        states=[[1, 0, 2, 4, 5, 3, 7, 8, 6]], columns=3,
        labels=["先保护已完成的部分", "缩小活动区域", "最后处理小棋盘"], knowledgePointIds=["K03"],
        note="复原策略示意；不保证最短，也不是对任意局面可解性的证明。",
        action="九格棋盘保留左上固定前缀；侧层说明先行列、后剩余局部的策略。")
    add(c, "行末两块，要一起留位置",
        "但别急着把每一块都锁死。比如这一行最后两块，要先留出它们一起转进来的位置。看这里，二滑到空位，三再跟上，一行才真正完成。策略里要留转身的空间，不能只贪眼前那一点整齐。",
        states=math["rowEndDemonstration"], columns=3,
        moveCues=[{"phrase": "二滑到空位"}, {"phrase": "三再跟上"}],
        labels=["保护数字 1", "2、3 成对进入行末", "先留空间，再封好一行"], reaction="别堵住后路",
        knowledgePointIds=["K03"], note="只演示行末成对收尾的两步，不是任意棋盘的完整复原算法。",
        action="连续播放已核验的2向左、3向上，保持1不动，展示行末两块成对收尾。")
    add(c, "能不能不把所有局面画出来？",
        "这些办法能帮我们拼，但片头的问题还没解决：拿到一个局面，怎么在动手之前判断它属于哪个圈子？总不能把大棋盘的所有局面都画出来。我们需要一个更小巧的读数，来记录这种顺序差别。",
        "cycle", [LOOP[0]], columns=2, components=True,
        formula="把“属于哪个圈子”压缩成一个标记", action="保留两个可达环，提出压缩状态图的需求，自然进入排列与连线表示。")

    c = "02  展开棋盘：用交叉记住顺序"
    add(c, "从棋盘到一行数字",
        "回到开头的六格棋盘。按第一行、第二行的顺序，把它摊成一排，空格也别丢，用零代替。下面另外放一排从零到五的参照，让相同数字连起来。现在，顺序问题变成了连线问题。",
        "wires", [START], reveal=True, formula="当前排列 2 3 1 4 5 0    →    排序参照 0 1 2 3 4 5",
        note="下排是排序参照，不是本题目标棋盘；0 表示空格。", knowledgePointIds=["K05"],
        action="同一组数字出现在上下两排，连线逐渐长出，颜色随数字身份保持。")
    add(c, "为什么这两条线会交叉？",
        "比如二在一的前面，但排好序以后，一应该在二前面。这两个数字的先后倒过来了，两条线就会交叉。反过来，四和五的顺序没有颠倒，线就不用互相穿过去。图上每一对交叉，都在记一次顺序颠倒。",
        "wires", [START], formula="前面的大于后面的 → 这一对构成逆序",
        focusPairs=[{"phrase": "比如二在一的前面", "pair": [2, 1]}, {"phrase": "反过来", "pair": [4, 5]}],
        knowledgePointIds=["K05"], action="逐对高亮交叉线，按线对计数；用排序参照解释交叉与逆序的等价关系。")
    add(c, "数的是线对，不是交点",
        "我们一对一对地数。二和一是一对，三和一又是一对，零在最后，还要和前面的五个数字各算一对。一共七对。即使好几条线恰好挤在同一个点，也要按线对数，不能把那个点只算一次。",
        "wires", [START], countPairs=True, formula="τ = 2 + 5 = 7    （包含空格 0）", reaction="数线对！",
        focusPairs=[{"phrase": "二和一是一对", "pair": [2, 1]}, {"phrase": "三和一又是一对", "pair": [3, 1]}]
                   + [{"phrase": "零在最后", "delay": i * 0.55, "pair": [value, 0]} for i, value in enumerate([2, 3, 1, 4, 5])],
        note="多线共点不减少逆序数；高亮依次列举实际逆序对。", knowledgePointIds=["K05", "K09"],
        action="枚举7个逆序对并依次高亮相应两条线；强调零同样参与计数。")
    add(c, "把这个数叫作逆序数",
        "这个交叉线对数，就叫逆序数。它把一长串数字的顺序，压缩成了一个整数。小棋盘直接两两比较就够了；如果数字很多，可以用归并排序一边排序一边计数，不必把所有线真的画出来。",
        "wires", [START], formula="τ = #{(i,j) : i < j 且 aᵢ > aⱼ}",
        note="两两比较 O(n²)；归并计数 O(n log n)。索引与空格标签 0 含义不同。", knowledgePointIds=["K05"],
        action="保留交叉图，只新增名称与定义；计算复杂度进入次层注释，不另开一节算法课。")
    add(c, "目标也能接到同一个装置上",
        "把输入换成目标，一、二、三、四、五、零。前面五个数字已经依次排好了，只有末尾的零还和它们各交叉一次，所以是五。当前是七，目标是五，数值不一样。看来，逆序数本身还不能直接当通行证。",
        "wires", [GOAL], reveal=True, formula="当前 τ = 7    ｜    目标 τ = 5", knowledgePointIds=["K09"],
        action="同一连线装置换目标输入，读出5；从两个读数不同提出需要研究合法动作如何改变读数。")

    c = "03  对换：只追踪奇偶"
    add(c, "先交换相邻两个数字",
        "要知道逆序数怎样变化，先做一个纸面实验：交换相邻的两项。它们和外面数字的前后关系没变，只是彼此的次序反了。原来交叉就解开，原来不交叉就交叉，逆序数因此只会加一或减一。",
        "swap", [[1, 2, 3, 4, 5, 0], [2, 1, 3, 4, 5, 0]],
        formula="相邻对换：τ 改变 ±1 → 奇偶翻转", knowledgePointIds=["K06"],
        note="这里是排列上的抽象对换，不是在示范允许任意拿起滑块。",
        action="在展开排列上交换1、2，线端点连续移动；明确抽象对换与合法滑动不同。")
    add(c, "隔得远，也还是翻一次奇偶",
        "如果两项隔得远呢？把左边这一项一路挪过去，再把另一项挪回来。隔了三格，可以拆成五次相邻对换；隔了四格，就是七次。无论隔多远，这个次数总是奇数，所以最后的奇偶一定翻转。",
        "swap", [[1, 2, 3, 4, 5, 0], [2, 1, 3, 4, 5, 0], [2, 3, 1, 4, 5, 0],
                 [2, 3, 4, 1, 5, 0], [2, 4, 3, 1, 5, 0], [4, 2, 3, 1, 5, 0]],
        moveCues=[{"phrase": "隔了三格", "delay": delay} for delay in (0, 0.85, 1.7, 2.55, 3.4)],
        formula="相距 d 个位置的对换 = 2d − 1 次相邻对换", knowledgePointIds=["K06"],
        note="分解发生在抽象排列中；不声称这些中间步骤都是拼图的合法滑动。",
        action="线端点交换1、4；显示d=3与2d−1=5的关系，强调只追踪奇偶。")
    add(c, "不必记住差了多少",
        "我们刚刚丢掉了一些信息，却得到一个更稳的规则。不再追踪逆序数究竟增了几、减了几，只问它是奇还是偶。只要交换任意两项，这个开关就翻转一次。复杂的数字变化，变成了一个很简单的动作。",
        "swap", [[4, 2, 3, 1, 5, 0], [1, 2, 3, 4, 5, 0]],
        formula="任何两项对换 → 逆序奇偶翻转", reaction="只记一个开关",
        knowledgePointIds=["K06"], action="对换回原状态，交叉数再次改变，保留奇偶翻转结论。")
    add(c, "真正的滑动，恰好也是对换",
        "现在把零重新折回棋盘。每一次合法滑动，无非就是零和旁边那一块交换位置。无论它们在展开排列里挨着，还是隔着一整行，都是两项对换。所以每滑一步，逆序数的奇偶必定翻转。",
        "parity", [START, [2, 3, 0, 4, 5, 1], START], formula="合法滑动：0 与相邻滑块对换 → τ 的奇偶翻转",
        knowledgePointIds=["K06", "K07"], action="从纸面对换回到合法棋盘，播放竖直往返，同步更新逆序奇偶读数。")
    add(c, "横着走、竖着走，都一样",
        "你可以试试横着滑，再试试竖着滑。逆序数的具体变化可能不同，但奇数和偶数总在轮流出现。这还不算不变量，毕竟它一直在变。可如果我们再找一个同样每步都翻转的开关，会发生什么？",
        "parity", [START, [2, 3, 1, 4, 0, 5], [2, 0, 1, 4, 3, 5]],
        formula="一个会翻转的量，还不是不变量", reaction="再找一个开关",
        knowledgePointIds=["K07"], action="真实横移再竖移；由逆序奇偶持续变化，引出第二个开关。")

    c = "04  空格颜色：让两个开关抵消"
    add(c, "把棋盘涂成两种颜色",
        "给棋盘像国际象棋那样，深浅交替地涂色。空格每次只能上下左右走，走到的必然是另一种颜色。于是我们不用数路径，光看空格在哪一种颜色上，就又得到一个每步都翻转的开关。",
        "parity", [START, [2, 3, 1, 4, 0, 5], [2, 0, 1, 4, 3, 5], [0, 2, 1, 4, 3, 5]],
        formula="空格走一步 → 棋盘颜色翻转", knowledgePointIds=["K07"],
        action="棋盘深浅交替，空格路径连续三步，每步同步显示颜色0/1。")
    add(c, "颜色也能写成一个式子",
        "从左上角开始，把行号和列号都从零计数。行号加列号，偶数是这一种颜色，奇数是另一种。比如右下角在第二行、第三列，用从零开始的坐标写，就是一和二，相加得到三。",
        "parity", [START], formula="颜色 = (r + c) mod 2    ｜    右下角：(1 + 2) mod 2 = 1",
        note="坐标从 0 开始；改用其他一致的坐标原点时，须同时重算当前与目标。",
        knowledgePointIds=["K07", "K09"], action="固定空格右下角，显示r+c=3和颜色1，说明0基坐标。")
    add(c, "两个一起翻，合起来就不变",
        "把逆序奇偶和空格颜色放在一起看。滑一步，前者翻一次，后者也翻一次；如果只看两者相加后的奇偶，就等于翻了两次，回到原来的状态。我们终于得到一件滑块怎么动都不会改变的东西。",
        "parity", [START, [2, 3, 0, 4, 5, 1], [2, 0, 3, 4, 5, 1], [0, 2, 3, 4, 5, 1]],
        formula="I = (τ + r + c) mod 2", reaction="两个变化抵消了",
        knowledgePointIds=["K07"], action="三次合法滑动，前两行开关同时翻，合成行始终0；公式从读数关系产生。")
    add(c, "不变的是奇偶，不是那个总和",
        "注意，我们保住的是最后这个零或一，不是前面那个整数总和。逆序数和坐标和都可以改变，两个加起来也可以改变。只是它们总在同一类奇偶里跳，所以这张通行证一直没有换过。",
        "parity", math["states"][:5], formula="τ+r+c 可以变化；I 只保留奇偶，始终不变",
        knowledgePointIds=["K07"], action="沿真实路径回放，显示不同整数读数与相同合成标记，避免把整数和误称不变量。")
    add(c, "不同标记，一步也跨不过去",
        "这下片头的机器就有道理了。起点的标记，走一步不会变，走一百步也不会变。如果目标拿着另一种标记，你再怎么绕，也进不了它的圈子。我们不用真的搜遍所有路线，就能断定这条路不存在。",
        "parity", [BAD], formula="当前 I = 1    ≠    目标 I = 0    →    不可达", reaction="不是没找到，是到不了",
        knowledgePointIds=["K08"], action="反例输入返回同一装置；以不变量递推解释不可达，不能仅说搜索失败。")
    add(c, "相同标记，什么时候就够了？",
        "反过来，相同标记就一定有路吗？对于至少两行两列、没有障碍、每块数字各不相同、只有一个空格的完整矩形拼图，确实可以。这是滑块拼图的可达性结论；刚才的每步不变，只证明了不能跨类，还没有单独证明这一半。",
        "parity", [START], formula="完整矩形，行列均 ≥ 2：同一 I ⇔ 同一可达类",
        note="条件：互异滑块、一个空格、上下左右移动；不直接推广到一维、障碍棋盘。",
        knowledgePointIds=["K08"], action="把充分性定理和不变量必要性区分；主层保留装置，次层列条件。")
    add(c, "小例子，可以把每条边都查一遍",
        "对这里的六格棋盘，我们还能做一次彻底核对。六个对象有七百二十种排列，计算机沿合法边把它们全部分组，得到两个各三百六十个局面的部分，和这个标记完全一致。它核验了本例，但不代替任意大棋盘的证明。",
        "parity", [START], formula="2×3：720 个排列 = 360 + 360    ｜    逐态核验与 I 一致",
        note="完整枚举核验文件：math-verification.json；一般结论有独立的适用条件。",
        knowledgePointIds=["K08"], action="把完整有限枚举结果放回判别器，明确枚举证据范围。")

    c = "05  装回开场：先判别，再找路"
    add(c, "把三件零件装回去",
        "现在重新看开头的装置，每个零件都认识了。棋盘摊成一排，连到排序位置，交叉线对数是七；空格在一行二列，坐标和是三；七加三是十，留下奇偶，读出零。它不再是一个凭空出现的公式了。",
        "wires", [START], reveal=True, countPairs=True,
        focusPairs=[{"phrase": "棋盘摊成一排", "delay": i * 0.5, "pair": pair}
                    for i, pair in enumerate([[2, 1], [3, 1], [2, 0], [3, 0], [1, 0], [4, 0], [5, 0]])],
        formula="当前：τ = 7，r+c = 3，I = 10 mod 2 = 0", reaction="零件都齐了",
        knowledgePointIds=["K09"], action="重新逐条画出片头连线，将已建立的交叉计数与空格颜色合成。")
    add(c, "目标与反例，用同一把尺",
        "目标的逆序数是五，空格还在同一个地方，五加三是八，也是零。再看只把一和二调换的反例，逆序数变成六，六加三是九，读出一。同一把尺，不用给每一道拼图重新编一套理由。",
        "parity", [BAD], formula="目标：5+3 → 0    ｜    原例：7+3 → 0    ｜    反例：6+3 → 1",
        knowledgePointIds=["K08", "K09"], action="沿用同一合成装置对照三个实算值；不同类不可达，本例同类可达。")
    add(c, "知道有路，还不等于知道怎么走",
        "原来的那局和目标同类，所以我们可以放心找路了。但标记并不会告诉你下一步往哪儿滑，也不保证你随便绕就能成功。它负责的是先排除不可能，剩下的具体路线，要交给另一件工具。",
        states=[START], goal=GOAL, labels=[], formula="判别可达性 ≠ 找到路线 ≠ 找到最短路线",
        reaction="接下来轮到找路", knowledgePointIds=["K02", "K08"],
        action="原棋盘与目标重新并列，用已判同类的结果引出状态图搜索。")
    add(c, "一个局面，画成一个点",
        "把整个棋盘当成一个节点，能一步滑到的局面，就用边连起来。这样，一道拼图变成了一张路网。边上没有传送门，每一条都对应零和相邻滑块交换一次，找解就是在这张图里找一条路。",
        "search", [START], formula="局面 → 节点    ｜    合法滑动 → 边", knowledgePointIds=["K02"],
        action="从真实起点生成前三层合法状态图，逐个长出节点和实际邻接边。")
    add(c, "一层一层向外铺",
        "最直接的找法，是先看一步能到哪里，再看两步、三步。第一次走到目标时，前面更短的路线都已经查过了。如果每条边都算一步，这种广度优先搜索，找到的就是最短步数。",
        "search", [START], formula="BFS：深度 0 → 1 → 2 → 3 → …", knowledgePointIds=["K02"],
        note="最短性条件：每次合法滑动代价相同；搜索层示意只画前三层。",
        action="按深度逐层展开真实邻接图，展示等步长BFS的最短性。")
    add(c, "旧地方，不必反复走",
        "不过，刚滑过去又滑回来，是同一个局面，不能当成一个新世界继续展开。给每个见过的局面做个记号，重复的就跳过。否则，计算机也会像我们一样，在一个小圈子里忙得很认真，却哪儿都没去。",
        "search", [START], formula="维护已访问集合，重复局面不再入队", reaction="别把绕圈当进展",
        knowledgePointIds=["K02"], action="由真实去重状态图说明避免重复；所有显示节点用数组身份去重。")
    add(c, "一路钻下去，和挑着找",
        "也可以沿一条路一直试，走不通再退回来，这叫深度优先，通常不保证最短。想让搜索更有方向，可以给局面一个估计：已经走了几步，加上每块数字离目标还差多少。这里空格不算进距离。",
        "search", [START], formula="A*：f = g + h    ｜    h = 各数字块的曼哈顿距离和（不计 0）",
        note="DFS 需防环；A* 用 g+h 与正确的去重/更新策略；仅挑 h 最小是贪心搜索。",
        knowledgePointIds=["K02"], action="保留状态图，侧层比较DFS/BFS/A*；不把只看接近程度误说成完整A*。")
    add(c, "这一次，最短路线是十四步",
        "这块六格拼图不用复杂估计，广度优先就能找到十四步的路线。接下来只看棋盘：每一次移动都让一块数字滑入空格，已经造好的标记继续留在旁边。路线在变，局面在变，它仍然读出零。",
        "route", math["states"][:6], goal=GOAL, pathOffset=0, totalSteps=14, formula="BFS 核验：最短 14 步    ｜    全程 I = 0",
        moveCues=[{"phrase": "接下来只看棋盘", "delay": delay} for delay in (0, 1.0, 2.0, 3.0, 4.0)],
        knowledgePointIds=["K02", "K09"], action="开始14步真实路径前5步，旁白介绍完整长度；计步器显示当前播放片段步数。")
    add(c, "让路线自己说话",
        "先把空格绕到左边，再把中间几块依次带出来。看着像是离目标更远了一点，但这是为了给后面的移动腾位置。一个局部更整齐的选择，未必是通向最终结果的那一步。",
        "route", math["states"][5:11], goal=GOAL, pathOffset=5, totalSteps=14, formula="同一条已验证路线：第 5 → 10 步    ｜    不凭“看起来更近”选路",
        knowledgePointIds=["K09"], action="延续原路径中间5步，不从起点重来；强调临时退让与真实空间。")
    add(c, "最后四步，回到目标",
        "空格来到左上角，一、二先后归位，再给三留出最后的位置。现在右边的目标，和左边的棋盘一样了。刚开始那张写着零的通行证没有承诺捷径，但它判断这条路存在；这十四步，把存在变成了看得见的路线。",
        "route", math["states"][10:], goal=GOAL, pathOffset=10, totalSteps=14, formula="第 10 → 14 步：到达 1 2 3 / 4 5 0", reaction="拼回来了",
        moveCues=[{"phrase": "空格来到左上角"}, {"phrase": "一、二先后归位"},
                  {"phrase": "一、二先后归位", "delay": 0.85}, {"phrase": "再给三留出最后的位置"}],
        knowledgePointIds=["K09"], action="继续最后4步到目标，原棋盘、目标和I读数同时保留，回收片头问题。")

    c = "06  带走一件工具"
    add(c, "拼图背后，是两个互不相通的世界",
        "从四格拼图里保留下来的循环次序，到展开排列的交叉，再到两个会一起翻转的开关，我们把滑动规则做成了一台小小的判别器。以后遇到怎么都拼不好的局面，先别怀疑手速，算一算，它是不是从一开始就在另一个世界。",
        "parity", [START, [2, 3, 0, 4, 5, 1], START],
        formula="I = (逆序数 + 空格行号 + 空格列号) mod 2", reaction="先判别，再动手",
        knowledgePointIds=["K07", "K08"], action="只做一次结尾收束，重用已经构造的棋盘和判别器，最后两次滑动I保持0。")
    add(c, "制作与参考",
        "本期的内容线索来自白绮的滑块拼图视频，演示组织参考真理院七叶的计算尺与列线图。图形和旁白在这里重新制作。人物暂用图片占位，配音使用晓晓。完整的数学核验、制作稿和字幕，随工程一起保留。",
        "credits", labels=["滑块拼图：先造一台可达性判别器", "内容参考：白绮 Infinity · BV1AV411V7SJ", "演示组织参考：真理院七叶 · BV1i4aS6SEBR",
                            "原创图形 / Java 动画 / Edge TTS 晓晓", "人物图片：用户提供的临时占位素材", "工程：vivhite_video_framework · GPL-3.0-only"],
        formula="数学数据、完整文案、字幕与渲染记录均随本次制作保留", note="未使用参考视频原画面、原配音或音乐；画面字体依赖本机 Microsoft YaHei。",
        action="完整展示来源、制作方式与占位身份；不冒用原作者旁白、角色或发布身份。")

    # Explicit provenance and coverage are inputs, never a fabricated human style approval.
    sources = {point["id"]: point["sourceSegmentIds"] for point in analysis["contentAnalysis"]["knowledgePoints"]}
    for beat in beats:
        beat["sourceSegmentIds"] = sorted({segment for point in beat["knowledgePointIds"] for segment in sources[point]})
    covered = {point for beat in beats for point in beat["knowledgePointIds"]}
    if not set(sources).issubset(covered):
        raise ValueError(f"Missing content: {set(sources) - covered}")
    if voice != "zh-CN-XiaoxiaoNeural":
        beats[-1]["narration"] = beats[-1]["narration"].replace("配音使用晓晓。", "配音使用当前配置的声音。")
        beats[-1]["labels"] = [line.replace("Edge TTS 晓晓", "Edge TTS / " + voice) for line in beats[-1]["labels"]]
    return {"schemaVersion": "vivhite-production-1", "caseId": "puzzle-restyle", "revision": 2,
            "title": "拼图怎么都拼不回去？先造一台数学判别器", "width": 1920, "height": 1080, "fps": 30,
            "fontFamily": "Microsoft YaHei UI", "videoCodec": video_codec,
            "voice": {"provider": "edge-tts", "name": voice, "rate": rate, "pitch": "+0Hz", "volume": "+0%"},
            "presenter": {"source": "supplied_separately", "role": "teaching_pointer", "replacement": "image_or_prerendered_video"},
            "provenance": {"analysisSha256": hashlib.sha256(analysis_bytes).hexdigest(),
                           "styleProfile": str(style_file.relative_to(ROOT)).replace("\\", "/"),
                           "styleProfileSha256": hashlib.sha256(style_file.read_bytes()).hexdigest(),
                           "mathVerificationSha256": hashlib.sha256(math_path.read_bytes()).hexdigest(),
                           "contentVideoSha256": sorted(expected), "authoring": "assistant_authored_v2",
                           "styleSimilarity": "pending_viewer_feedback"}, "beats": beats}


def find_hashes(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from find_hashes(item)
    elif isinstance(value, list):
        for item in value:
            yield from find_hashes(item)
    elif isinstance(value, str) and len(value) == 64:
        yield value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("analysis", type=Path)
    parser.add_argument("math", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    parser.add_argument("--rate", default="+8%")
    parser.add_argument("--video-codec", default="h264_nvenc", choices=["libx264", "h264_nvenc"])
    args = parser.parse_args()
    plan = compose(args.analysis, args.math, args.voice, args.rate, args.video_codec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"Composed {len(plan['beats'])} action beats")
