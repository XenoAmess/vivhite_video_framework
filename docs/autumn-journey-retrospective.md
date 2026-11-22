# 《白绮／秋日旅程》结项复盘

结项日期：2026-11-22。用户明确表示“我很满意”，要求总结经验教训并入库，本期据此结项。对应[结项记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/project-closeout-20261122.json)与[本期入口](../series/vivhite/autumn-journey/episodes/01-autumn-journey/README.md)。本复盘总结公开制作过程和可复用方法，不新增剧情或角色背景。

## 最终交付与验收口径

| 交付 | 最终版本 | 规格与位置 |
| --- | --- | --- |
| 原始768P完整影片 | v12，骑行车座修订 | 1344×768、30fps、205秒／6150帧；[Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v12-768p-20261119) |
| 原生4K完整影片 | v13 | 3840×2160、30fps、205秒／6150帧、48镜；[Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v13-4k-20261121) |
| bilibili 16:9封面 | 20261121-v1 | 1664×936；[JPEG](../series/vivhite/autumn-journey/episodes/01-autumn-journey/assets/generated/bilibili-covers-20261121-v1/cover-16x9.jpg)，另留PNG和生成原图 |
| bilibili 4:3封面 | 20261121-v1 | 1448×1086；[JPEG](../series/vivhite/autumn-journey/episodes/01-autumn-journey/assets/generated/bilibili-covers-20261121-v1/cover-4x3.jpg)，独立构图，另留PNG和生成原图 |

4K影片本机文件：`D:/workspace/vivhite-analysis-output/vivhite/autumn-journey/production-v13-native-4k-full-001/film.mp4`，SHA-256为 `4a2f833105a027becbc4a1f2553de801d4a7ec994d1e837c6eaadddcf77a8819`。大型音视频在仓库外及Release保存，源码、计划、图片、非敏感收据和复盘在Git保存。

最终制作记录覆盖48段完整源片、6150个成片解码帧、193页全帧有序图册、18张原尺寸重点画面、13张字幕检查代理及其他局部证据。35段、38处印花做了场景光照匹配。4K Release六个附件已在发布时实际完整回下载并核对SHA-256。详细范围、已知动作差异和合成边缘限制见[制作记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v13-native-4k.md)与[发布凭据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/release-v13-native-4k.json)。

本轮新增的是用户在项目层面的满意与结项确认。它不追溯改变过去的检查范围，不将助手有序帧图审阅写成人工连续播放，也不将音轨数值对照写成人工听完整曲。旧报告中的“待用户审美验收”是发布时的历史状态；当前项目状态以结项记录为准。既有Release标签、附件和所有历史版本保持原样。

## 做对了什么

**把艺术参考转成叙事方法。** 本片的连贯性来自短片段的旅行蒙太奇、景别和地点变化、手与道具的具体活动、音乐和环境声的连接，以及白绮周边的反复出现。参考的是这些组织方法，不是逐镜复制参考视频的构图。真实世界里有使用痕迹的包、阴晴变化、普通植被与日常设施，比一味追求无瑕奇景更贴合本片。

**让角色通过周边进入世界。** 贴纸、徽章、立牌、布袋与玩偶既连接不同地点，也使真人可以只出现手、衣袖、腿脚等局部。周边先做母版，再用于场景图和视频，便于检查角色身份。它们是图像中的拟制设计，不代表已经生产实物；没有把静态形象宣称为Live2D或表情驱动。

**配乐有统一主题，也可以精确复现。** 本片采用程序作曲与波形合成，保留柔和琶音、钟铃主题、和弦铺底和按镜头排程的环境声；未调用Suno，也未采用视频模型原声。实际配方为96 BPM、4/4、D大调、种子20261116。用户认可的是本片听感，不能据此推断程序合成在所有场景都优于音乐模型。后续应优先保留已获认可的主题与母带，分辨率升级不必重做音乐。完整配方见[音乐生成说明](autumn-journey-music-generation.md)。

**原片、候选和采用决定分开保存。** 每次返工另开运行目录，保存完整请求、输入与输出指纹、实际运行代码、失败记录和选择依据；采用清单只指向实际检查过的版本。拒收旧S05后，后续装配明确阻止旧无车座版本回填。这样才能在多天运行、单镜返工和跨机器接续时知道最终到底用了什么。

