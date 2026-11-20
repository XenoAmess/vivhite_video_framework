# 本地视频制作：原始768P与原生4K

用户于2026-11-17明确：后续本地生成式视频只制作原始1344×768和UHD 3840×2160，不再新建2K任务。旧计划、失败输出、停止收据和已交付历史版本保留；其中的2K参数属于归档事实，不作为当前默认调用。

## 当前调用知识

| 环节 | HTTP API | 实际模型ID | 必须使用的尺寸与参数 |
| --- | --- | --- | --- |
| 原始768P参考图生成 | `http://192.168.1.11:8001/v1/videos` | `fasth3-omni-bf16` | `1344x768`、`task=ref2va`、8步；运行时核实36层解码器 |
| 原生4K视频再生成 | `http://192.168.1.11:8002/v1/videos/regenerations` | **`open-h3-2k`** | **`3840x2160`**、`sampler=up3`、当前种子1234；GPU单窗口；本期客户端 `--window 32 --poll-seconds 60` 预排队 |

4K服务沿用旧模型ID和端口，不要擅自改成不存在的 `open-h3-4k`，也不要省略尺寸让服务落回旧默认。2026-11-17本项目实际读取8002的 `/v1/models`，已看到 `3840x2160` 与单窗口能力声明；只读查询不是本项目4K成片验收。

**2026-11-21更新：长镜头已改用整段生成。** 本次实际查询8002返回 `long_4k_strategy=full_sequence`、`long_4k_independent_window_fallback=false`。当前声明以规范化后超过124帧为长序列阈值，时间轴24fps，即超过约5.167秒；不能再把10秒、14秒源片按旧方案估成三个、四个拼接窗口。沿用原再生成HTTP请求，后端部署决定时间策略，没有新增已验证的客户端切窗参数。这里只使用原生3840×2160，不恢复旧2K路线。

本片14秒S48已真实完成：服务端任务 `video_gen_505d3a78c78a42d7b933b6519e1007e9` 返回 `temporal_strategy=full_sequence`、`global_attention=true`、`windows=1`、`hard_cuts=0`、`independent_window_fallback=false`，36层FP32解码器；输出3840×2160、24fps、336帧。计算尺寸仍为3840×2176。首次观察运行至本地下载完成约8小时9分，不能按短镜头耗时简单线性推算长镜头。

实际审阅覆盖336帧整景、336帧原生蝴蝶局部及原生首尾整景，未观察到切换、场景重置、无关人员或新增前景树木，可作为片尾源片；蝴蝶保留原版较快节奏，没有另做减速。远景纹理和快速翼缘仍有模型处理痕迹。这是助手有序图像审阅，不等同于人工连续播放、听音或完整影片验收，见[具体源片与覆盖绑定](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S48-full-sequence-source-review-v11-4k.json)。其他长序列仍需逐个核实结果、完整解码与内容审阅；该实测不证明15秒已可用。

