# 视频制作任务交接：puzzle-restyle

更新日期：2026-10-27。历史分析与导演稿基线为 `76e1435`，风格复分析为 `6d0ecf2`；制作器与完整首版视频已经完成，后续以工作区最新提交为准。

本交接用于下一会话继续优化已生成的视频。当前已先实现 `video-maker` 制作链路，再重写 v2 全文并生成滑块拼图主题的完整首版视频。运行方式见 [制作流程](../video-maker/docs/production.md)，实跑结果见 [成片记录](../video-maker/docs/cases/puzzle-restyle/production-v2.md)。

**最新变化：v2 已按“先借用判别器，再逐步构造并装回原例”的主线重写并渲染。** 完整稿为 [director-v2.md](../video-maker/docs/cases/puzzle-restyle/director-v2.md)，源头是 [案例适配器](../video-maker/examples/puzzle-restyle/compose_production.py) 和 [制作计划快照](../video-maker/examples/puzzle-restyle/production-plan-v2.json)。仍须阅读 [风格复分析 v2](../video-analyzer/docs/cases/puzzle-restyle/style-reanalysis-v2.md)；技术检查和规则引用不能替代风格相似度反馈。

## 1. 接手后先明确的状态

- 已有完整 v1 导演稿：20 镜，计划 12 分 20 秒，含原创旁白、画面、屏幕文字、动作顺序、音频与停顿安排；其风格需要重写，镜头数和时长按新稿重新规划。
- 已有内容分析、风格分析和独立数学验证；本例由本地媒体处理加当前会话助手辅助分析完成。
- v2 为39段、实际661.4秒、1920×1080/30fps，配音为 Edge 晓晓 `zh-CN-XiaoxiaoNeural`。人物使用用户指定的 JPEG 占位，已有可替换的视频人物素材接口；不直接驱动 Live2D。
- 当前 `video-maker` 的 `render` 命令仍只导出历史导演稿；`produce` 才生成视频。`scripts/run-puzzle-case.ps1` 重建 v1 分析/导演历史结果，`scripts/produce-puzzle-video.ps1` 制作 v2 视频。
- 完整视频位于 `D:/workspace/vivhite-analysis-output/puzzle-restyle/production-v2-cued/film.mp4`，附字幕、音轨、实测导演稿、配音缓存和制作收据。没有记录人工完整观看或风格批准。

## 2. 必读材料与阅读顺序

以下路径均相对仓库根目录。

| 顺序 | 材料 | 用途 |
| --- | --- | --- |
| 1 | [AGENTS.md](../AGENTS.md)、[根 README](../README.md) | Java 21、父 POM、模块边界、GPL-3.0-only、验证及默认自动提交推送约定 |
| 2 | [制作器 README](../video-maker/README.md) | 已实现的命令、导演稿契约、当前能力边界 |
| 2a | [制作流程](../video-maker/docs/production.md)、[v2 完整稿](../video-maker/docs/cases/puzzle-restyle/director-v2.md)、[成片记录](../video-maker/docs/cases/puzzle-restyle/production-v2.md) | 实际制作器、当前成片、复现方式及检查范围 |
| 3 | [风格复分析 v2](../video-analyzer/docs/cases/puzzle-restyle/style-reanalysis-v2.md)、[改稿依据](../video-analyzer/docs/cases/puzzle-restyle/style-transfer-v2.json)、[开场方向示例](../video-maker/examples/puzzle-restyle/opening-direction-v2.json) | 新稿优先依据；示例不等于已完成的 v2 导演稿 |
| 4 | [v1 导演稿](../video-maker/docs/cases/puzzle-restyle/director.md) | 对照复分析阅读，识别需要保留的数学信息和需要重排的表达 |
| 5 | [原创稿源文件](../video-maker/examples/puzzle-restyle/director-template.json)、[绑定后的导演数据](../video-maker/docs/cases/puzzle-restyle/director.json) | 前者用于修改创作稿；后者为旧稿已绑定分析指纹的结构化快照 |
| 6 | [案例分析说明](../video-analyzer/docs/cases/puzzle-restyle/README.md)、[分析摘要](../video-analyzer/docs/cases/puzzle-restyle/analysis-summary.json) | 首轮内容分析、证据位置、改编决策与分析局限；风格判断已由 v2 复分析补充 |
| 7 | [数学验证](../video-analyzer/docs/cases/puzzle-restyle/math-verification.json) | 原例 14 步路径、行尾两块的合法动作、枚举规模 |
| 8 | [2×2 全状态图](../video-analyzer/docs/cases/puzzle-restyle/puzzle-2x2-graph.json)、[2×3 全状态图](../video-analyzer/docs/cases/puzzle-restyle/puzzle-2x3-graph.json) | 状态图动画的数据，按需读取，不以模型猜测替代合法邻居 |
| 9 | [第三方声明](../THIRD-PARTY-NOTICES.md) | 现有依赖与模型来源；新增配音、字体、音乐和渲染依赖时补充声明 |