**生成与审核交错推进。** GPU继续普通排队时，本地同时下载已完成片段、准备证据、审阅和做可复用编码缓存；不必等48段全部结束才开始后处理。缓存按源片SHA-256、镜长、尺寸、编码配方和结果指纹匹配，素材一变就重新核对，避免把局部返工变成全片盲目重做。

## 返工暴露的教训

| 问题与实例 | 这次暴露的遗漏 | 后续执行规则 |
| --- | --- | --- |
| 场景美得不真实 | 审核偏向单张画面的漂亮程度，忽略影片要呈现普通世界 | 首帧就检查天气、地理、材质、生活痕迹和可信光照；先让美术方向成立再批量生成 |
| 视频出现新增人员或真人脸 | 把首帧没有人物、提示词要求不露脸当作充分条件 | 约束覆盖全部生成帧，包括远景、身体局部、反射和影子；原图没有的无关人员即使不露脸也拒收 |
| 误称角色从闭眼变睁眼 | 未准确区分原图眼形与生成后的形变 | 用户给定这一批原图的眼睛均睁开；逐张对照原图和对应母版，记录虹膜、镜框、嘴形与比例的具体变化，不凭印象解释 |
| 秋叶散步僵住、咖啡杯被反复抚摸、帐门拉上又拉下、玩偶只被碰一下 | 把“有运动”当作“完成了有意义的动作” | 每镜定义起态、过程和终态；要求连续步行、提起杯子、从闭帐到打开景色、把玩偶调整到更好角度，审阅是否真的发生 |
| 首镜左右手错误、玩偶镜头第三只手或腕部变形 | 只数肢体数量，未追踪左右关系和关节连接 | 连续核对手臂—手腕—掌背／掌心—拇指—道具接触；有结构错误就重生成，不用印花贴片掩盖 |
| 骑行缺车座、背景跳变 | 检查了印花与人员，却漏掉机械和承重关系 | 同时审车座、座轨、夹具、座管、臀部支撑及双腿／踏板／曲柄；完整时序检查背景连续，不能由漂亮首帧放行 |
| 印花修复后亮脸、圆盘边缘、双镜框或残留嘴线 | 纹样更清楚被误当成整体融合更好 | 分开审身份、配准、遮罩、清晰度、场景照明与遮挡；先看原片／旧修复／多档候选，再从未修改原片重做 |
| 印花从画外进入后出现横缝 | 在首帧画布上裁掉了后续需要的纹理和遮罩 | 保留母版完整局部，每帧组合配准与跟踪变换后再投影和裁切；边缘进出、透视与遮挡都要实际看 |
| 反复生成前景树枝或不自然蝶翼 | 把语义提示当成强制约束；速度问题与结构问题混在一起 | 清楚描述正向构图与动作，按真实输出拒收；慢放只能改善正确动作的速度，不能修复错误翼形。用户取消减速后保留已选原速度 |
| 为凑205秒拟缩短S46 | 没有把用户限定的改动范围作为硬约束 | 前47镜固定191秒，S46保持5秒，仅片尾14秒，合计205秒／6150帧；不能擅改其他镜长，不能循环或冻结补时 |
| 后端版本与能力被混称 | 把模型ID、部署解码器、HTTP参数、计算窗口混为一谈 | 保存实际能力声明与任务收据；核实36L部署和实际尺寸，不虚构接口参数，不将未开放的完整MiniMax教师模型写成已使用 |
| 4K完成很慢，守护异常造成空转 | 把持续询问、进程存在或守护配置当作正常推进 | 核对任务、下载、心跳和异常；恢复同一任务并修复守护。批量排队维持GPU供给，助手连接期间继续审片，守护仅兜底 |
| 中文记录出现替换问号、图片比例与提示词不一致 | 只检查命令成功，未核对写入后的实际内容 | UTF-8写入后回读，文字和图片都检查；按实测像素验证比例。封面记录的编码问题修正后重新绑定审核；生成原图与实际提示词保留 |

这些问题不能归结为“再加几个禁止词”。本期实读的FastH3接口固定 `task=ref2va`、8步、`guidance_scale=1.0`、空 `negative_prompt`，没有独立像素级首帧锁定参数。正文里的禁止语句不能变成接口并未提供的控制能力，提示词也不能替代结果检查。此处是本期部署实测，其他服务版本须重新核对。

