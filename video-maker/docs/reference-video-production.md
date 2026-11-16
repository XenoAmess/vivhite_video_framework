# 参考图视频制作入口

`produce-reference` 为旅行等影像提供独立的参考图视频制作路径：Java 校验计划和实际参考图，运行人格／披露绑定检查，再调用 FastH3 Omni Ref2VA，保存异步任务、下载源视频、按导演时长裁剪并统一为 1080p30。数学动画与 TTS 路径继续使用原命令。

本 Java 入口输出 **无声画面装配中间文件** `picture-assembly.mp4`。它保留模型原始音视频作为源素材，画面装配阶段不接入未经审核的生成音轨。独立 `reference_finisher.py` 负责原创非语言音轨、镜内片名／署名和正式 MP4 合成；它另行检查实际最终计划和全部源文件的审核绑定。不得将无声中间文件标为正式成片。

## 计划与运行

计划版本为 `vivhite-reference-video-1`。它用于参考图生成与逐镜裁剪；已有数学计划依赖旁白与数学状态，无法表达这种无对白输入，因此使用独立内部制作计划，不修改 analyzer 报告契约。

计划声明 `width/height/fps`、`sourceSize`、`noSpeech/noHumanFaces`、`allCharactersFemale`、`costumeStyle`、`totalFrames` 和 `shots`。当前入口只接受静默、不露脸、全女性且声明服装风格的计划。每镜包含稳定 ID、连续的 `startFrame`、`seconds`、`sourceSeconds`、完整生成提示词、随机种子和 `references`。参考路径相对于计划目录，必须留在该目录内；文件与 symlink 的实际目标都要核对。

当前输出为 1920×1080、30fps，单镜 2–10 秒；源片使用 5／10 秒档。模型原生分辨率与 24fps、最终放大及帧率转换必须分别记录，不能把 1080p 导出称作原生 1080p 生成。局域网服务地址从命令行传入，不写入稿源和共享配置。

```powershell
.\mvnw.cmd -pl video-maker -am verify
$episode = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/episode.json'
$plan = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/production-plan-v4.json'
$output = '<仓库外的独立运行目录>'
$apiBase = 'http://<模型服务器>:8001/v1'
$python = 'video-maker/.venv/Scripts/python.exe'
$jar = 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'

# 所有场景参考图生成并审阅后，先导出本计划及实际参考素材的审核收据。
java -jar $jar validate-reference-production $plan

# 冻结实际采用的引擎；后续构建不改变该次运行使用的 JAR。
New-Item -ItemType Directory -Force -Path "$output/engine" | Out-Null
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $jar).Hash.ToLowerInvariant()
$frozenJar = "$output/engine/video-maker-$hash.jar"
if (-not (Test-Path -LiteralPath $frozenJar)) { Copy-Item -LiteralPath $jar -Destination $frozenJar }
java -jar $frozenJar produce-reference $episode $plan $output $apiBase $python
```

正式入口会收集每镜实际使用的全部参考图，作为重复的 `--asset` 自动运行 `scripts/character_review.py check`；审核缺失或版本不符时，在提交模型任务之前失败。需要由审阅者实际检查完整计划与素材并在私有角色库记录依据，然后导出公开收据，不能靠本程序自动作出语义结论。

## 提供方与失败恢复

