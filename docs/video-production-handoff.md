# 视频制作交接

更新日期：2026-10-27。当前已实现 Java `video-maker`，并完成数学教育系列·逆序数课题的三期完整视频。第一期使用去除模板化表达的 v3 台词；第二期完整证明矩形棋盘结论；第三期从头证明 Wilson 一般图定理。接手时以实际成片、实测时间轴和对应稿源为准。

## 当前交付

本机输出根目录为 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/`。各目录包含 `film.mp4`、`subtitles.srt`、`narration.wav`、`timeline.json`、`director-timed.md`、配音/分段缓存、工具快照和媒体检查记录；大型媒体不进入 Git。

| 期数 | 输出子目录 | 实测片长 | 仓库制作记录 |
| --- | --- | --- | --- |
| 1，v3 | `01-sliding-puzzle/production-v3/` | 10:55 | [制作记录](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/production-v3.md) |
| 2，v1 | `02-rectangle-proof/production-v1/` | 18:29.3 | [制作记录](../series/math-education/inversion-count/episodes/02-rectangle-proof/docs/production-v1.md) |
| 3，v1 | `03-wilson-theorem/production-v1/` | 32:24 | [制作记录](../series/math-education/inversion-count/episodes/03-wilson-theorem/docs/production-v1.md) |

三期均为1920×1080、30fps、H.264/AAC，中文字幕已烧录并另附SRT。当前人物是用户指定JPEG占位，配音是 Edge TTS 晓晓 `zh-CN-XiaoxiaoNeural`，基准语速 `+8%`；可修改声音参数及人物素材。现在可消费已渲染的人物视频，不直接驱动 Live2D，也没有图片口型或表情映射。

独立审核摘要见[三期制作复核](three-episode-production-review.md)。技术检查、模型内容审阅、人工整片播放和用户认可风格相似度分别记录，不能互相替代。

## 必读材料

1. [AGENTS.md](../AGENTS.md)、[根README](../README.md)、[默认制作要求](video-production-defaults.md)：Java21、模块边界、默认声音/人物、并发与第一期优先、自动提交推送。
2. [角色与文案规约](character-workflow.md)：创作前完整读取外部私有角色库的唯一人格文档，成稿后分别检查人格一致性与信息披露。不能仅凭哈希、关键词或旧审核继续制作。
3. [课题说明](../series/math-education/inversion-count/README.md)与本期 `episode.json`：内容边界、角色ID和当前产物路径。
4. [制作器README](../video-maker/README.md)、[生产流程](../video-maker/docs/production.md)、[证明场景契约](../video-maker/docs/proof-scene.md)：通用命令、配音提供方、实际词时间、合法动作、缓存和检查。
5. 各期 `authoring/README.md`、制作计划、完整证明和 `docs/production-*.md`：实际稿源、运行命令、指纹和检查范围。第一期另读[逐段台词修订](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)及[风格复分析](../series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-reanalysis-v2.md)。

角色人格只存 `D:/workspace/vivhite_characters` 对应的独立私有GitHub仓库。公开仓库只保留角色ID和审核版本收据；详细审核依据仍在私有库。不得把完整人格或敏感审查理由复制进本项目。文案、人格或实际人物素材改变后，都需重新绑定双项语义审核。

## 复现与并发

在仓库根目录安装环境后先构建制作器，再生产视频：

```powershell
uv venv --python 3.12 video-maker/.venv
uv pip install --python video-maker/.venv/Scripts/python.exe -r video-maker/tools/requirements-lock.txt
.\mvnw.cmd -pl video-maker -am verify

# 第一期默认v3；有NVIDIA编码器时使用此参数
.\scripts\produce-puzzle-video.ps1 -VideoCodec h264_nvenc

