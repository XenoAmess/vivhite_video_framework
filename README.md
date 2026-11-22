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

内容子项目[白绮／秋日旅程](series/vivhite/autumn-journey/README.md)已于 **2026-11-22结项，用户表示满意**。最终交付为原始768P v12、原生4K v13及16:9／4:3两张bilibili封面，影片均为205秒／6150帧。经验教训、可复用流程及代码索引见[结项复盘](docs/autumn-journey-retrospective.md)，最新状态见[结项记录](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/project-closeout-20261122.json)。下文各版本的排队、未完成及待审描述保留为历史，不再作为当前任务。

早期v3成片为无对白的多地点自由旅行蒙太奇，48镜、202秒、每镜2–10秒；全员女性，服装贴近白绮，真人不露脸，不允许新增原图没有的无关人员，配合贴纸、玩偶、周边与意象。按用户反馈重做42镜为更接近实拍的普通世界，全部生成与检查图片入库。源片832×480／24fps，最终上采样为1080p30；实际成片、修订与审核覆盖见[制作记录](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v3.md)。

该片新增[片尾修订 v4](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v4.md)：蓝蝶八倍慢放，片尾仅显示“白绮|秋日旅程”“献给最可爱的你”，移除画面制作署名；完整影片和单独片尾另存，v3 完整保留。

配乐的实际旋律、和声、程序合成音色、环境声、混音与复现方式见[《秋日旅程》背景音乐生成说明](docs/autumn-journey-music-generation.md)。202秒与196秒母带均已独立重生成并核对文件指纹一致。

周边印花的首帧稳定、场景原图纹理回贴、慢放候选、全源帧复核与精确时长装配见[视频后处理方法与代码索引](docs/autumn-journey-video-postprocessing.md)，包含适用边界、实际案例和可复用命令。

本地生成式旅行视频后续只制作[原始768P与原生4K](docs/local-video-768p-4k.md)，不再新建2K任务。4K沿用8002接口与历史模型ID，明确请求3840×2160，单任务执行；旧2K资料仅作归档。

已完成[片尾修订 v7的原生768P成片](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v7-768p.md)：48镜、201秒、1344×768／30fps，S20高山湖与S48片尾各连续10秒，其余镜头2–5秒。片尾前两行完全复用片头文字与样式，再缓慢浮现“献给世界上最可爱的你”；6030个最终帧完成解码与画面轨对照。[v7 GitHub Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v7-768p-20261117)供用户审阅。全部2K任务已按用户要求停止，不自动恢复；v6 Release、旧影片与中间材料完整保留。

当前768P交付为[v12骑行车座修订](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v12-S05-saddle.md)：重做00:14—00:19骑行镜头，检查黑色车座、座轨、夹具、座管与坐姿支撑，替换S05后仍为1344×768、30fps、205秒／6150帧，其余47镜、时长、音乐和字幕保持。[v12 Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v12-768p-20261119)中的完整影片及四份附件已完整回下载并核验指纹。对应原生4K使用实际采用的新768P源片进入普通队列，旧无车座4K结论已撤回，禁止回填；完整4K仍在制作。

最终完整4K交付为[v13原生4K版](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v13-4k-20261121)：3840×2160、30fps、205秒／6150帧，全部48段源片完成，含有车座新S05、单序列10秒S20和单序列14秒片尾。35段／38处印花完成场景光照匹配；6150帧成片已完整解码、逐帧图册复核并核对音轨和字幕，六个Release附件实际完整回下载、核验摘要。原768P、旧4K审核版及全部失败和中间材料保留。检查范围及限制见[完整制作记录](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v13-native-4k.md)；2026-11-22用户已在项目层面确认满意并结项，不追溯扩大此前检查范围。

历史[v10左手反手拉帘修订](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v10-left-hand-768p.md)仅重做00:00–00:04首镜，纠正左臂、腕部与左手的对应关系，保留手背朝镜头的自然反手捏帘姿势。两张翻掌候选被用户拒收，不进入影片。其他47镜源片、全部48镜时长／起点、音乐、标题和原生14秒蝶翼保持v9；成片1344×768、30fps、205秒／6150帧。[v10 Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v10-768p-20261118)、[交付计划](series/vivhite/autumn-journey/episodes/01-autumn-journey/delivery-plan-v10-768p.json)及[全部首帧候选和检查图片](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/image-inventory-v10-768p.json)继续保留。

已按用户要求启动[v11原生4K制作](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v11-native-4k.md)：以全部48段v10采用源片为输入，经局域网模型再生成3840×2160，单任务顺序执行。时长仍为205秒／6150帧，首镜反手、帐门、玩偶动作和原生蝶翼速度保持当前版本；768P成片与历史Release保留。尚未完成4K验收，[进度记录](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/run-progress-v11-4k.json)区分生成和内容审核。