需要追查原视频证据时，再读 [逐窗分析注释](../video-analyzer/examples/puzzle-restyle/review-notes.json)、[分析器 README](../video-analyzer/README.md) 及本地完整报告。[早期分析设计](../video-analyzer/docs/BV1AV411V7SJ-analysis-design.md) 是目标设计和框架调研，当前实施情况以案例说明与代码为准。

## 3. 本地工作区与仓库外材料

当前机器：Windows / PowerShell。

```text
代码仓库：D:\workspace\vivhite_video_framework
GitHub：https://github.com/XenoAmess/vivhite_video_framework
案例工作目录：D:\workspace\vivhite-analysis-output\puzzle-restyle
当前视频制作目录：D:\workspace\vivhite-analysis-output\puzzle-restyle\production-v2-cued
```

交接时已核对以下本地文件存在；新会话应再次检查：

```text
analysis-report.json / .md           完整分析报告，包含逐窗及逐段记录
workspace.json                       两个来源、指纹与 67 个窗口索引
content/、style/                     全文机器转写、选帧、联系表、OCR、音量指标
packets/                             67 个连续证据窗口
review-bundle.json                    辅助分析导入数据
math-verification.json                数学验证及路径
puzzle-2x2-graph.json                 小棋盘完整状态图
puzzle-2x3-graph.json
director/director-plan.json           已绑定分析文件指纹的原创导演计划
director/director.json / .md          已导出的导演稿
director/director-validation.json     导演稿结构校验结果
```

这些运行产物、虚拟环境、模型和原始视频不在 Git 中。同一机器的新会话可直接复用；换机器时复制案例工作目录及人物素材，按根 README 重建环境。v2 目录还包含 `film.mp4`、`subtitles.srt`、`narration.wav`、`timeline.json`、`director-timed.md`、分段与检查记录。配音缓存当前复用 `production-v2/tts-cache`；该目录的旧 `film.mp4` 是同步改进前的中间版本，查看当前成片请使用 `production-v2-cued`。

完整分析报告的文件 SHA-256 被写入导演稿。`analysis-summary.json` 是摘要，不能代替它执行既有导演稿指纹校验；复制完整报告时保留原始字节，避免换行转换造成指纹改变。

源视频路径在 [案例配置](../video-analyzer/examples/puzzle-restyle.case.json) 中：

```text
内容源：
Z:\workspace\bilibili-download-skill\downloads\BV1AV411V7SJ\此视频的所有收益均捐给我用来买拼图 [BV1AV411V7SJ].mkv

风格源：
Z:\workspace\bilibili-download-skill\downloads\BV1i4aS6SEBR\【数学】怎么动动尺子就能算 BMI 和解方程？从计算尺到列线图 [BV1i4aS6SEBR].mkv
```

制作原创图形视频可先使用现有导演稿和验证数据；需要复核原片或重建完整分析时，再访问源视频。原片图像、角色、音轨不是新片已获授权的制作素材。

## 4. 已有架构与可复用代码

项目主干为 Java。父 package / groupId：`com.xenoamess.vivhite_video_framework`；共享父 POM，两个模块当前没有相互添加 Maven 依赖。

| 部分 | 现有实现 | 后续用途 |
| --- | --- | --- |
| `video-analyzer` / `.analyzer` | Java 调度、来源指纹、证据包、报告导入与覆盖校验；Python worker 执行 FFmpeg、faster-whisper、PyAV/OpenCV、RapidOCR | 复用既有分析与数学数据，需要时复核证据 |
| `video-maker` / `.maker` | Java 导演任务、数学动画、配音调度、排程、编码合成、整片解码检查；独立 Python Edge worker | 修改案例适配器、图形或素材后重做对应生产步骤 |
| 模型语义层 | 本例由助手阅读完整机器转写与联系表，写逐窗摘要、关键修订、风格规则及原创导演稿 | 下一会话负责把镜头要求细化为可执行画面，判断阅读节奏与表达质量 |
| 本地计算层 | 完整媒体解码、识别、数学枚举、路径搜索、结构与引用检查 | 渲染、配音处理、字幕生成、合成及可测量的成片检查 |