调用依据为用户指定的[4K HTTP文档](https://github.com/XenoAmess/local-model-operations/blob/main/deployments/video-generation/docs/open-h3-4k-http.md)。原生路线使用已有IC再生成权重；模型计算3840×2176，再按上游逻辑上下各裁8行得到UHD，不把普通空间放大称作原生4K。服务端记录为BF16 DiT、原版36层FP32 tiled VAE；不是宣称接入了未开放的完整MiniMax教师模型。

## HTTP请求与文件保留

先向8002的 `POST /v1/files` 上传实际审阅过的768P源片，再提交：

```json
{
  "model": "open-h3-2k",
  "input_video": {"file_id": "file_实际上传ID"},
  "prompt": "保留输入视频原有场景、人物局部、动作与周边图案，生成原生4K细节。",
  "size": "3840x2160",
  "sampler": "up3",
  "seed": 1234
}
```

也可使用文档允许的 `input_video: {"job_id": "video_gen_实际任务ID"}`。本项目优先上传**实际采用且通过完整复核的本地源片**，因为纹理回贴、规范化等修订未必存在于原始服务器任务中；直接引用原任务会丢掉这些处理。上面提示词仅说明接口结构，正式任务仍使用逐镜最终计划和实际素材绑定。

提交返回202后，使用 `GET /v1/videos/{id}` 轮询，完成后从 `GET /v1/videos/{id}/content` 下载。完整请求、上传哈希、任务ID、轮询、原始音视频、规范化源片、日志和失败材料均保留。POST超时不能盲目重提；先核对受理状态，避免重复任务。

4K与768P共用GPU队列，按普通队列执行，GPU每次仅加载一个4K窗口，不能按两块GPU估算耗时。服务声明的`four_k_max_windows_per_load=1`是单次推理加载窗口数，不等于客户端只能排一个独立HTTP任务。

2026-11-18用户先要求至少3个任务排队、完成后及时处理，随后要求评估并尽量排入全部剩余任务。[服务端队列文档](https://github.com/XenoAmess/local-model-operations/blob/main/deployments/video-generation/docs/video-http-queue.md)规定同模型最多32个未完成任务，超限返回429。排队保存上传文件及SQLite任务记录，前端和调度器不加载模型；排队本身不增加同时执行的GPU任务，但仍消耗存储，不能称为零成本。当前以`--window 32 --poll-seconds 60`填充允许的32个未完成名额，超出的剩余镜头随完成自动补入。单次GPU窗口、模型、原顺序不变，不插队。

批量模式每轮只读一次`GET /v1/queue`，仍在等待列表中的任务不逐一查询；运行或已离队的任务获取完整收据，完成后立即下载、检查。明确收到429时保留该镜头为prepared，本轮停止后续新提交，继续处理已知任务，下轮再按原顺序尝试；受理不明的POST仍不得盲目重试。已提交计划及请求字节保持不变。首次窗口4的[历史记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/queue-policy-v11-4k-20261118.json)保留，窗口32的实际部署与队列证据另记[批量排队记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/queue-backlog-v11-4k-20261118.json)。服务端OOM后保留失败任务和现场，不提高内存限制或自行重试失败生成。

数日运行可使用本期已实测的[Windows独立执行器](autumn-journey-background-rendering.md)。它由按需任务承载，保留任务ID、冻结代码、下载与机器检查、图片Git检查点和技术合成，不依赖GPT对话存活；其自动恢复不等于自动通过内容审核。

## 已验证范围与恢复边界

服务端[4K验收记录](https://github.com/XenoAmess/local-model-operations/blob/main/deployments/video-generation/deployment/video-queue/4k-validation.json)报告：首条完整样片为3840×2160、124帧、24fps、约5.167秒，完成下载、哈希、音轨及全量解码；端到端约77分47秒。该记录只有首、中、尾选帧查看，不能称为完整时序或画质对比验收；它也不是本片48镜的实测速度或确定交付时间。

2026-11-18本片S01另已完成实际3840×2160、120帧／24fps／5秒生成、下载、哈希与完整解码，提交至下载规范化约77分45秒；后续S02自动进入队列。具体源片指纹、检查范围及未通过内容审核的边界见[v11记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v11-native-4k.md)。这不是长镜头或全片4K验收。

以下长镜头分窗说明记录2026-11-19旧部署。旧接口约4.7–15.1秒输入范围、重叠窗口和接缝记录保留用于复查历史输出；2026-11-20完成的S48已使用上文整段生成方案。15秒4K仍没有本项目实际出片验收，不由接口范围推断已经可用。

2026-11-19对本片S20十秒任务的[一次日志诊断](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/long-source-diagnostic-v11-S20-20261119.json)实际观察到`window-00`与`window-01`顺序计算，首窗已写出124帧原生4K，第二窗仍在采样。任务元数据中的`batch_windows=1`不能证明整个十秒源片只含一个时间窗。此时完整240帧尚未下载，不将首窗或运行中日志计为十秒出片验收；后续需看完整序列，并以原生画面重点审查时间窗接续处、玩偶与徽章。计算分窗也不改变最终连续十秒镜头或其他镜头时长。

上述为02:39 UTC的历史快照；03:20 UTC日志已出现第三窗，前两个窗口各124帧均写出，完整十秒任务仍未完成。后续[检查准备记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S20-native-window-review-plan-v11.json)固定了公开服务端规划源码版本：默认124帧窗口、至少24帧重叠，240帧输入推算需三窗，输出接续点为91／149帧；336帧片尾推算需四窗。这些是该源码的计算结果，尚未取得实际部署任务的window-plan文件，也不是十秒／十四秒成片验收。重叠窗口会重复计算上下文，长镜头不能仅按最终秒数与五秒实测做线性耗时保证；应结合实际完成窗口、完整出片及接缝复核记录更新预算。

旧部署保留4K潜变量检查点 `window-XX-4k.latent.pt` 和完成窗口 `window-XX-4k.mkv`；当时续跑复用的是已完成视频窗口。新整段方案的潜变量恢复与独立续解码尚未在本项目实测，不能沿用旧窗口恢复结论。模型版本、采样器、尺寸或输入变化时应另开运行目录。

## 本仓库制作入口

- [`prepare_local_refinement.py`](../video-maker/tools/prepare_local_refinement.py)：实际768P交付及其绑定通过后，准备独立4K计划和完整已审源片，不提交任务。新计划明确写入3840×2160和单任务窗口，重新进行人格／披露审核。
- [`local_video_pipeline.py`](../video-maker/tools/local_video_pipeline.py)：新再生成请求固定为UHD，拒绝新2K计划；核实实际服务尺寸声明。`--window`限制客户端未完成任务数，支持预排队，不改变服务端GPU加载窗口。完整下载和检查源片，不将HTTP成功自动写为内容通过。
- [`local_video_finisher.py`](../video-maker/tools/local_video_finisher.py)、[`reference_finisher.py`](../video-maker/tools/reference_finisher.py)：按实际计划装配原始768P或4K影片，绑定实际配乐和标题。既有数学视频1080P接口属于独立历史工作流，不据此新建本地2K生成。
- [`inspect_local_video_film.py`](../video-maker/tools/inspect_local_video_film.py)：完整解码和画面轨核对。检测器使用缩小图输入，细小人物、印花及接缝仍需原生4K局部检查，不能靠检测器或放大后的768P截图代替。

正式4K提交示例，需先准备独立计划并完成实际输入审核：

```powershell
video-maker/.venv/Scripts/python.exe video-maker/tools/local_video_pipeline.py `
  --episode <实际episode.json> --plan <已审4K计划.json> `
  --directory <独立4K运行目录> --api http://192.168.1.11:8002/v1 `
  --evidence <项目内检查图片目录> --face-model <实际YuNet权重> --window 32 --poll-seconds 60
```

## 《秋日旅程》片尾的条件规则

当期[工作流策略](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/workflow-policy.json)记录用户最新要求：**第三轮15秒请求显存不足失败后，用户明确改回14秒源片**，取代此前触发的15秒重试规则。第四轮起完整审阅336帧，片尾入片14秒。前47镜保持原来的191秒，全片205秒／6150帧，S46仍5秒；15秒失败请求与被取代规则保留归档。

当前源片与成片片尾均为14秒，不改变其他镜头长度，不靠循环或冻结补时。修改实际源片长度时另存计划和运行、更新哈希绑定并复审；已经提交的计划不原地改字节。14秒原生4K源片的实际审阅见上文；15秒和完整影片不在该结论范围。

最初更新只读取接口、未提交4K。2026-11-18用户另行明确要求开始4K后，[v11制作](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v11-native-4k.md)已以v10的48段完整采用源片启动；保留768P，不恢复2K。新4K提示词保持实际输入动作及原蝶翼速度，不拼接历史图生指令或重新要求慢扇。准备器也核对768P交付的实际五项素材绑定；只有新4K实际输入审核通过才提交，后续输出另审。