## 后处理的边界

先把问题分成两类：动作、人员、人体或机械结构错误，优先修首帧与动作描述后重新生成；动作已经成立、只是既有印花细节漂移，才考虑局部恢复。两类修复不能互相冒充。

印花恢复按问题选择首帧固定、场景原图回贴、母版眼睛／镜框局部投射、多区域跟踪，必要时增加下巴锚点做三点仿射。任何配准都要防镜像、退化与过度伸缩；母版坐标、原生视频坐标和跟踪代理坐标必须分开记录。只对齐两眼不保证嘴、下巴和旧镜框一起正确。

光照单独处理：使用非眼部肤色样本校准RGB增益，按场景保留阴影、暖灯或蓝调变化，必要时用受约束的时间曲线和适当柔化。不能把同一个曝光或清晰度套给白天、车厢和夜景。候选发现错误时从原片重新合成，减少叠加编码与已处理像素的污染。

处理后同时查看完整场景、全部实际修订局部、原生重点与检测候选，并比较区域外的全部帧。PSNR或相关系数可以帮助定位编码差异，不能证明手部、人物数量、接触关系和审美成立。具体方法与失败例见[后处理方法论](autumn-journey-video-postprocessing.md)和[印花光照复盘](autumn-journey-print-lighting.md)。

## 排队、续跑与时间估算

客户端预排队和GPU并行是两件事。本期按用户要求尽量预排所有剩余任务；当时同模型最多32个未完成任务，客户端使用 `--window 32 --poll-seconds 60`，超出部分随空位补入，GPU仍单任务执行。正常有足够剩余任务时至少保留3个等待；按普通顺序，不插队。429是已知限流，等待空位；POST超时受理不明时先核对既有任务，禁止盲目重提。

对话断开后由Windows独立任务、隐藏窗口进程、持久任务ID和冻结代码继续生成、下载、完整解码及检查点归档。实际故障试验显示，仅配置“失败后重启”不足以保证恢复；每分钟看护触发器才完成控制器退出后的续接。Windows JSON替换曾因共享句柄失败并导致空转，修复为独立临时文件与有界退避重试，同时保留持续失败现场。记录见[独立执行与故障修复](autumn-journey-background-rendering.md)。

已完成片段必须按完成顺序处理。旧材料准备器按镜号等待，曾让先完成的片尾被前面的未完成镜头挡住；后来改为每轮检查全部本地待办，哪段输入和检查报告先齐就先导出证据。准备证据、机器检查与实际内容采用仍是三个状态。

估算应拆成排队、短片生成、长片生成、下载检查、局部修订、最终编码、全片检查与上传验证。本期17个5秒4K源片的历史运行至下载中位约76.16分钟；14秒整段S48实际观察约8小时9分。这是特定部署和负载的历史数据，不是未来服务保证，也不能用短片秒数线性外推长序列。

长镜头后端后来从重叠独立窗口改成 `full_sequence`，必须在实际任务收据核对 `windows=1`、`independent_window_fallback=false`，再审完整序列。旧10秒多窗记录、旧恢复方式和旧预算不能套到新后端；本片14秒成功也不证明15秒已经可用。原始768P和原生4K路线、36层解码器与端口／历史模型ID的对应关系见[调用规约](local-video-768p-4k.md)。

对用户汇报“生成、源片审核、成片检查、发布验证”各自的百分比，以及还剩什么、预算依赖什么；不把排队、导出图片或模型块级进度算成内容已通过。发现新返工或部署变化及时更新节点，保留旧估算作为历史。

## 下一次的执行顺序