# 第二、三期使用各自的编译器和入口
& 'series/math-education/inversion-count/episodes/02-rectangle-proof/authoring/produce.ps1'
& 'series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/produce.ps1'
```

这些命令顺序列出便于复制；实际多期生产可以在独立进程中并行。每期保留独立输出、TTS和分段缓存，并按哈希冻结当前JAR/worker；共享制作器实现与构建要统一协调，发生资源或代码冲突时优先第一期。不要同时向同一输出或TTS缓存写入。

入口先编译计划并保存实际输入，检查该计划、完整人格和外部图片/视频素材的审核绑定，再正式配音渲染。缺审核时按规约完成真实语义审阅，无需新增用户批准流程。`-PreviewOnly` 只生成技术预览。声音、人物、编码器和输出参数见各入口及稿源README；改参数后重新核对实际计划收据。

导演稿时长只是排练预算。先测真实口播，再分配操作及阅读时间，不能把原预算作为硬下限，用几十秒静帧补时。第三期保留全部证明后，按实际配音及合法移动重排为32:24；原49:30预算不再作为交付时长。

## 架构与修改入口

| 层 | 职责与入口 |
| --- | --- |
| 分析器 | Java调度来源指纹、证据包和报告；Python执行FFmpeg、faster-whisper、PyAV/OpenCV、OCR。详见[分析器README](../video-analyzer/README.md)。 |
| 创作层 | 助手阅读完整人格、内容/风格证据，编写和审阅旁白、证明、镜头与可执行计划。各期适配器在 `series/math-education/inversion-count/episodes/<本期>/authoring/`。 |
| 制作器 | [VideoProduction.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/VideoProduction.java)调度实际配音、排程、分段编码、缓存、合成和整片解码；Java2D图形通过raw BGR管道送入FFmpeg。 |
| 证明动画 | [ProofScene.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/ProofScene.java)预计算合法滑动和置换；[ProofCanvas.java](../video-maker/src/main/java/com/xenoamess/vivhite_video_framework/maker/ProofCanvas.java)绘制图、代数层、分阶段表格/矩阵，保留标号身份。 |
| 配音与字幕 | [production_worker.py](../video-maker/tools/production_worker.py)调用Edge、缓存音频与词边界、按视频帧补齐PCM并生成字幕；证明动作使用真实词锚点与操作量排程。 |
| 检查 | [review_film.py](../video-maker/tools/review_film.py)从编码成片提取所有阶段和路径子步结果；全文字幕/配音、数学动作、黑场和响度检查另有绑定成片指纹的报告。 |

当前 `render ANALYSIS DIRECTOR OUT` 只导出历史导演稿；`produce` 才生成完整影片，`preview` 输出技术预览。新的数学主题仍需编写可执行画面及验证程序，不能靠输入任意文案自动得到任意正确动画。

参考工程 `Z:/workspace/xar_promo_toolchain` 是只读架构依据：提供方隔离、内容哈希缓存、失败材料保留及媒体检查分层。没有引入它的发布/人工签字流程，不向参考工程写入。

## 数学与覆盖边界

- 第一期逆序数 `τ` 包含空格0，行列 `r,c` 从0计数，保持 `I=(τ+r+c) mod2`。两种不变量不同一定不可达；相同可达的全尺寸证明放在第二期。2×2/2×3枚举和14步路径不是一般证明。
- 第二期限定有限、完整矩形、至少两行两列、一个空格、互异滑块、仅共边移动；必要性与充分性都进入成片，不以Wilson定理作黑箱。
- 第三期逐项处理图前提、群论引理、耳分解、环及七点例外，相关恒等式和有限证书可复算；不能把有限检验当作一般图定理的证明。
- 图上合法空格边、代数置换的支持连线必须有不同标识。合法路径由制作器预先逐步执行，不能用最终快照代替动作。
- 全片解码、全音轨ASR、全部字幕和数学阶段审阅分别记录。编码证据选帧覆盖所有阶段/动作结果，仍不代表每帧语义审查或人工整片观看。ASR同音误写及静音幻听需结合原字幕、词时间和实际PCM核实，不能直接改成片台词。

## 来源、历史材料与验证

来源视频路径见[案例配置](../series/math-education/inversion-count/episodes/01-sliding-puzzle/case.json)。内容来自BV1AV411V7SJ；表达方法参考BV1i4aS6SEBR。原片图像、声音或角色不自动成为新片素材授权。

原完整分析在 `D:/workspace/vivhite-analysis-output/puzzle-restyle/`：两片全音轨1002段，连续解码58,808帧，语义输入为415选帧/35联系表，35个内容窗和32个风格窗。逐句条目保留ASR及关键修订，没有完成源片逐句回听、全帧语义审阅或完整OCR。实际采用助手辅助导入；独立API路径存在，但未联网端到端验证。源分析和第一期历史v2目录保持原样，当前三期成片请使用本交接首表。

代码验证：

```powershell
.\mvnw.cmd -pl video-maker -am verify
video-maker/.venv/Scripts/python.exe -m unittest discover -s video-maker/tools/tests -v
git diff --check
```

各期完整证明/有限证书另按本期README运行。修改公共POM需验证两个模块；只改文档检查内容、JSON和链接。提交前复核所有实际指纹及私有库可见性，分别提交并推送两个仓库；不要提交媒体、虚拟环境、模型、密钥或完整私人背景。

## 给下一会话的接手指令

```text
请接手 D:/workspace/vivhite_video_framework，先读AGENTS.md、
docs/video-production-handoff.md及docs/video-production-defaults.md。
逆序数课题三期已制成，当前片长10:55、18:29.3和32:24，实际输出路径见交接首表。
先读对应期制作记录、实测导演稿、authoring/README.md，再依据新反馈修改稿源及画面。
创作前完整读取外部私有库中的唯一人格，改完分别复审人格一致性与信息披露，
绑定实际计划和人物素材。默认Edge晓晓、用户指定JPEG占位，声音/人物保留替换配置。
先补齐并验证video-maker再重做影片；并发使用独立目录和冻结工具，冲突时第一期优先。
保留完整证明和真实动作，不用长静帧凑原导演预算。说明机器/语义/人工实际覆盖。
完成后按AGENTS.md自动提交推送，交付实际成片、字幕、检查结果与限制。
```
