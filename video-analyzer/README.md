# video-analyzer：视频分析器

Java 包前缀：`com.xenoamess.vivhite_video_framework.analyzer`。

本模块读取视频，输出带来源指纹、时间窗、全文转写段和画面证据的分析报告。当前 Java CLI 已实现完整媒体任务调度、连续证据包、辅助审查导入、Responses API 审查入口和覆盖校验；本地模型通过 Python worker 运行。

具体案例的分析材料归入[系列 → 课题 → 对应期](../series/README.md)，通用分析程序仍在本模块。为新视频提供建议或审查成稿时，按[角色与文案审核规约](../docs/character-workflow.md)读取所用角色的完整私有人格，分别审查人格一致性和信息披露；不要把角色档案混入公开视频分析报告。

## 实战设计

- [《酸橙色信笺》导演案](../docs/analysis/BV1nB3u6tEHD/director.md)：英文歌曲、实拍与角色混合影像的44个镜群，包含全片证据、识别纠错、辅助审查包和复现入口；尚未完成逐句听音或人工全片验收。
- [BV1AV411V7SJ 全量文案检查与全片审查设计](../series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/BV1AV411V7SJ-analysis-design.md)：包含本地音视频框架调研、全文转写与逐句检查、全片视听审查、制作器输出及覆盖验收。
- [两部视频实跑结果](../series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/README.md)：已完成内容分析、风格提炼与导演稿；说明实际范围及未完成的音频校准。
- [风格复分析 v2](../series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-reanalysis-v2.md)：纠正 v1 对叙事、图形推演、角色和节奏的提炼；后续 v2 已据此重写并成片，实际状态见本期制作记录。

## 当前命令

在仓库根目录安装依赖并构建后：

```powershell
$caseWork = 'D:/workspace/vivhite-analysis-output/puzzle-restyle'
$analyzerJar = 'video-analyzer/target/video-analyzer-0.1.0-SNAPSHOT.jar'
java -jar $analyzerJar prepare series/math-education/inversion-count/episodes/01-sliding-puzzle/case.json $caseWork
```

`prepare` 顺序运行 ffprobe、全文 ASR、全帧解码/变化测量、可选字幕 OCR、完整音轨 RMS，并生成覆盖全时长的 30 秒窗口。`--reuse` 只使用已有产物，检查源文件指纹、模型名称、OCR 开关、取帧间隔与解码覆盖，不重新推理；模型 worker 正常执行时也按输入及参数缓存。每个窗口包含全部相交 ASR 段、所属选帧、字幕观测和 RMS bins。

案例配置可设置 `asrLanguage`（默认 `zh`，英文歌曲使用 `en`）；语言会传给 Whisper 并参与缓存校验，改变语言后需重新转写。直接运行 worker 时使用 `transcribe --language en`。歌曲的延长音、伴奏和多语混唱仍可能造成识别或对齐错误，需要结合画面歌词审查。

产物主要为 `workspace.json`、`content/`、`style/`、`packets/`。视频不复制；原始转写和选帧保存在工作目录。帧间差异大只称为转场候选，不等价于完整镜头检测；5 秒画面与变化候选用于语义输入。OCR 有 200ms 冷却和 1500ms 刷新上限，不能宣称全部字幕都已识别。

```powershell
# 自动语义审查；需本地配置 API key 和支持图像/结构化输出的模型
$env:OPENAI_MODEL = '填入可用模型名称'
java -jar $analyzerJar review $caseWork

# 或导入已经编写的完整辅助审查包
java -jar $analyzerJar import-review $caseWork "$caseWork/review-bundle.json"

# 实战案例数学核验：输出最短路线、行尾两块示例及两种小棋盘全状态图
java -jar $analyzerJar verify-puzzle "$caseWork/math-verification.json"
```

API 使用环境变量 `OPENAI_API_KEY`、`OPENAI_MODEL`；可选 `OPENAI_BASE_URL`（默认 `https://api.openai.com/v1`）、`OPENAI_MAX_REQUESTS`（每次进程默认最多 200 次，重试也计数）。`review` 将每个窗口的转写、OCR、音量数值和所属选帧发送给配置的服务，不发送音轨/视频文件，不具备听音能力；`store=false`。每窗结果按请求内容、端点及图像内容缓存；429/5xx 最多重试 3 次，5 分钟超时，失败保留已完成窗并报错。

