# vivhite_video_framework

以 Java 为主要开发语言，包含自动化数学科普视频制作器和视频分析器两个子项目。分析器提炼参考视频的创作方法，制作器据此制作和优化视频。

## 项目结构

根目录 `pom.xml` 同时作为 Maven 父 POM 与聚合 POM，统一管理 Java 版本、编码和构建插件版本。两个子项目分别拥有自己的目录、POM 和源码。

| 子项目 | 职责 | Java 包前缀 |
| --- | --- | --- |
| [video-maker](video-maker/README.md) | 自动制作数学科普视频，完成选题、数学内容核验、文案、分镜、视听素材及合成渲染 | `com.xenoamess.vivhite_video_framework.maker` |
| [video-analyzer](video-analyzer/README.md) | 读取视频，结合本地分析与 GPT 分析，解读主题、分镜、文案和创作风格，提供可执行的制作建议 | `com.xenoamess.vivhite_video_framework.analyzer` |

- 父 package / Maven groupId：`com.xenoamess.vivhite_video_framework`。
- 父 artifactId：`vivhite-video-framework`；当前版本：`0.1.0-SNAPSHOT`。
- 两个子项目通过带版本标识的分析报告交换信息，目前不互相添加 Maven 依赖。
- 分析报告应将时间戳、关键帧和文案等证据，与风格参数、逐镜头建议及优化动作对应起来，支持制作器模仿创作方法并验证改进效果。

当前已实现从完整媒体处理、内容/风格分析、导演稿到配音、二维数学动画与 MP4 的命令行流程。Java 负责调度、证据与数学校验、图形动画及合成；独立 Python worker 分别运行媒体分析和 Edge TTS。人物先用用户提供的图片占位，可替换为已渲染的视频形象。

视频创作材料按[系列 → 课题 → 多期](series/README.md)组织，当前课题为[数学教育系列 · 逆序数](series/math-education/inversion-count/README.md)：第一期保留已交付内容，第二期证明完整矩形棋盘结论，第三期从头证明 Wilson 一般图定理。案例材料已直接移动到各期目录，原模块下不保留兼容入口。

后续视频任务必须执行[角色参与及文案审核规约](docs/character-workflow.md)：创作前读取独立私有角色仓库中的唯一完整人格文档，成稿后分别审核人格一致性与信息披露。公开项目只保存角色 ID、必要版本引用及审核状态，不保存人格副本。

## 已完成的实战案例

- 内容来源：`BV1AV411V7SJ`，分析滑块拼图的搜索、复原方法与奇偶不变量。
- 风格来源：`BV1i4aS6SEBR`，提炼先操作后解释、持续图形对象、纸色细线与章节/结论条。
- [案例分析与覆盖说明](series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/README.md)。
- [v1 导演草稿](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director.md)：20 镜、计划 12 分 20 秒；风格复核后需要重写。
- [目标片风格复分析与改稿依据](series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-reanalysis-v2.md)：逐段对照、文本密度统计、工具构造主线及 90 秒方向样稿。
- [后续视频制作任务交接](docs/video-production-handoff.md)：下一会话的必读材料、本地产物、实现任务与验收标准。
- [实际视频制作流程](video-maker/docs/production.md) 与 [v2 制作计划](series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/production-plan-v2.json)：39 段新版文案，先展示判别器再逐步构造，消费真实数学状态生成动画。
- [第一期 v3 台词修订稿](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director-v3.md)与[39 段审查及改前改后对照](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)：从真实成片台词修掉模板化表达，重写人物反应、逐步动作与配音触发；尚未重新配音或渲染。

本例完整处理了两部音轨并阅读全部转写，连续解码 58,808 帧；语义画面输入是贯穿全片的 415 张选帧。逐窗摘要由本次助手编写，逐句条目保留 ASR 与关键修订，不是逐句听音校准。本机没有配置 OpenAI API 凭据，实际交付使用 `assisted` 导入路径；独立 API 路径已实现，尚未联网验证。

## 制作完整视频

在已有案例分析产物的本机，安装独立配音环境后执行：

```powershell
uv venv --python 3.12 video-maker/.venv
uv pip install --python video-maker/.venv/Scripts/python.exe -r video-maker/tools/requirements-lock.txt
.\scripts\produce-puzzle-video.ps1 -Build -VideoCodec h264_nvenc
```

