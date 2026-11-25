# 参考图视频制作入口

`produce-reference` 为旅行等影像提供独立的参考图视频制作路径：Java 校验计划和实际参考图，运行人格／披露绑定检查，再调用 FastH3 Omni Ref2VA，保存异步任务、下载源视频、按导演时长裁剪并统一为 1080p30。数学动画与 TTS 路径继续使用原命令。

下方 Java 用法用于复现历史 `fasth3-omni` 提供方。新本地生成任务使用后文的 BF16 工作流，通过 8080 统一网关提交。

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
$apiBase = 'http://<旧式提供方>/v1'
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

标题计划可通过 `closingCredit` 指定片尾署名；显式设为 `""` 时不生成署名事件。省略该字段仍沿用历史署名。`titleOverlays` 的 `text` 与 `subtitle` 分别控制第一行和第二行，也可用于标题与献词；所有实际文字均须参与最终计划和素材的独立审核。

`source-selections.json` 可以选择修订源片，必须同时绑定其原文件与修订收据，旧版保留。`stabilize_printed_patch.py` 默认将首帧已有的周边印花跟踪回物体表面；首帧本身错误时，可用 `--texture-reference <原图> --reference-box 左 上 右 下 --target-box 左 上 右 下` 将同一原始印花配准到视频中原有的对应物件，首帧也做相同处理。收据绑定原图指纹及配准位置；此功能是既有原画的视频合成，不生成或重绘图像。矩形越界、未覆盖整个修订区域或跟踪不明确即失败；`--used-seconds` 限定实际使用区间。它不用于盖住人物或消除新增路人。修订完成后仍须逐帧重审印花、物件运动、接触与合成边缘，不能沿用原视频的通过记录。

`inspect_printed_region.py` 用相同表面跟踪提取原视频印花细节，默认覆盖全部120帧；S20使用 `--frames 240` 覆盖完整10秒，分页保存两组各120帧的局部图，收据逐帧记录全部240项。它仅保存原始像素的检查图，不输出修订影片。两个工具的缩放上限默认均为2.5倍；实际镜头推近超过该范围时，可通过 `--max-scale` 显式指定已观察到的有限上限，数值写入收据，跟踪成功仍不代表内容通过。推近后出现模糊贴片、光晕或边界接缝的修订片须另行拒收；可采用另存的节奏调整候选或重新生成，保留每次失败输出及其实际结论。

## BF16 768P 与逐镜原生4K接入

`tools/local_video_pipeline.py` 默认连接 `http://192.168.1.11:8080/v1`，用 `/v1/models` 核实注册的参考图生成能力；网关目录只公布能力，旧直连目录才公布解码器层数。BF16模型名为 `fasth3-omni-bf16`，默认每次请求5秒、1344×768、8步。S20的10秒和S48的10／14／15秒均须显式声明时长例外，其他镜头仍为2–5秒；S48允许15秒源片裁为14秒成片片尾。场景图提供构图与外观参考，可另传设计母版；运动参考可选。发现旧视频的眼形或印花错误时，使用仅含场景和母版的图像参考计划重新生成，不能让错误视频继续指导外观。当前 OpenAPI 的 `task` 固定为 `ref2va`，首帧构图由参考图和提示词引导。提交的只有实际制作素材及提示词。新生成式旅行视频采用[768P／4K规约](../../docs/local-video-768p-4k.md)。

```powershell
$episodeRoot = 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
$episode = "$episodeRoot/episode.json"
$plan = "$episodeRoot/production-plan-v5-bf16-768p-r2.json"
$run = '<本轮独立运行目录>'
$faceModel = '<YuNet 2023mar 权重>'
# 正式生成前，实际审阅最终计划、每张场景图和每段运动参考，并导出全部素材的匹配收据。
video-maker/.venv/Scripts/python.exe video-maker/tools/local_video_pipeline.py --episode $episode --plan $plan --directory $run --evidence "$episodeRoot/assets/generated/production-v5-bf16-001/review/video-768p" --face-model $faceModel --window 3
```

worker只依赖Python标准库进行HTTP上传、提交、轮询与下载；检查图像沿用可选OpenCV／NumPy／Pillow环境。它记录完整请求、实际上传文件指纹、上传回执、每次轮询、原始输出、服务器日志和下载校验。提交超时记为不确定，恢复时拒绝盲目重复提交；429才作为明确未受理而可重试。退出客户端不取消服务器任务，重跑读取已保存的任务ID；计划变更要求新运行目录。`--skip S43` 等参数只排除本客户端后续提交和轮询的镜头，不取消服务器任务；用于旧批次排除需要独立重做的场景，旧请求与计划指纹继续保留。生产运行须保存实际采用的worker副本及指纹，后续源码更新不改变运行中的引擎。