优先阅读的代码入口：

- [DirectorMain.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorMain.java)：当前 CLI。
- [DirectorScript.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorScript.java)：导演稿校验与导出。
- [DirectorPlanner.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorPlanner.java)：模型任务导出及 API 调用。
- [SlidingPuzzle.java](../video-analyzer/src/main/java/com/xenoamess/vivhite_video_framework/analyzer/SlidingPuzzle.java)、[PuzzleExample.java](../video-analyzer/src/main/java/com/xenoamess/vivhite_video_framework/analyzer/PuzzleExample.java)：数学验证与动画用数据生成。

渲染后端是 Java2D 经 raw BGR 管道送入 FFmpeg，支持 libx264 与 h264_nvenc。当前案例使用后者。新的数学图形类型继续在制作器添加，不把案例叙事写进通用 CLI。参考工程 `Z:/workspace/xar_promo_toolchain` 的配置/执行分离、缓存与检查分层，没有引入它的发布审批流程。

## 5. 已有分析的范围

两片完整音轨已机器转写，共 1002 段；连续解码 58,808 帧，语义输入为贯穿全片的 415 张选帧、35 张联系表。已编写内容片 35 窗、风格片 32 窗的上下文摘要。

这次实际采用 `assisted` 导入。独立 Responses API 分析/导演稿入口已实现，但实跑时没有配置 API 凭据，尚未联网端到端验证。新会话按实际环境检查凭据，不假设有可用的模型或配音服务。

逐句条目只有关键句被改写，其余保留 ASR 和疑点标记；逐句回听校准、第二 ASR、全部字幕/公式识别、完整人工听音和逐帧语义审查仍待完成。已确定的制作决策可以复用；影响新片数学含义的疑点应在制作前解决。配音声线、背景音乐及停顿是新方案，不是经过完整听音确认的参考片特征。

## 6. 后续制作要求与数学约束

### 内容与表达

内容来自 BV1AV411V7SJ：滑块拼图的搜索、复原策略和奇偶不变量。风格来自 BV1i4aS6SEBR：先操作后解释、纸色背景、细线图形、固定颜色职责、对象连续变换、章节卡和结论条。

v2 已按“棋盘回路→顺序与交叉→空格修正→组合标记→可达类别→找路线”建立对象依赖链。规格1920×1080、30fps；39段与11:01.4来自实际配音排程。图形和旁白重新制作，人物为指定占位图；未使用参考片原画面、原配音或背景音乐，片尾分别注明内容与表达参考来源。

后续改进优先基于当前成片反馈与参考片逐段对照，避免仅修改颜色或加速口播。人物目前只做图片出场、位移和指示，不应误写成已完成Live2D口型或表情。切换音色/语速可直接使用脚本参数；新增TTS提供方仍须实现worker适配。

### 必须保持正确的数学信息

- 按行展开棋盘，逆序数 `τ` **包含空格 0**；行列索引 `r,c` 均从 0 开始。
- 不变量为 `I=(τ+r+c) mod2`。保持的是奇偶性；整数和本身可以变化。
- 原例起点 `[2,3,1;4,5,0]` 的 `τ=7`、`r+c=3`、`I=0`；目标 `[1,2,3;4,5,0]` 的 `τ=5`、`I=0`。
- 无解反例 `[2,1,3;4,5,0]` 的 `τ=6`、`I=1`；目标仍为 `I=0`。
- 一次合法动作只交换 `0` 和共边滑块；行尾收尾示例与 14 步最短路径直接消费验证 JSON。序列如 `023451` 的前导 0 必须保留。
- 排列证明中的任意对换或相邻交换，与棋盘合法动作使用不同视觉标签。
- 不变量不同必不可达；相同可达需要额外连通性依据。本例完整枚举 2×2 的 24 态、2×3 的 720 态，分别得到 12+12、360+360；一般尺寸条件与有限枚举分开陈述。
- 适用范围为完整矩形、至少两行两列、一个空格、滑块互异、仅共边移动；一维、有障碍或其他规则单独处理。

## 7. 构建、复用和修改导演稿

在仓库根目录执行。制作器新增4个Java测试与3个Python排程测试，并已真实制作完整视频；详细结果见成片记录。

