# 视频制作任务交接：puzzle-restyle

更新日期：2026-10-26。分析与导演稿实现基线：`76e1435`，位于 `main` 分支；该提交之后的变更以新会话实际读取的工作区为准。

本交接用于下一会话继续完成：消费现有导演稿，实现可复用的视频制作流程，输出《这块拼图真的无解吗？用两个奇偶开关判断滑块拼图》的完整首版视频。

## 1. 接手后先明确的状态

- 已有完整首版导演稿：20 镜，计划 12 分 20 秒，含原创旁白、画面、屏幕文字、动作顺序、音频与停顿安排。
- 已有内容分析、风格分析和独立数学验证；本例由本地媒体处理加当前会话助手辅助分析完成。
- 待实现：动画渲染、配音、字幕与音画同步、成片合成、成片检查及可重复执行的制作入口。
- 当前 `video-maker` 的 `render` 命令只校验并导出导演稿 JSON/Markdown，**不生成视频**。`scripts/run-puzzle-case.ps1` 也只运行到导演稿。
- 当前用户要求交接文档；本文件描述的是后续视频制作任务，当前尚无已完成的成片或技术样片。

## 2. 必读材料与阅读顺序

以下路径均相对仓库根目录。

| 顺序 | 材料 | 用途 |
| --- | --- | --- |
| 1 | [AGENTS.md](../AGENTS.md)、[根 README](../README.md) | Java 21、父 POM、模块边界、GPL-3.0-only、验证及默认自动提交推送约定 |
| 2 | [制作器 README](../video-maker/README.md) | 已实现的命令、导演稿契约、当前能力边界 |
| 3 | [完整导演稿](../video-maker/docs/cases/puzzle-restyle/director.md) | 逐镜阅读，理解全片叙事与具体制作要求 |
| 4 | [原创稿源文件](../video-maker/examples/puzzle-restyle/director-template.json)、[绑定后的导演数据](../video-maker/docs/cases/puzzle-restyle/director.json) | 前者用于修改创作稿；后者为当前已绑定分析指纹的结构化快照 |
| 5 | [案例分析说明](../video-analyzer/docs/cases/puzzle-restyle/README.md)、[分析摘要](../video-analyzer/docs/cases/puzzle-restyle/analysis-summary.json) | 内容主线、风格规则、证据位置、改编决策与分析局限 |
| 6 | [数学验证](../video-analyzer/docs/cases/puzzle-restyle/math-verification.json) | 原例 14 步路径、行尾两块的合法动作、枚举规模 |
| 7 | [2×2 全状态图](../video-analyzer/docs/cases/puzzle-restyle/puzzle-2x2-graph.json)、[2×3 全状态图](../video-analyzer/docs/cases/puzzle-restyle/puzzle-2x3-graph.json) | 状态图动画的数据，按需读取，不以模型猜测替代合法邻居 |
| 8 | [第三方声明](../THIRD-PARTY-NOTICES.md) | 现有依赖与模型来源；新增配音、字体、音乐和渲染依赖时补充声明 |

需要追查原视频证据时，再读 [逐窗分析注释](../video-analyzer/examples/puzzle-restyle/review-notes.json)、[分析器 README](../video-analyzer/README.md) 及本地完整报告。[早期分析设计](../video-analyzer/docs/BV1AV411V7SJ-analysis-design.md) 是目标设计和框架调研，当前实施情况以案例说明与代码为准。

## 3. 本地工作区与仓库外材料

当前机器：Windows / PowerShell。