4K任务现由[Windows独立执行器](docs/autumn-journey-background-rendering.md)持续推进，已实测原对话客户端突然退出后的自动续接；对话关闭不会停止源片生成、下载与机器检查。当前009配置只收齐原48镜源片并保存检查点，不自动合成含旧S05的预览；新S05有独立守护。完整4K另由逐镜核对实际采用素材的导入器和正式审核流程装配，历史影片与Release保留。

历史[v9闭帐门与手部修订](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v9-motion-768p.md)及[v9 Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v9-768p-20261118)保留。该版S44从全闭帐门开始拉开拉链与门帘，S47用自然连接的双臂摆正玩偶；这两镜在v10原样复用。旧版影片与全部中间产物保留。

历史[v8七处动作返工](series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v8-motion-768p.md)及[v8 Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v8-768p-20261118)保持原样。其S44/S47随后被用户拒收，由v9替换；两份未采用的蝶翼减速候选继续留档。

三期当前成片均已完成，规格1080p30、晓晓配音、中文字幕及可替换人物图片：第一期[10分55秒](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/production-v3.md)、第二期[18分29.3秒](series/math-education/inversion-count/episodes/02-rectangle-proof/docs/production-v1.md)、第三期[32分24秒](series/math-education/inversion-count/episodes/03-wilson-theorem/docs/production-v1.md)。制作器新增通用证明动画后端，后两期保留全部证明、合法移动和分阶段推导。成片与缓存放在仓库外，检查范围见各期制作记录及[独立复核](docs/three-episode-production-review.md)。

后续视频任务必须执行[角色参与及文案审核规约](docs/character-workflow.md)：创作前读取独立私有角色仓库中的唯一完整人格文档，成稿后分别审核人格一致性与信息披露。公开项目只保存角色 ID、必要版本引用及审核状态，不保存人格副本。

用户说“做视频”时的[默认制作约定](docs/video-production-defaults.md)已固定：先补齐制作器再交付完整影片，参考 XAR 工具链，默认 Edge 晓晓和可替换的人物图片占位，多期并行且冲突时第一期优先。

## 已完成的实战案例

- [《明日方舟》EP《酸橙色信笺》导演案](docs/analysis/BV1nB3u6tEHD/director.md)：使用 analyzer 分析全片，按44个镜群还原旅行影像、群体签收与角色回信结构；附证据引用、审查范围及复现脚本。
- 内容来源：`BV1AV411V7SJ`，分析滑块拼图的搜索、复原方法与奇偶不变量。
- 风格来源：`BV1i4aS6SEBR`，提炼先操作后解释、持续图形对象、纸色细线与章节/结论条。
- [案例分析与覆盖说明](series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/README.md)。
- [v1 导演草稿](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director.md)：20 镜、计划 12 分 20 秒；风格复核后需要重写。
- [目标片风格复分析与改稿依据](series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-reanalysis-v2.md)：逐段对照、文本密度统计、工具构造主线及 90 秒方向样稿。
- [后续视频制作任务交接](docs/video-production-handoff.md)：下一会话的必读材料、本地产物、实现任务与验收标准。
- [实际视频制作流程](video-maker/docs/production.md) 与 [v2 制作计划](series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/production-plan-v2.json)：39 段新版文案，先展示判别器再逐步构造，消费真实数学状态生成动画。
- [第一期 v3 台词修订稿](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director-v3.md)与[39 段审查及改前改后对照](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)：从真实成片台词修掉模板化表达，重写人物反应与逐步动作；已重新制作为10分55秒的1080p30影片，详见[制作记录](series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/production-v3.md)。

本例完整处理了两部音轨并阅读全部转写，连续解码 58,808 帧；语义画面输入是贯穿全片的 415 张选帧。逐窗摘要由本次助手编写，逐句条目保留 ASR 与关键修订，不是逐句听音校准。本机没有配置 OpenAI API 凭据，实际交付使用 `assisted` 导入路径；独立 API 路径已实现，尚未联网验证。

## 制作完整视频

在已有案例分析产物的本机，安装独立配音环境后执行：

```powershell
uv venv --python 3.12 video-maker/.venv
uv pip install --python video-maker/.venv/Scripts/python.exe -r video-maker/tools/requirements-lock.txt
.\scripts\produce-puzzle-video.ps1 -Build -VideoCodec h264_nvenc

# 第二、三期有独立入口，复用同一制作器
& 'series/math-education/inversion-count/episodes/02-rectangle-proof/authoring/produce.ps1'
& 'series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/produce.ps1'
```

默认采用最新 v3 台词；`-Revision 2` 选择历史 v2。无 NVIDIA 编码器时省略 `-VideoCodec`，使用 CPU `libx264`。默认 Edge TTS 晓晓 `zh-CN-XiaoxiaoNeural`，音色、语速、输出目录和人物可由参数改变。首次联网合成旁白，之后按内容哈希复用配音。新 v3 成片实测10分55秒，位于仓库外 `../vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3/`；历史v2仍保存在 `../vivhite-analysis-output/puzzle-restyle/production-v2-cued/`。详见 [制作器说明](video-maker/docs/production.md)。

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