```powershell
.\mvnw.cmd clean verify
video-analyzer/.venv/Scripts/python.exe -m unittest discover -s video-analyzer/tools -p test_media_worker.py -v
video-maker/.venv/Scripts/python.exe -m unittest discover -s video-maker/tools/tests -v
```

环境安装见根 README。同机已有媒体产物时，如需重建分析包和导演稿，可运行：

```powershell
.\scripts\run-puzzle-case.ps1 -Build
```

该脚本当前重建 v1 历史结果，不会自动应用独立的 v2 风格改稿依据。重新生成时应明确注入新要求，并重新做语义风格对照。

首次重建媒体证据时使用 `-Extract`；需要原视频、Python 环境和模型，内容片 OCR 较慢。已有人工注释绑定源文件指纹与语音段 ID，换视频或重新识别导致切分变化时应重新核对注释及引用。

制作 v2 使用 `scripts/produce-puzzle-video.ps1`，改全文请先修改 `compose_production.py`，同步生成 `production-plan-v2.json`，重做真实配音排程与导演稿快照。以下命令仅用于历史 v1，`director-template.json` 不是当前成片稿源：

```powershell
$caseWork = 'D:/workspace/vivhite-analysis-output/puzzle-restyle'
$analysisFile = "$caseWork/analysis-report.json"
$directorPlan = "$caseWork/director/director-plan.json"

video-analyzer/.venv/Scripts/python.exe video-maker/examples/puzzle-restyle/bind_director.py `
  $analysisFile video-maker/examples/puzzle-restyle/director-template.json $directorPlan

java -jar video-maker/target/video-maker-0.1.0-SNAPSHOT.jar render `
  $analysisFile $directorPlan "$caseWork/director"
```

命令失败时停止依赖该结果的后续步骤。同步更新仓库中的导演稿快照，避免只改 Markdown 后被下一次导出覆盖。

## 8. 完成标准

完整首版视频及后续版本均保留以下交付标准：

1. 可播放的完整 MP4，覆盖经重写导演稿的全部知识内容，数学、文字和动作正确；建议 H.264 视频、AAC 音频、1080p、30fps。
2. 清晰普通话配音、与实际配音对齐的字幕文件及成片字幕；公式与字幕使用各自阅读区域。
3. 可重复运行的制作入口、配置、素材来源记录和实际时间轴；支持分镜重做及失败定位。
4. 本地产物保存在 `production/` 等仓库外目录，包括成片、字幕、音轨、中间产物及制作清单；源码、配置示例、原创稿和说明纳入 Git。
5. 整片检查记录：片头片尾、镜头衔接、每个数学演示、字幕可读性、音画同步、源引用和素材署名。结构校验、实际渲染、机器检测、人工/模型观看分别记录。
6. 新增实现对应的检查通过，文档说明实际运行方法与仍存在的局限，按 `AGENTS.md` 自动提交并推送。

基于 v1 的历史工时粗估为首版 16–24 工程工时、较精细版本 30–50 工时；加入全文改稿后，应依据新稿、实际后端和技术样片重新估算。

## 9. 可复制给下一会话的指令

```text
请接手 D:\workspace\vivhite_video_framework，先阅读 AGENTS.md 和
docs/video-production-handoff.md，并按交接文档的顺序阅读导演稿、分析和数学验证数据。

当前已实现 Java video-maker，并完成 v2 全片。先阅读 video-maker/docs/production.md、
docs/cases/puzzle-restyle/production-v2.md 与 director-v2.md（后两者在 video-maker 下）。
当前成片：D:/workspace/vivhite-analysis-output/puzzle-restyle/production-v2-cued/film.mp4。
依据用户新反馈优化当前成片，继续对照 style-reanalysis-v2.md；不要把旧v1的20镜和12:20当新稿。
文案稿源为 compose_production.py，制作入口 scripts/produce-puzzle-video.ps1。
声音暂用 Edge TTS 晓晓，音色/语速配置可变；人物为用户指定图片，后续可消费渲染视频。
不要把图片占位误说成Live2D或口型已实现。保留真实数学状态、音频排程、字幕与检查证据。

涉及数学内容时，以交接文档中的定义和验证数据为依据；依据实际配音调整时间轴并同步稿源。
遵守项目 Java 主干、模块边界和 GPL-3.0-only 约定。完成任务后按 AGENTS.md 自动提交、推送，
并说明成片路径、复现命令、验证结果和实际未完成项。
```