FastH3 的请求使用 `task=ref2va`、有序的 `image_reference: [{image_url: ...}]`、8 步与 guidance 1.0，并通过 data URL 上传实际图片。普通 `input_reference` 是旧字段；多模态参考使用 typed reference 对象。契约依据为[上游请求类型](https://github.com/hao-ai-lab/FastVideo/blob/main/fastvideo/entrypoints/openai/protocol.py)和[OmniRef 推理规约](https://github.com/hao-ai-lab/FastVideo/blob/main/docs/inference/fasth3_omniref.md)，仍以所接服务的实际响应为准。

每镜的请求键包含提供方地址、完整提示词、种子、采样参数及图片内容。`requests/Sxx.json` 在仓库外保存完整实际请求（包括参考图 data URL）；`jobs/Sxx.json` 保留远端任务 ID、完整状态和输出哈希；`sources/` 保存原始音视频，`segments/` 保存精确裁剪的画面。源片完整解码后才发布，分段校验实际帧数后才写入装配清单。

- HTTP 请求、下载、轮询与 FFmpeg 都有时限。中断会保留任务 ID；恢复时继续查询已有任务，不自动创建重复任务。
- POST 超时可能已经创建远端任务，记录保留为不确定状态，须检查远端任务后处理，不盲目重试。
- 服务端任务失败时保留原因并停止后续生成；修复后重新运行会保留旧尝试，再提交该失败镜头。任务 ID 查询返回 404 时，依据本服务不持久化任务索引的约定，单次运行最多重新提交一次，并保留旧尝试。已下载且哈希正确的源片优先复用，不依赖远端索引继续存在。
- 源片缓存校验文件哈希，不能把截断或被替换的文件当成成功输出。服务使用的权重版本仍需另行记录，客户端请求哈希不能证明服务权重未变。
- 成功装配也只记为 `picture-assembly-completed-audio-and-semantic-review-pending`；后续必须检查所有实际画面、音轨与标题，并完整解码最终影片。

新增测试用本地 HTTP stub 验证 typed reference 实际传输和服务失败保留，并检查单镜时长、时间轴连续性与参考路径越界。它们验证客户端，不证明远端 GPU 已成功渲染。

## 原创音轨与最后合成

可选依赖见 `tools/requirements-reference.txt`（NumPy），不影响 Edge TTS 和 Java 数学渲染依赖。NumPy 使用 BSD-3-Clause，版本沿用本机已实跑环境；来源与授权见根目录第三方声明。

```powershell
uv pip install --python video-maker/.venv/Scripts/python.exe -r video-maker/tools/requirements-reference.txt
$sourcePlan = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/production-plan-v4.json'
$finalPlan = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/final-assembly-plan-v4.json'
video-maker/.venv/Scripts/python.exe video-maker/tools/reference_finisher.py soundtrack --plan $sourcePlan --output $output
# 等全部真实源片和 picture-assembly.mp4 到齐：
video-maker/.venv/Scripts/python.exe video-maker/tools/reference_finisher.py prepare --source-plan $sourcePlan --directory $output --destination $finalPlan
# 实际审阅音轨、全部镜头、标题、署名与组合，绑定 finalPlan 及其中 files 的全部实际文件，再导出收据。
video-maker/.venv/Scripts/python.exe video-maker/tools/reference_finisher.py finish --episode $episode --plan $finalPlan --directory $output
```

音轨按真实时间轴生成 48kHz 立体声 PCM：96 BPM、D 大调器乐和按镜头分配的合成环境声。没有采样音乐、录音人声或 TTS；不使用模型原生音轨。收据保存具体音符事件、环境声来源、随机种子、样本数、代码和波形哈希。环境声为程序合成，不能称作现场实录。

`prepare` 只准备待审核的最终实际计划。`finish` 在编码前核对所有文件哈希、限制文件留在运行目录、执行人格／披露绑定检查，然后添加标题和镜内淡出，完整解码并核对 1080p30、总帧数和音轨时长；成功状态只证明编码技术检查，不自动填写语义或人工验收结论。ASS 中的 `Dialogue` 是格式的事件字段，实际内容仅为片名、副题与制作署名；无对白字幕。

`review_reference_clips.py` 可逐帧连续解码并测量运动、突变和 YuNet 面孔候选，保存全部实际入片原生帧的检查拼图，另存每半秒、末帧和候选局部。模型来自 [OpenCV Zoo YuNet](https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet)，权重放仓库外并记录 SHA-256。面孔检测可能漏检，也会识别周边的绘制脸，不能自动宣布“无人脸”或语义通过。实际逐镜审阅需读取全部入片帧与候选；检查拼图按本任务要求保存在内容项目并提交 Git。

最终合成还要求 `clip-decisions.json`：每镜绑定实际选用视频的 SHA-256，审阅方式为 `assistant-frame-review`，明确记录全部入片帧的查看范围，以及静默画面、无真人脸、无新增人员、全女性、服装、动作连续性和周边行为的结论。`prepare` 和 `finish` 拒绝缺失、未通过或绑定旧文件的记录；脚本本身不代替审阅者作出结论。原图没有的路人、远景剪影、额外身体局部与倒影，即使不露脸，也不能放行。

`source-selections.json` 可以选择修订源片，必须同时绑定其原文件与修订收据，旧版保留。`stabilize_printed_patch.py` 只允许将首帧已有的周边印花跟踪回物体表面，遇到跟踪不明确即失败；`--used-seconds` 限定实际使用区间。它不用于盖住人物或消除新增路人。修订完成后仍须逐帧重审，不能沿用原视频的通过记录。
