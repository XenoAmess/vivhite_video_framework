# 第一期：滑块拼图与奇偶判别器

所属：[数学教育系列 · 逆序数课题](../../README.md)。状态：最新v3完整视频已生成，片长10分55秒、1920×1080、30fps。第一期不追加任意矩形棋盘或 Wilson 一般图定理的完整证明，后续分别由第二、三期承担。

`episode.json` 当前导演稿入口指向v3，最新成片位于仓库外 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3/film.mp4`。见[v3制作记录](docs/production-v3.md)与[完整实测导演稿](docs/director-timed-v3.md)。已交付v2保留为独立历史版本。

| 材料 | 用途 |
| --- | --- |
| [episode.json](episode.json) | 本期 ID、角色 ID、导演稿与制作状态 |
| [case.json](case.json) | 内容源、风格源与本地处理配置 |
| [分析说明](analysis/README.md) | 内容、来源与实际审查覆盖；其中明确首轮分析的局限 |
| [风格复分析](analysis/style-reanalysis-v2.md) | v1 需要改写的原因与 v2 工具构造方法 |
| [v2 实测导演稿](docs/director-v2.md) | 已交付成片的完整旁白、动作与真实时间 |
| [v3制作记录](docs/production-v3.md) | 最新成片位置、哈希、实际字幕/动作/媒体检查与复现命令 |
| [历史v2制作记录](docs/production-v2.md) | 首版成片与原有检查范围 |
| [计划适配器](authoring/compose_production.py) | 从已验证分析与数学证据生成本例制作计划 |
| [制作计划快照](authoring/production-plan-v2.json) | 已交付首版视频的原始输入，保持字节以便核对来源 |
| [v1 历史导演稿](docs/director.md) | 对照风格复分析使用，不是当前制作依据 |

## v3 全量台词修订

已按实际成片的全部39段台词完成文字复审与改稿，修订旁白共3083字符。v3已用实际晓晓音轨重新排程、渲染和全片解码；399段字幕逐段与全文对齐，32个明确动作使用真实词边界。已交付的v2视频、制作计划和实测导演稿保持原样。人格一致性与信息披露按最终文稿、实际计划及人物图片的精确指纹完成双审，文体修改记录不代替通过收据。

| 材料 | 用途 |
| --- | --- |
| [v3 完整导演稿](docs/director-v3.md) | 全部旁白、画面动作、屏幕文字与触发短语 |
| [v3 实测导演稿](docs/director-timed-v3.md) | 本次成片39段的实际时间与执行内容 |
| [39段逐段台词复审](docs/dialogue-review-v3.md) | 按旧成片时码列出全部改前、改后与公开文体依据 |
| [唯一逐段修订稿源](authoring/dialogue-v3.json) | 基于固定 v2 哈希，按段 ID 覆写台词、提示及必要动作短语 |
| [v3 制作计划](authoring/production-plan-v3.json) | 本次实际输入，包含b05真实词时序校准的0.04秒微延迟 |
| [v3 适配器](authoring/compose_production_v3.py) | 复用原数学构造，拒绝缺段、状态覆写或失效触发短语 |
| [文档导出器](authoring/write_dialogue_docs_v3.py) | 从同一新稿源导出完整导演稿与全部改前改后 |

从仓库根目录重建新稿与文档：

```powershell
$episodeRoot = 'series/math-education/inversion-count/episodes/01-sliding-puzzle'
$analysisFile = 'D:/workspace/vivhite-analysis-output/puzzle-restyle/analysis-report.json'
video-maker/.venv/Scripts/python.exe "$episodeRoot/authoring/compose_production_v3.py" `
  $analysisFile "$episodeRoot/analysis/math-verification.json" "$episodeRoot/authoring/production-plan-v3.json"
video-maker/.venv/Scripts/python.exe "$episodeRoot/authoring/write_dialogue_docs_v3.py" `
  "$episodeRoot/authoring/production-plan-v3.json" `
  D:/workspace/vivhite-analysis-output/puzzle-restyle/production-v2-cued/timeline.json
java -jar video-maker/target/video-maker-0.1.0-SNAPSHOT.jar validate-production "$episodeRoot/authoring/production-plan-v3.json"
video-maker/.venv/Scripts/python.exe -m unittest discover -s "$episodeRoot/authoring" -p test_dialogue_v3.py -v
```

无网络检查覆盖39段完整性、数学与来源字段不变、短语存在及顺序、遗漏与越权修改失败，以及14步路线每块数字的真实移动方向。单元测试的合成词边界只验证绑定逻辑；本次另以实际词时间、最终MP4的73张证据帧和完整编码音轨的420段机器转写完成制作检查，不将其描述为人工全片观看或逐句回听。

`analysis-authoring/` 保存辅助分析与复算脚本，`authoring/` 保存本期原创稿源和制作适配器。通用代码与命令说明仍在 [video-maker](../../../../../video-maker/README.md) 和 [video-analyzer](../../../../../video-analyzer/README.md)。

历史原片分析、转写与v2成片位于仓库外 `D:/workspace/vivhite-analysis-output/puzzle-restyle/`；新版制作位于上述系列/课题/本期目录。历史JSON中捕获时的旧路径是来源记录，当前执行入口以本目录及根脚本为准；旧仓库路径不保留兼容入口。

本期角色 ID 为 `vivhite`。后续任何改稿或新制作都须先读取私有角色仓库中的完整人格，再完成[人格一致性与信息披露审核](../../../../../docs/character-workflow.md)。历史成片标记不代表已经通过新增的审核流程。