默认采用最新 v3 台词，输出到 `production-v3-cued/`；`-Revision 2` 选择历史 v2。无 NVIDIA 编码器时省略 `-VideoCodec`，使用 CPU `libx264`。默认 Edge TTS 晓晓 `zh-CN-XiaoxiaoNeural`，音色、语速、输出目录和人物可由参数改变。首次联网合成旁白，之后按内容哈希复用配音。已交付的 v2 实测片长 11分01.4秒、1080p30，保存在仓库外 `../vivhite-analysis-output/puzzle-restyle/production-v2-cued/`；v3 当前只有新稿及计划，没有新成片。详见 [制作器说明](video-maker/docs/production.md)。

新增的制作前检查会保留本次 `authored-plan.json`，并在缺少匹配的人格/披露审核时停止正式配音与渲染。按[规约](docs/character-workflow.md)实际审阅完整计划与人物素材、导出收据后重试；不需要另行请求用户批准，也不能伪造审核通过。`-PreviewOnly` 可先生成技术预览。

## 重建分析与历史导演稿

先安装 JDK 21、Python 3.12 和带 `ffprobe` 的 FFmpeg，确保 `java`、`ffmpeg`、`ffprobe` 在 PATH 中。在仓库根目录执行：

```powershell
py -3.12 -m venv video-analyzer/.venv
video-analyzer/.venv/Scripts/python.exe -m pip install -r video-analyzer/tools/requirements-lock.txt
.\mvnw.cmd clean verify
.\scripts\run-puzzle-case.ps1 -Extract
```

也可用 `uv venv --python 3.12 video-analyzer/.venv` 和 `uv pip install --python video-analyzer/.venv/Scripts/python.exe -r video-analyzer/tools/requirements-lock.txt` 创建相同环境。首次运行会下载 ASR 模型，OCR 使用安装包内模型；本例以 CPU/int8 实跑，内容片 OCR 需要较长时间。

视频位置及角色见 [案例配置](series/math-education/inversion-count/episodes/01-sliding-puzzle/case.json)。默认将运行产物写到仓库同级 `../vivhite-analysis-output/puzzle-restyle/`，可用 `-WorkDirectory` 改变。已完成媒体提取后，执行 `./scripts/run-puzzle-case.ps1` 即可重建证据包、导入案例注释、核验数学算例和生成导演稿；`-Build` 会先构建。该脚本复用已编写的案例注释，检查两个视频的 SHA-256，不是对任意视频自动套用同一结论。

一般视频的自动模型审查使用分析器 `review` 和制作器 `generate`，需要自行设置 `OPENAI_API_KEY` 与 `OPENAI_MODEL`；不写死模型名称。运行方法、传输范围和失败行为见两个模块 README。`prepare`、案例辅助导入、数学验证及导演稿校验可在没有 API 凭据时运行。

## 构建与验证

需要 JDK 21 或以上版本，编译目标为 Java 21。仓库提供 Maven Wrapper，固定使用 Maven 3.9.16，无需额外安装 Maven；首次执行需联网下载 Maven 和构建插件。

Windows PowerShell：

```powershell
.\mvnw.cmd clean verify
.\mvnw.cmd -pl video-maker -am verify
.\mvnw.cmd -pl video-analyzer -am verify
```

macOS / Linux：

```sh
./mvnw clean verify
./mvnw -pl video-maker -am verify
./mvnw -pl video-analyzer -am verify
```

第一条命令构建并验证全部模块，后两条分别选择单个子项目。两个 `target/*-0.1.0-SNAPSHOT.jar` 均可用 `java -jar` 运行。Java 测试覆盖丢失文案/窗口、错误来源、非法时间轴、过密旁白、模型不完整返回，以及 2×2 / 2×3 全排列数学验证。

Python 的真实编解码集成检查：

```powershell
video-analyzer/.venv/Scripts/python.exe -m unittest discover -s video-analyzer/tools -p test_media_worker.py -v
```

## 开发约定

- 主要语言：Java。
- 文件编码：UTF-8；Java 代码使用 4 个空格缩进。
- Java 版本、公共依赖版本及构建插件配置在父 POM 中统一维护；子项目仅声明自身需要的依赖。
- 自动化协作规范见 [AGENTS.md](AGENTS.md)。完成有文件变更的任务后，默认检查、Git 提交并推送。

## 许可证

本项目采用 GNU General Public License v3.0，SPDX 标识为 `GPL-3.0-only`。完整协议见 [LICENSE](LICENSE)。

Maven Wrapper 脚本保留 Apache License 2.0 授权，协议见 [.mvn/wrapper/LICENSE](.mvn/wrapper/LICENSE)。

新增依赖及模型说明见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