`analysis-report.json` 契约版本为 `1.0`：`sourceHashes` 分别标记内容和风格源；`windowReviews` 对应所有窗口和原始语音段 ID；`contentAnalysis.knowledgePoints` 只引用内容源语音段；`styleAnalysis.rules` 只引用风格源窗口/帧；`provenance` 与 `coverage` 记录审查方式及局限。导入验证所有窗口和语音段是否遗漏、重复或错引；结构覆盖通过不保证事实正确，也不将 ASR 索引当作听音核对。

## 分析流程

1. 读取本地视频，提取时长、分辨率、帧率、音轨及其他基础信息。
2. 在本地处理完整音轨、连续画面和全部字幕变化，取得带时间戳的全量转写、画面文字、镜头与视觉事件，形成可追溯的证据。
3. 核对全部文案，并由 GPT 按原顺序逐句检查含义、作用、事实和论证；每句保留检查状态及证据。
4. 逐段覆盖全片视听内容，结合文案审查分镜、创作风格和音画关系，随后跨段归纳主题、叙事及改进建议。
5. 分别记录解码、识别、全文检查、视频语义审查和人工复核的范围，标记事实、推断及缺失信息。短样本仅用于技术校准。
6. 输出完整机器转写、分析报告及制作器消费的结构化报告。当前机器转写仍是待核对文本；逐句听音校准、第二 ASR、强制对齐和每个瞬时事件的语义识别仍待补齐。

## 报告要求

| 维度 | 应包含的信息 | 对制作器的用途 |
| --- | --- | --- |
| 主题与受众 | 主旨、知识点、先备知识、受众、学习目标 | 选题与讲解深度 |
| 分镜与节奏 | 镜头起止时间、景别或版式、画面内容、转场、讲解对应关系 | 分镜模板与时间轴 |
| 文案与叙事 | 带时间戳的文案、开场方式、铺垫、举例、推导、总结 | 文案结构与讲述策略 |
| 视觉风格 | 配色、字体、构图、公式与图形呈现、动画方式 | 可复用的画面及动画配置 |
| 声音与字幕 | 语速、停顿、配音特点、音乐、音效、字幕位置与同步 | 配音、音轨和字幕参数 |
| 质量与优化 | 理解障碍、信息密度、节奏问题、数学表达疑点及改进方向 | 制作检查与优化任务 |

每条关键结论应关联时间戳或证据。建议应说明依据、具体修改动作、涉及的制作参数、预期效果及优先级；可测量的属性尽量提供数值或范围，无法确认的内容明确标为未知。

可落地建议示例：若连续公式推导导致信息密度过高，标出对应镜头区间，建议拆成几步、每步保留哪些公式、何处增加图形解释及停顿，并给出目标时长范围。报告应将已测量的数据与建议值区分开。

## 模块边界

- 本地分析负责可测量的数据和素材提取；GPT 分析负责语义理解及创作方法归纳，两部分应可分别调用与验证。
- 本地分析阶段可以独立运行；GPT 分析明确报告调用失败、缺失证据和不确定性，不以编造结果补齐报告。
- GPT 凭据由环境或本地配置提供，不写入源码；模型、超时、重试及分析预算在实现时提供配置。
- 输出报告供 `video-maker` 读取，两个模块当前不建立 Maven 依赖。

## 构建

在仓库根目录执行：

```powershell
.\mvnw.cmd -pl video-analyzer -am verify
```

macOS / Linux 使用 `./mvnw -pl video-analyzer -am verify`。Java 入口为 `AnalyzerMain`；案例配置的 Python 路径使用 Windows 格式，其他平台需调整。实际采用 faster-whisper、PyAV/OpenCV、RapidOCR/ONNX Runtime；JavaCV、WhisperX、FunASR 的调研不代表已集成。
