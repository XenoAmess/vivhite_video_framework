"""Export the full director text and public language review from one v3 source.

All inputs are public text; private character review evidence is never loaded.
GPL-3.0-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from compose_production_v3 import BASE_FILE, HERE, REVISION_FILE


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stamp(seconds: float) -> str:
    return f"{int(seconds // 60):02d}:{seconds % 60:06.3f}"


def director_text(plan: dict) -> str:
    lines = ["# 第一期 v3：完整台词修订导演稿", "",
             "这是基于已交付 v2 的独立改稿，包含全部39段最终拟用旁白和画面文字；尚未重新配音、排程或渲染。第一期不追加第二、三期承担的完整证明。", "",
             "声音暂用 Edge TTS 晓晓；人物仍为图片占位。短操作指令由旁白与现有提示线、高亮配合，不假称已具备 Live2D 表情、动作或口型。", "",
             "段落顺序沿用原39个动作段。以下没有借用 v2 的实测时码；新版时长、停顿与动作完成时间，须在新配音后按真实词边界重新排程。", "",
             "稿源：[逐段修订数据](../authoring/dialogue-v3.json)；执行输入：[v3 制作计划](../authoring/production-plan-v3.json)；修改依据：[全量台词复审](dialogue-review-v3.md)。人格一致性与信息披露的详细复审另存私有库，审核结论须绑定本文件及实际制作计划的各自哈希。", ""]
    for beat in plan["beats"]:
        lines += [f"## {beat['id']} · {beat['heading']}", "", f"章节：{beat['chapter']}", "",
                  "旁白：", "", f"> {beat['narration']}", "", f"画面动作：{beat['action']}", ""]
        if beat.get("formula"):
            lines += [f"主层公式／读数：`{beat['formula']}`", ""]
        if beat.get("labels"):
            lines += ["屏幕文字：", ""] + [f"- {label}" for label in beat["labels"]] + [""]
        if beat.get("reaction"):
            lines += [f"人物旁提示文字：{beat['reaction']}", ""]
        if beat.get("note"):
            lines += [f"次层注释：{beat['note']}", ""]
        if beat.get("moveCues"):
            lines += ["动作触发短语（按序，每次对应一个状态转换）：" +
                      " → ".join(f"「{cue['phrase']}」" for cue in beat["moveCues"]), ""]
        if beat.get("focusPairs"):
            lines += ["连线高亮触发：" + "；".join(
                f"「{cue['phrase']}」+{cue.get('delay', 0):g}秒 → {cue['pair'][0]}/{cue['pair'][1]}"
                for cue in beat["focusPairs"]), ""]
        if beat["knowledgePointIds"]:
            lines += ["知识点：" + "、".join(beat["knowledgePointIds"]) + "。", ""]
        lines += ["状态、目标与来源证据的完整机器字段见制作计划中的同名段落。", ""]
    return "\n".join(lines).rstrip() + "\n"


def review_text(base: dict, plan: dict, revision: dict, timeline: dict) -> str:
    if timeline["planSha256"] != revision["basePlanSha256"]:
        raise ValueError("The historical timing does not belong to the reviewed v2 delivery")
    ids = [beat["id"] for beat in base["beats"]]
    if not (ids == [beat["id"] for beat in plan["beats"]] ==
            [entry["id"] for entry in revision["beats"]] ==
            [beat["id"] for beat in timeline["beats"]]):
        raise ValueError("Director, dialogue review and historical timing must cover the same 39 beats")
    count = sum(len(beat["narration"]) for beat in plan["beats"])
    lines = ["# 第一期 v3：全部实际台词复审与修订", "",
             "本次审查对象是已经制作的第一期实际39段旁白，覆盖100%台词。仓库 v2 制作计划与成片目录 `production-v2-cued/production-plan.json` 的完整 SHA-256 相同，均为 `" + revision["basePlanSha256"] + "`；不能拿早期20镜草稿代替这一基准。", "",
             "文字层面的判断：原稿的模板感较明显。反复用‘机器／通行证／圈子／世界’解释同一结论，又常以‘复杂变简单’‘把存在变成路线’之类概括句收尾。人物多在替课程作说明，实际看图、试操作、发现小问题再继续的反应偏少。逆序数、奇偶不变量与搜索的知识链条本身保留。", "",
             f"修订结果：39段逐段检查并改写，共{count}个旁白字符；删除重复的抽象评价与劝诫，把语气落到正在移动的数字、正在数的线对和当前读数上。保留39段顺序、数学状态、知识点与来源证据；同步修改语音触发短语，末14步逐一核对真实方向。两条过于抽象的屏幕标题也改为具体任务。", "",
             "人物相关创作已先读取独立私有库中的唯一完整人格。详细人格依据及信息披露分析存私有库，公开文件只记录文体改动；本文不充当人格双审通过收据。", "",
             "审核边界：本次完成的是全文语义与动作数据核对，没有重新配音、回听新版声音、观看新版成片，也没有人工验收‘自然度’或目标风格。下面的时间仅定位旧版成片，不能作为新版时码。", "",
             "## 逐段检查", ""]
    for old, new, entry, timed in zip(base["beats"], plan["beats"], revision["beats"], timeline["beats"]):
        start = timed["startFrame"] / timeline["fps"]
        end = (timed["startFrame"] + timed["frames"]) / timeline["fps"]
        lines += [f"### {old['id']} · {new['heading']}", "", f"旧成片定位：{stamp(start)}—{stamp(end)}。", "",
                  f"问题：{entry['issue']}", "", "原台词：", "", f"> {old['narration']}", "",
                  "修订台词：", "", f"> {new['narration']}", "", f"修改理由：{entry['reason']}", ""]
        if old["heading"] != new["heading"]:
            lines += [f"屏幕标题同步修改：‘{old['heading']}’ → ‘{new['heading']}’。", ""]
        if old.get("reaction") != new.get("reaction"):
            lines += ["人物旁提示文字：" + (new["reaction"] if new.get("reaction") else "删除旧提示。"), ""]
        if new.get("moveCues") != old.get("moveCues") or new.get("focusPairs") != old.get("focusPairs"):
            lines += ["同步：动作／连线触发已按新台词更新，具体短语与顺序见完整导演稿和制作计划。", ""]
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("plan", type=Path)
    parser.add_argument("timeline", type=Path, help="The immutable v2 delivery timeline, used only to locate old speech")
    parser.add_argument("--output-directory", type=Path, default=HERE.parent / "docs")
    args = parser.parse_args()
    plan = read_json(args.plan)
    revision = read_json(REVISION_FILE)
    if plan["revision"] != 3 or plan["provenance"]["dialogueRevisionSha256"] != hashlib.sha256(REVISION_FILE.read_bytes()).hexdigest():
        raise ValueError("Regenerate the v3 plan before exporting its director documents")
    args.output_directory.mkdir(parents=True, exist_ok=True)
    for name, content in (("director-v3.md", director_text(plan)),
                          ("dialogue-review-v3.md", review_text(read_json(BASE_FILE), plan, revision, read_json(args.timeline)))):
        (args.output_directory / name).write_text(content, encoding="utf-8", newline="\n")
    print("Exported all 39 revised beats and the complete public language review")