```text
代码仓库：D:\workspace\vivhite_video_framework
GitHub：https://github.com/XenoAmess/vivhite_video_framework
案例工作目录：D:\workspace\vivhite-analysis-output\puzzle-restyle
建议后续制作目录：D:\workspace\vivhite-analysis-output\puzzle-restyle\production
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

这些运行产物、虚拟环境、模型和原始视频不在 Git 中。同一机器的新会话可直接复用；换机器时，建议另行复制整个案例工作目录，按根 README 重建环境。继续视频制作最直接的输入是导演数据、数学验证数据，以及用于保持来源可追溯的完整 `analysis-report.json`。

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
| `video-maker` / `.maker` | Java 导演任务导出、模型请求入口、导演稿校验和 JSON/Markdown 导出 | 在此模块继续建立制作和渲染流程 |
| 模型语义层 | 本例由助手阅读完整机器转写与联系表，写逐窗摘要、关键修订、风格规则及原创导演稿 | 下一会话负责把镜头要求细化为可执行画面，判断阅读节奏与表达质量 |
| 本地计算层 | 完整媒体解码、识别、数学枚举、路径搜索、结构与引用检查 | 渲染、配音处理、字幕生成、合成及可测量的成片检查 |

优先阅读的代码入口：

- [DirectorMain.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorMain.java)：当前 CLI。
- [DirectorScript.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorScript.java)：导演稿校验与导出。
- [DirectorPlanner.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/DirectorPlanner.java)：模型任务导出及 API 调用。
- [SlidingPuzzle.java](../video-analyzer/src/main/java/com/xenoamess/vivhite_video_framework/analyzer/SlidingPuzzle.java)、[PuzzleExample.java](../video-analyzer/src/main/java/com/xenoamess/vivhite_video_framework/analyzer/PuzzleExample.java)：数学验证与动画用数据生成。

渲染后端尚未选定。接手会话应根据当前环境和镜头需求调研、选择后端，保持 Java 调度、清晰的数据契约与可独立运行的 worker 边界。需要新依赖时核对官方文档和许可证。

## 5. 已有分析的范围

两片完整音轨已机器转写，共 1002 段；连续解码 58,808 帧，语义输入为贯穿全片的 415 张选帧、35 张联系表。已编写内容片 35 窗、风格片 32 窗的上下文摘要。

这次实际采用 `assisted` 导入。独立 Responses API 分析/导演稿入口已实现，但实跑时没有配置 API 凭据，尚未联网端到端验证。新会话按实际环境检查凭据，不假设有可用的模型或配音服务。

逐句条目只有关键句被改写，其余保留 ASR 和疑点标记；逐句回听校准、第二 ASR、全部字幕/公式识别、完整人工听音和逐帧语义审查仍待完成。已确定的制作决策可以复用；影响新片数学含义的疑点应在制作前解决。配音声线、背景音乐及停顿是新方案，不是经过完整听音确认的参考片特征。

## 6. 后续制作要求与数学约束

### 内容与表达

内容来自 BV1AV411V7SJ：滑块拼图的搜索、复原策略和奇偶不变量。风格来自 BV1i4aS6SEBR：先操作后解释、纸色背景、细线图形、固定颜色职责、对象连续变换、章节卡和结论条。

全片画面与旁白按现有 20 镜推进。计划规格为 1920×1080、30fps；12:20 是导演预算，实际配音后可调整镜头时间，同时更新结构化导演稿与导出文件。优先制作干净的二维数学动画。图形、角色和音频使用新建或授权素材，片尾分别注明内容与表达参考来源。

可先选择棋盘滑动、逆序计数、双灯不变量等代表镜头做总计 60–90 秒的技术样片，检查清晰度与音画同步；验证后继续完成整片。样片可由多个镜头节选组成，正式视频仍按 01–20 镜的完整叙事排列。

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

在仓库根目录执行。当前已有的验证记录为 9 个 Java 测试及 1 个真实编解码 Python 集成测试通过；新实现按影响范围补充验证。

```powershell
.\mvnw.cmd clean verify
video-analyzer/.venv/Scripts/python.exe -m unittest discover -s video-analyzer/tools -p test_media_worker.py -v
```

环境安装见根 README。同机已有媒体产物时，如需重建分析包和导演稿，可运行：

```powershell
.\scripts\run-puzzle-case.ps1 -Build
```

首次重建媒体证据时使用 `-Extract`；需要原视频、Python 环境和模型，内容片 OCR 较慢。已有人工注释绑定源文件指纹与语音段 ID，换视频或重新识别导致切分变化时应重新核对注释及引用。

修改旁白、镜头或时间后，以 `director-template.json` 为稿源，绑定当前完整分析报告再导出：

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

下一会话交付完整首版视频时，应同时提供：

1. 可播放的完整 MP4，覆盖全部 20 镜知识内容，数学、文字和动作正确；建议 H.264 视频、AAC 音频、1080p、30fps。
2. 清晰普通话配音、与实际配音对齐的字幕文件及成片字幕；公式与字幕使用各自阅读区域。
3. 可重复运行的制作入口、配置、素材来源记录和实际时间轴；支持分镜重做及失败定位。
4. 本地产物保存在 `production/` 等仓库外目录，包括成片、字幕、音轨、中间产物及制作清单；源码、配置示例、原创稿和说明纳入 Git。
5. 整片检查记录：片头片尾、镜头衔接、每个数学演示、字幕可读性、音画同步、源引用和素材署名。结构校验、实际渲染、机器检测、人工/模型观看分别记录。
6. 新增实现对应的检查通过，文档说明实际运行方法与仍存在的局限，按 `AGENTS.md` 自动提交并推送。

历史工时粗估为首版 16–24 工程工时、较精细版本 30–50 工时，仅作规划；技术样片完成后按实际后端和同步效果更新估算。

## 9. 可复制给下一会话的指令

```text
请接手 D:\workspace\vivhite_video_framework，先阅读 AGENTS.md 和
docs/video-production-handoff.md，并按交接文档的顺序阅读导演稿、分析和数学验证数据。

目标：在现有分析与导演稿基础上，实现可重复执行的视频制作流程，完成 puzzle-restyle
全部 20 镜的首版视频，包含二维数学动画、普通话配音、字幕和成片合成。

当前 video-maker 的 render 只输出导演稿 JSON/Markdown；动画、配音和成片渲染尚待实现。
请复用现有分析、原创导演稿和已验证的数学动作，先核对本地产物与环境，选定实现方案，
通过代表镜头验证后继续完成整片，交付可运行代码、完整视频及制作/检查记录。

涉及数学内容时，以交接文档中的定义和验证数据为依据；依据实际配音调整时间轴并同步稿源。
遵守项目 Java 主干、模块边界和 GPL-3.0-only 约定。完成任务后按 AGENTS.md 自动提交、推送，
并说明成片路径、复现命令、验证结果和实际未完成项。
```