原始输出的帧对齐尾部保留在 `sources-raw/`；另存精确120帧／24fps、无音轨的5秒源片到 `sources/`，S20例外为240帧／10秒，S48按实际计划为336帧／14秒或360帧／15秒。完整源片都进入逐帧检查，因为后续4K输入包括最终剪辑未使用的部分。`record_local_clip_review.py` 只记录审阅者明确提供的实际结论；检测候选不自动放行。新版计划要求 `referenceAppearanceRequired: true`，实际对照原始设计后记录 `--reference-fidelity-reviewed`，检查睁眼轮廓、虹膜、圆形金框眼镜和脸部比例；表情稳定不能代替原画一致性。角色／披露审核与正式合成检查仍分别执行。

当前计划的全部镜头审阅后，`local_video_finisher.py` 按原生目标尺寸与每镜实际时长准备画面，拒绝错误分辨率或指纹不符的缓存。v5为49镜，用户恢复S20长镜后的v6为48镜、196秒；归档批次百分比不能当作当前v8进度。随后审阅实际最终计划、声音、标题和所有输入，再调用 `reference_finisher.py finish`。本地新计划使用1344×768或3840×2160；1920×1080保留给已有数学及历史工作流，2560×1440不再作为新输出。`inspect_local_video_film.py` 对最终全片逐帧解码、对照所选画面并输出面孔候选，仍需独立解释证据。

从多个已审核运行目录沿用相同源片时，本期 `production/materialize-sources-v6.py` 会保存原生成计划、任务、修订收据和实际视觉结论，并核对源片与全部证据字节。它不会把源片沿用写成重新观看或新模型生成。`source-imports.json` 如存在，会纳入最终计划的素材指纹绑定。S20唯一10秒例外也传入最终计划，成片检查允许这300帧，同时仍拒绝其他超时镜头。

768P成片实际交付并通过绑定检查后，`prepare_local_refinement.py` 从全部已审阅源片准备4K输入和新计划；S20保留完整10秒，S48保留实际14或15秒，其余为完整5秒，新计划须再次独立审核。之后调用统一网关的 `POST /v1/videos/regenerations`，使用模型ID `open-h3-2k`，显式指定 `3840x2160`、`sampler=up3`。4K以原生对齐画面计算后裁为UHD，每次由共享GPU执行一个4K窗口。每段结果重新检查、选择、合成和交付。接口、长镜头实测和恢复边界见[当前规约](../../docs/local-video-768p-4k.md)。

历史初始预计节点 `production/schedule-768p-2k-v1.json` 仅作归档，不作为4K速度或后续执行依据。进度分别记录实际生成、语义接受和最终交付，不能将HTTP成功或仅源片到齐写成成片验收通过。

## v7片尾10秒与延迟献词

当前worker允许在 `shotDurationExceptions` 中分别显式声明 `S20: 10`、`S48: 10`；声明的镜头必须实际存在且恰为10秒，其他镜头仍限2–5秒。历史计划的默认行为不变。v7为48镜、201秒，两个例外均为连续单镜头。

`titleOverlays` 的片尾项可增加 `dedication`、`dedicationDelaySeconds` 和 `dedicationFadeInMs`。前两行仍使用与片头相同的Title／Subtitle样式；献词另用Dedication样式，在镜头内延迟淡入，并保留完整阅读时间。没有献词的旧计划不新增该样式。实际v7使用3秒延迟、1800毫秒淡入；最终检查工具导出献词出现前、淡入中和完全显示的编码帧。

`retime_local_clip.py --output-seconds 10` 可将已通过的连续素材另存为240帧／24fps的10秒候选，原默认仍为5秒。处理收据明确记录末端短暂边缘填充，不自动赋予外观或内容通过。v7素材导入由本期 `production/materialize-sources-v7.py` 调用共用校验器，保留原真实生成任务、原计划和完整修订链；不把被拒收的新生成任务写成沿用素材的来源。

本项目全部2K任务已按用户最新要求停止，取消收据保存在本期 `production/stopped-2k-20261117.json`；归档目录中的2K命令和估算为历史接入记录，不代表继续执行授权。已交付v7为768P，旧版Release及所有中间文件保留。

## 当前片尾条件与固定时长

v8前47镜按v7锁定，共191秒，成片固定205秒／6150帧，仅S48为14秒。第二轮14秒原生片尾已因新增树枝和拍翼过快拒收，第三轮改为15秒源片但因服务端显存不足失败。用户随后明确取代15秒规则，第四轮起改回14秒源片，完整审阅336帧；片尾入片14秒，其他镜头长度不动。已有请求和计划不原地修改，独立重试另存真实来源。条件与分辨率选择由本期 `production/workflow-policy.json` 记录；旧2K字段保留实际历史，不是当前调用配置。