1. **先冻结制作约束。** 写明静默、角色与人员边界、真实世界要求、镜长例外、文字、总帧数和本轮允许修改的镜头；后续明确改动另存版本，不混用旧指令。
2. **先核实素材与角色。** 完整查看原图与母版，创作前遵守[人格与文案流程](character-workflow.md)；完整档案和详细审核依据留私有库，公开库只留规定的版本绑定与结论。
3. **先试最难镜头。** 挑左右手／拉链、骑行机械、多个周边、阴影转暖光及最长镜头做样片，量出失败模式、真实生成速度和后处理成本，再扩大批次。
4. **先修原始768P，再升级对应4K。** 全部源帧检查后明确采用；升级上传本地实际采用文件，不能引用遗漏后处理的旧服务端任务。4K是新生成结果，要独立检查，不能继承768P的画面通过结论。
5. **长任务从第一天可续跑。** 独立运行目录、冻结worker、持久收据、队列补位、原子状态写入、完整下载检查和异常报警同时到位；助手在线期间持续处理已完成片段。
6. **边审核边准备可复用材料。** 从实际采用源片做分段缓存，局部返工只失效相关缓存；新源片未通过时阻止回填旧版本，不能为了先拼全而放行。
7. **装配后重新审输出。** 以帧数固定时间轴，标题由后期统一生成；核对全片音视频、全部字幕、动作与局部细节，分别写明自动检查、助手语义审阅和人工复核范围。
8. **下载验证后交付，反馈后结项。** Release上传成功后实际完整回下载并验哈希；保留原片、失败版与检查资料；用户接受后在新的结项记录更新状态，旧证据与已发布附件保持原样。

## 可复用实现入口

这些工具是Java制作框架配套的Python worker和Windows执行入口。通用工具参数可复用；本期专用脚本中的镜号、坐标、母版和指纹不能直接套到新片。

| 用途 | 代码或记录 |
| --- | --- |
| 生成、批量预排队、下载与状态保留 | [local_video_pipeline.py](../video-maker/tools/local_video_pipeline.py) |
| 对话外独立运行与单实例恢复 | [durable_video_controller.py](../video-maker/tools/durable_video_controller.py)、[Windows任务入口](../scripts/start-durable-video-task.ps1) |
| 按完成顺序准备检查材料 | [prepare-ready-native-evidence-v12.py](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-ready-native-evidence-v12.py) |
| 完整源帧与检测候选、显式采用／拒收 | [review_reference_clips.py](../video-maker/tools/review_reference_clips.py)、[record_local_clip_review.py](../video-maker/tools/record_local_clip_review.py) |
| 首帧／场景纹理固定、母版局部投射 | [stabilize_printed_patch.py](../video-maker/tools/stabilize_printed_patch.py)、[restore_printed_eyes.py](../video-maker/tools/restore_printed_eyes.py)、[restore_printed_regions.py](../video-maker/tools/restore_printed_regions.py) |
| 印花测光、光照曲线及柔化 | [print_lighting_calibration.py](../video-maker/tools/print_lighting_calibration.py)、[restore_printed_regions_lighting.py](../video-maker/tools/restore_printed_regions_lighting.py)、[restore_printed_badge_lighting.py](../video-maker/tools/restore_printed_badge_lighting.py) |
| 48镜来源绑定及禁止旧素材回填 | [materialize-native4k-sources-v13.py](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-native4k-sources-v13.py) |
| 精确镜长装配、统一文字与程序配乐 | [local_video_finisher.py](../video-maker/tools/local_video_finisher.py)、[reference_finisher.py](../video-maker/tools/reference_finisher.py) |
| 全片解码、画面轨与完整音轨数值核对 | [inspect_local_video_film.py](../video-maker/tools/inspect_local_video_film.py)、[inspect-audio-v9.py](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/inspect-audio-v9.py) |
| 版本绑定后的Release发布与回下载验证 | [publish-native4k-v13.py](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/publish-native4k-v13.py) |
| 两种封面、实际提示词与导出尺寸 | [封面制作记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/assets/generated/bilibili-covers-20261121-v1/README.md) |

## 归档与跨机器接续

Git不是大型媒体的完整备份。新机器需分别取得本仓库、获授权的私有角色库、用户原始ZIP及仓库外运行目录／Release影片和所需WAV；按记录核对哈希，再准备Python、FFmpeg和局域网服务。只拉公开Git不能声称已经具备所有输入、检查结果和断点恢复文件。

归档保留原始768P、原生4K、旧2K历史记录、全部已交付旧版、失败请求、候选、图片和审核范围。本项目结项不新增渲染、不中途改写旧请求、不自动恢复2K；未来新改动另开明确任务和运行版本。本轮文档归档也没有清理旧素材或重新发布既有影片。

最终仍有已如实记录的动作简化和局部合成柔化，见v13制作记录。用户满意使本期完成交付，不能把这些已知边界从历史中抹掉；下一片应把高风险动作和光照融合的样片检查提前，以减少后期连续返工。
