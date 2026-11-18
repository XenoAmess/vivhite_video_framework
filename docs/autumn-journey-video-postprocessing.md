# 旅行视频后处理：印花稳定、原图回贴与复核

本文记录《白绮／秋日旅程》实际使用的后处理方法及代码入口，供其他镜头复用。核对日期为2026-11-18。技术范围是既有视频的局部纹理合成、慢放候选、标题和最终装配；不是重新训练模型，也不是保证所有镜头都能修好的一键修复。

## 先区分问题，再选择方法

| 实际问题 | 可选处理 | 需要重新生成的情况 |
| --- | --- | --- |
| 首帧图案正确，之后眼睛眨动或印花漂移 | 跟踪并固定首帧纹理 | 道具本体、手部或背景也有错误 |
| 视频首帧的眼形、眼镜已经变形 | 从对应场景参考图回贴原有纹理，再逐帧跟踪 | 参考图本身不符合设定；跟踪或合成效果不成立 |
| 动作成立，只是速度过快 | 另存慢放与插帧候选 | 动作本身错误、身体或翅膀结构不连续 |
| 多出人物、真人脸、第三只手，或背景跳变、步伐冻结、无效动作 | 修订提示词并重新生成 | 不能用小贴片或裁剪冒充已修正动作和人数 |
| 标题样式、顺序或淡入时间不对 | 后期统一生成字幕事件并重合成 | 不把文字交给视频模型临时绘制 |

“原画恢复”容易引起误解。本项目区分**首帧纹理固定**、**场景原图纹理回贴**与**对应周边母版的局部纹理恢复**。早期768P回贴使用此前imagegen生成、已保存入库的场景图；v11原生4K的S03、S06另采用M05徽章、M09贴纸母版。它们都不意味着直接从ZIP抠脸或与ZIP原图逐像素相同。角色设定仍是外观判断依据，实际取样图本身也要先检查。

## 实现与数据流

核心代码为 [`stabilize_printed_patch.py`](../video-maker/tools/stabilize_printed_patch.py)：

```text
原始生成视频（保留）
  → 标定脸部中心、半径；必要时映射场景原图纹理
  → 跟踪未修改视频上的稳定边界
  → 对固定纹理逐帧做平移、旋转和等比缩放
  → 羽化遮罩合成
  → 独立修订视频＋处理收据＋编码日志
  → 全部源帧与原图复核
  → 明确采用或拒收；之后才进入成片
```

### 方法一：固定视频首帧的印花

`PrintedPatch.__init__()` 保存视频首帧及局部圆形遮罩。后续帧把这份首帧纹理随道具运动贴回；首帧本身不修改。处理收据为 `vivhite-printed-patch-1`。

它能抑制小范围眼睛、嘴部与眼镜的随机变动，却会原样固定首帧已有的错误。不能把“眼睛不动了”当作“眼形与原图一致”。

### 方法二：回贴对应场景图的原有印花

`project_reference_texture()` 接收原图取样框 `reference_box` 和视频首帧落点框 `target_box`，映射图案到同一个原有道具。`stabilize()` 从首帧开始合成，再沿用相同跟踪。处理收据为 `vivhite-printed-patch-2`，额外记录原图哈希、两个框和首帧已修正标记。

坐标均为各自图像的原生像素：`left top right bottom`。当前命令只接收两个轴对齐矩形，不提供任意四边形标定。首帧映射虽调用 `getPerspectiveTransform()`，后续运动模型仍是局部相似变换，不是完整透视或三维表面恢复。

圆形修订区必须完整落在首帧落点框内；不要只对齐眼睛而忽略眼镜、脸颊、发缘和领口接缝。修改半径或映射位置后必须另存版本，检查是否出现双眼镜、光圈、颈部错位或局部清晰度突变。

### 跟踪与融合的实际参数

`PrintedPatch.features()` 用Shi–Tomasi角点，最多100个，`qualityLevel=0.005`、`minDistance=3`。取点环带位于修订半径的0.62–1.06倍，尽量跟随稳定发缘、图案边界，避开正在变化的眼睛。

`PrintedPatch.frame()` 使用金字塔LK前后向光流：窗口25×25、`maxLevel=3`，往返误差小于1.5像素才保留。至少6个有效点，RANSAC局部相似变换至少5个内点，重投影阈值1.5像素；逐帧累积平移、旋转与等比缩放，再从未修改的视频边界刷新跟踪点。

默认累积缩放范围为0.1–2.5倍；`--max-scale` 只能显式适配已经观察到的有限推近，不能拿放宽阈值代替效果检查。纹理与遮罩通过3×3矩阵投影，圆形遮罩约3像素羽化，然后做alpha混合。最终另编码H.264、CRF16、`yuv420p`，保留源帧率；这是有损重编码，不承诺像素无损。

当前实现没有深度、手指遮挡分割、布料形变、逐帧光照重建或大角度侧转补偿。大幅折叠、遮挡、透视变化、失焦或光照变化可能失败；跟踪成功也可能有贴片感。遇到这些情况应调整方法或重新生成，保留失败候选。

### 方法三：只恢复印花的眼睛和镜框

v11的S06原生4K贴纸仍睁眼，但虹膜和细金镜框弱化。第一份完整圆形贴脸候选在f000暴露明显边界，已拒收；不能因为眼睛更清楚就接受脸上多出一个圆盘。之后改用[`restore_printed_eyes.py`](../video-maker/tools/restore_printed_eyes.py)，只从M09原有RGBA母版取眼睛／镜框区域：

1. 标记母版与视频首帧的两只印刷眼睛。`eye_registration()`计算不镜像的二维相似变换，精确对齐这两对位置；不宣称完成任意透视或三维重建。
2. 在母版坐标中生成两个镜片椭圆和鼻梁连接区；当前椭圆半径95×78像素、中心在眼点下23像素，Gaussian羽化σ=18，再乘母版alpha。该配方按本份M09标定，不能直接套到不同尺寸或不同构图的母版。
3. 将母版RGB乘显式照明增益，S06为`0.9 0.87 0.76`，使原图纹理适配窗内暖色；不重新绘制虹膜，也不把恒定增益称为逐帧光照恢复。
4. 在未修改的1344×768代理上跟踪同一贴纸，再用`S⁻¹ T S`把运动映射回原生3840×2160，逐帧投影纹理和遮罩。代理只负责跟踪；世界画面原本已是模型原生4K，没有靠此步骤放大整片。
5. 完整处理120／240／336帧，以CRF16另编码，保留首帧、源片和失败候选，完整解码后写技术收据；之后仍需实际看完全部整景帧和全部原生局部，才能选择采用。非眼部既有纹理没有被自动恢复为母版，全画面有损重编码也不保证遮罩外像素逐点相等。

坐标单位需要分开：`--reference-eyes`是母版原生像素，`--target-eyes`是原生4K首帧像素，`--tracking-center/--tracking-radius`是1344×768跟踪代理像素。以下为S06实际参数，输出示例另用新名字：

```powershell
$eyeEpisode = 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
$eyeRun = '../vivhite-analysis-output/vivhite/autumn-journey/production-v11-native-4k-001'
video-maker/.venv/Scripts/python.exe video-maker/tools/restore_printed_eyes.py `
  --source "$eyeRun/sources/S06.mp4" --destination "$eyeRun/corrections/S06-eyes-reuse-example-001.mp4" `
  --reference "$eyeEpisode/assets/generated/production-v2-fasth3-001/masters/M09-sticker-v1.png" `
  --reference-eyes 455 545 705 520 --target-eyes 2427 1174 2515 1158 `
  --tracking-center 861 411 --tracking-radius 53 --frames 120 --gain-rgb 0.9 0.87 0.76
```

实际S06-v2由提交`6cad868`中的worker生成。两项单元检查覆盖双点配准不镜像，以及遮罩不覆盖整头／透明区；真实v2另经120帧完整解码、120帧整景和120帧原生印花复审，之后才接入采用清单。代码后来补强断管时的编码器清理，不热改正在运行的生成器。源片、取样图、处理代码、跟踪代码、参数和修订结果指纹见[本次收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S06-reference-restoration-v11-4k.json)。这一路线不能用于遮盖新增真人、修手臂或补救错误动作。

S07的M08布袋母版中，眼睛间距比M09贴纸母版小，因此不能照搬95×78像素的镜片遮罩。提交`f5651ce`增加显式`--mask-scale`，同步缩放镜片椭圆、桥部、纵向偏移与羽化；默认1保留旧配方。S07实际使用`--reference-eyes 809 463 904 450 --target-eyes 3328 925 3412 932 --tracking-center 1185 331 --tracking-radius 43 --mask-scale 0.39 --gain-rgb 0.98 0.88 0.80 --frames 120`，引用M08原始RGBA文件。先检查首帧配准，再处理120帧；修订v1的全部整景、全部原生眼部裁切及候选页实际复核通过后才采用。原始片两只手分别检查了全部120帧局部，未用眼部修补掩盖手部问题。对应[处理与复核收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S07-reference-restoration-v11-4k.json)记录实际代码和素材哈希。新增的小尺寸遮罩范围测试与原有两项测试均通过；此方法不保证恢复未覆盖的身体或头发印花细节。

S14的M05徽章还暴露了遮罩过小的另一种问题：前四张首帧试样保留了部分旧镜框，形成重影，均未用于完整视频。扩大遮罩后另看四张试样，采用06参数制作唯一一份完整修订：`--reference-eyes 530 714 775 690 --target-eyes 2653 1476 2802 1459 --tracking-center 956 505 --tracking-radius 115 --mask-scale 1.6 --gain-rgb 0.83 0.83 0.78 --frames 120`。原始与修订的120帧整景、120帧徽章局部及全部检测候选分别实际查看后才采用，原始片和八张试样均保留，详见[S14收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S14-reference-restoration-v11-4k.json)。

这个较大遮罩也覆盖了母版嘴部及相邻刘海，实际范围不能再写成“只改虹膜像素”；脚本名称或通用收据的eye/glasses描述不能替代逐案观察。徽章外圈、衣服和真实场景保留，其他未恢复印花仍偏软，全源片仍经过CRF16重编码。该镜原水迹沿徽章边侧及包面经过，没有穿过眼部；遇到实际遮挡穿过恢复区域时，应单独处理遮挡关系，不能直接照抄本镜参数。

S15提杯的原生4K版本使用M09母版，四张首帧试样逐一查看后采用01：`--reference-eyes 455 545 705 520 --target-eyes 1520 1255 1590 1248 --tracking-center 541 466 --tracking-radius 70 --mask-scale 1.08 --gain-rgb 0.86 0.84 0.76 --frames 120`。修复范围为眼睛／镜框及羽化内相邻印刷像素，真实手指没有经过这一区域；不能据此推断别的提杯镜头也没有遮挡。两版整景、印花及原有两只手分别实际看完120帧，确认提起与稳捧连续，才绑定采用修订。两版检测器均为零候选，依然完成整景语义检查。原始眼睛始终睁开，问题是细节保真；其余头发／身体仍软，整帧重新编码。详见[S15收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S15-reference-restoration-v11-4k.json)。

S16石阶布袋的M08印花中，原眼睛睁开，但虹膜／镜片被粗灰紫线替代。六张首帧试样均保留并查看，采用02，只做一份完整修订：`--reference-eyes 809 463 904 450 --target-eyes 1887 900 1957 880 --tracking-center 673 321 --tracking-radius 65 --mask-scale 0.55 --gain-rgb 0.90 0.88 0.84 --frames 120`。过窄试样残留旧镜片线，过宽试样影响头发／领口，因此不能只按“越大覆盖越全”选遮罩。实际采用遮罩也涉及相邻刘海、脸颊和嘴部，保留嘴下原布料褶皱；其余未恢复印花仍偏软。两版整景／印花各120帧、原始可见腿部120帧、原始299框和修订276框均实际复核后才采用，见[S16收据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S16-reference-restoration-v11-4k.json)。腿部交替迈动可见，但脚多在画外，不把局部序列检查扩写成完整足部触地验收。

## 可复用的处理命令

在仓库根目录使用已配置的Python环境，FFmpeg／FFprobe须在PATH中。以下参数来自实际S15提杯镜头，但输出使用新的示例文件名，不覆盖既有采用版本。迁移到其他镜头时必须重新标定坐标。

```powershell
$postPython = 'video-maker/.venv/Scripts/python.exe'
$postEpisode = 'series/vivhite/autumn-journey/episodes/01-autumn-journey'
$postRun = '../vivhite-analysis-output/vivhite/autumn-journey/production-v8-motion-768p-S15-002'
$postSource = "$postRun/sources/S15.mp4"
$postReference = "$postEpisode/assets/generated/production-v3-realism-001/scenes/S15-v2.png"
$postCorrected = "$postRun/corrections/S15-original-face-reuse-example-001.mp4"

& $postPython video-maker/tools/stabilize_printed_patch.py `
  --source $postSource --destination $postCorrected `
  --center 540 448 --radius 33 --used-seconds 5 `
  --texture-reference $postReference `
  --reference-box 610 500 740 600 --target-box 490 402 594 485
```

只固定首帧时，省略 `--texture-reference`、`--reference-box`、`--target-box` 三项，并使用另一个输出文件名；这三项必须一起提供或一起省略。所有版本保留原始输入。已存在的修订目标会被拒绝覆盖。

`--used-seconds` 决定**修订源片覆盖范围**，不修改导演稿时长。例如S15生成源片5秒／120帧，成片仍只使用4秒；S44同样是5秒源片、4秒成片。若检查策略要求全部源帧，就处理并检查完整5秒，不能只检查成片截取部分。

复用时还需核对实际输出帧数：输入提前结束不会由该参数补足画面；若输入自带音轨，当前工具会可选复制原音轨，没有按这个画面区间单独裁剪音频。本项目使用已规范化的无音轨源片，最终另配WAV，因此不能把这些示例直接当作带原声短视频的通用音视频裁剪器。

## 处理后如何复核和采用

1. 用 [`review_reference_clips.py`](../video-maker/tools/review_reference_clips.py) 的 `inspect(source, shot, evidence, output, face_model)` 导出完整帧图、时序图、检测候选和逐帧指标。这里 `shot['seconds']` 控制被统计的使用范围；检查完整源片时传入独立的镜头副本，将其设为实际 `sourceSeconds`，不修改正式计划。修订版本使用独立检查输出目录，保留原报告。
2. 用 [`inspect_printed_region.py`](../video-maker/tools/inspect_printed_region.py) 提取全部跟踪局部。它只保存原视频像素的检查图，不修改视频；当前命令仅支持120帧和240帧。14秒等其他长度不能宣称由这个工具完整覆盖，需另做全帧局部证据或扩展实现。
3. 实际查看全部源帧图、检测候选、原生尺寸首尾帧、全部局部图，以及与实际原图的并排对照。检查原有睁眼轮廓、虹膜、眼镜与脸部比例，也检查真实人物、手部、道具接触、背景连续性、遮挡和合成边缘。检测器零候选或运动阈值通过不等于内容通过；帧图审阅也不能冒称人工连续播放验收。
4. 经实际复核后再写入 `source-selections.json`：合并该镜条目，保留其他镜头，绑定修订文件 `path/sha256`、原文件 `parent/parentSha256`、处理 `receipt` 和独立 `inspectionReport`；串联修订时保留 `processingChain`，来源任务仍须是真实原生成任务。
5. 用 [`record_local_clip_review.py`](../video-maker/tools/record_local_clip_review.py) 记录明确采用或拒收的结论与实际观察。该工具核对所选文件、原文件、计划、完整证据范围及原图一致性声明，拒收结论另存历史；它不会自动作出审美或语义判断。不要未查看就填写 `--all-frames-viewed` 或 `--reference-fidelity-reviewed`。
6. 最终实际输入变化后重新进行[角色／披露审核](character-workflow.md)，再装配和检查真实成片。原视频通过记录不能直接覆盖回贴版本。

实际局部检查示例，须与待查看的修订版本匹配：

```powershell
$postEvidence = "$postEpisode/assets/generated/postprocess-reuse-example-001/review"
& $postPython video-maker/tools/inspect_printed_region.py `
  --source $postCorrected --evidence $postEvidence `
  --identity S15-reuse-example --center 540 448 --radius 33 --frames 120
```

截图、原图对照和检查拼图保存在项目中并提交Git。大型源片、修订片、完整请求、编码日志和收据原件保留在独立输出目录，公开项目保存必要的非敏感版本与处理记录；不要覆盖已经交付的影片或Release。

原生4K阶段使用本期[`inspect-print-details-v11.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/inspect-print-details-v11.py)支持完整120／240／336帧的原生局部导出。检测候选较多或涉及远处疑似人物时，另用[`extract-native-candidates-v11.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/extract-native-candidates-v11.py)：绑定实际源片与完整报告，保存**每个候选框**的原生裁切、坐标、指纹及分页JPEG，不只保存半秒间隔的代表例图。S09实际读完137个候选框，S10实际读完285个候选框；小裁切仍有疑问时，回到相同帧的更宽原生上下文核对。PNG导出、JPEG页阅读和逐张原尺寸展开是不同覆盖，须分别记录。此脚本不删除候选、不修改视频，也不自动批准内容。

## 慢放、标题与最终装配

[`retime_local_clip.py`](../video-maker/tools/retime_local_clip.py) 的 `retime()` 通过明确源区间、`setpts` 和FFmpeg `minterpolate` 另存慢放候选；插帧使用MCI、AOBMC、双向运动估计与可变块。当前只支持大于1且不超过16的慢放倍率，输出为5秒／120帧或10秒／240帧、24fps，不支持任意14秒输出。10秒配方包含0.25秒末端克隆填充，以补足插帧边缘，必须保留收据并检查尾部停顿。插帧会产生遮挡、透明翅膀或重影伪影，不能纠正本来就错误的蝴蝶结构或动作。

此前v7片尾曾使用该慢放路线；v8当前提交的是**原生14秒重新生成**，不能把历史慢放说明当成本轮已采用结论。任何源内变速也须保留既定成片镜头长度，改导演稿时长需要明确授权。

另有 [`retime_local_region.py`](../video-maker/tools/retime_local_region.py)，将指定矩形内部按真实源区间慢放、光流插帧并羽化融合，外围保持原时间线；不循环、无末帧克隆。收据记录局部源区间、倍率、羽化范围、完整命令和代码快照。它需要足够的真实前后帧，缩小源区间、降采样或关闭场景变化回退也可能产生翼缘重影，必须检查完整局部及边界；合成后的外围因有损编码不保证逐像素相同。两个真实编码测试核对源片未改、完整帧数、局部确实变化及外围同时刻运动保留，不能替代美术验收。

v8试做的第一份局部候选出现可见翼缘重影，已拒收；第二份完成编码但没有语义验收。用户随后明确取消蝴蝶减速，最终S48采用第五轮原生14秒视频，两份局部候选均不采用、不继续处理。普通24→30fps转换仍保留原动作速度，不能称为蝴蝶慢放。

[`reference_finisher.py`](../video-maker/tools/reference_finisher.py) 的 `titles()` 统一生成ASS标题，片头片尾共享Title／Subtitle样式，献词独立延迟淡入。`local_video_finisher.py` 按计划把24fps源片转为精确帧数的30fps镜段，再做画面装配；此处普通 `fps=30` 不是MCI运动插帧。`reference_finisher.finish()` 绑定实际声音与标题，检查角色收据，输出真实MP4并全量音视频解码；模型原生音轨没有进入本片最终混音。

[`inspect_local_video_film.py`](../video-maker/tools/inspect_local_video_film.py) 对成片所有编码帧与所选画面轨做对照，另输出检测候选、各镜样图、标题与献词淡入帧。它用于核对后期是否引入意外改动，不证明所选源片本来就正确；仍要解释全部候选，并区分机器覆盖、助手帧图审阅、人工连续观看和听音。

若要审阅装配后的每个整景帧，使用本期[`extract-encoded-whole-frames-v11.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/extract-encoded-whole-frames-v11.py)：传入`--film <实际MP4> --inspection <encoded-film-inspection.json> --destination <本期项目内的新目录>`。工具核对实际影片SHA、完整对照报告、3840×2160／30fps和帧数，将每个解码帧按顺序保存至32帧一页的JPEG，同时记录页码、首尾帧、数量和指纹。每格416×234，仅常规面积降采样；不是图像增强、换帧或内容修改。已存在但不同的证据拒绝覆盖，导出本身不批准内容。前十六镜63秒预览实际导出并看完60页／1890帧，另看全部原生候选和关键印花局部，见[检查记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/technical-prefix-v11-first16.md)。逐页查看缩略整景不能称为每个4K像素分别检查、人工连续播放或听音；细小眼睛、手指、遮挡仍须原生局部证据。

音频相关性阈值须说明校准范围，不能把前32秒上的经验值当作全部AAC内容的保证。v11的40秒阶段预览与原WAV相关性约0.999810／0.999814，未满足此前0.9999的经验门槛。保留失败材料后，用原WAV、同样的`-t 40 -c:a aac -b:a 256k -ar 48000`独立编码，再将两份AAC完整解码为双声道float32，确认每声道1920000个样本逐一完全相同，最大差值为0。这样将原曲身份、时间对齐和该参数的有损编码差异分别核对；没有通过降低门槛或修改原曲消除失败。实际影片、独立AAC、失败脚本、诊断和完成的worker均保留在`checkpoints/prefix-10-001/`，详见[40秒预览记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/technical-prefix-v11-first10.md)。数值一致仍不代替听音检查。

本期 [`materialize-sources-v8.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-sources-v8.py) 的 `validate_locked_timing()` 将前47镜时长及起点逐项锁定v7，仅允许S48变为14秒，总计205秒／6150帧。它调用共用导入器核对原任务、所选源片、完整证据与修订链，不负责生成或自动批准内容。

v9进一步用 [`materialize-sources-v9.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-sources-v9.py) 锁定与v8相同的**全部48镜时长和起点**，仅允许S44/S47源片指令及对应素材变化。闭帐门起点和手臂空间错误均重新生成，不用印花回贴修补人体；实际两段新片没有回贴、遮罩、换帧或变速。原生手臂局部检查与采用范围见[v9记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v9-motion-768p.md)。用户已确认3:25显示正确，因此未用补帧或改其他镜头长度处理播放器差异。

v10的S01检查暴露另一种漏检：同一条手臂上只有一只手，并不代表左右手接对。必须从肘、前臂、腕部跟到手掌，结合拇指侧、掌背、指关节与实际捏布接触核对，不能仅相信提示词的LEFT标签。用户要左手反手拉帘时，把掌心翻向镜头展示属于改错动作；本轮前两张翻掌候选被拒收。应先生成可辨认的自然反手首帧，再检查完整源片是否出现翻掌、换手或扭腕，详见[v10记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v10-left-hand-768p.md)。首帧选定不等于视频已验收；局部纹理回贴不能修复左右手错误。

## 实际案例与代码索引

v7实际来源收据中有10个镜头经过局部处理：S07、S11、S16、S20仅锁定首帧；S29、S37、S42、S44、S45、S46包含场景图回贴，S29另外串联首帧锁定。v8的S07、S15、S28、S44均另存场景图回贴版本；S47未用回贴。v8已发布，随后用户拒收其S44/S47，v9以新生成片替换两镜；旧版记录和素材保留。完整状态以[v8记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v8-motion-768p.md)、[v9记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v9-motion-768p.md)及各版本实际收据为准。

| 复用入口 | 职责 |
| --- | --- |
| [`stabilize_printed_patch.py`](../video-maker/tools/stabilize_printed_patch.py) | `PrintedPatch`跟踪；`project_reference_texture`映射原图；`stabilize`合成、编码、保存处理参数与哈希 |
| [`inspect_printed_region.py`](../video-maker/tools/inspect_printed_region.py) | 跟踪裁出原始视频局部，供实际查看 |
| [`inspect-closing-details.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/inspect-closing-details.py) | S48固定区域原生像素检查；完整336帧分页、原生首尾、输入与代码哈希，不编辑视频、不自动验收 |
| [`inspect-motion-details-v9.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/inspect-motion-details-v9.py) | 120帧原生局部分页、六个完整原生帧、JPEG查看副本；核对掌背、拇指、手腕、手臂连接和接触，检查图不改变源片 |
| [`inspect-audio-v9.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/inspect-audio-v9.py) | 完整AAC解码、205秒流时长／样本数、与实际WAV数值相关性；不替代听音验收 |
| [`review_reference_clips.py`](../video-maker/tools/review_reference_clips.py) | 完整源帧、时序、运动与真人脸候选证据 |
| [`record_local_clip_review.py`](../video-maker/tools/record_local_clip_review.py) | 显式采用／拒收、原图一致性与旧结论归档 |
| [`retime_local_clip.py`](../video-maker/tools/retime_local_clip.py) | 明确源区间的慢放候选与插帧收据 |
| [`retime_local_region.py`](../video-maker/tools/retime_local_region.py)、[`test_retime_local_region.py`](../video-maker/tools/tests/test_retime_local_region.py) | 局部慢放候选、外围时间线保留与真实编解码测试；本期未采用 |
| [`local_video_finisher.py`](../video-maker/tools/local_video_finisher.py) | 原生尺寸、固定镜头时长与精确帧数装配 |
| [`reference_finisher.py`](../video-maker/tools/reference_finisher.py) | 原创配乐、ASS标题、实际文件绑定及最终合成；音乐详见[专文](autumn-journey-music-generation.md) |
| [`inspect_local_video_film.py`](../video-maker/tools/inspect_local_video_film.py) | 成片全部编码帧对照、检测候选和标题淡入检查 |
| [`materialize-sources-v6.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-sources-v6.py) | 多批次真实源片与修订链的共用校验、独立复制 |
| [`test_stabilize_printed_patch.py`](../video-maker/tools/tests/test_stabilize_printed_patch.py)、[`test_local_clip_correction.py`](../video-maker/tools/tests/test_local_clip_correction.py) | 原图首帧回贴、运动跟踪、输入不变、边界及版本绑定验证 |
| [`test_retime_local_clip.py`](../video-maker/tools/tests/test_retime_local_clip.py)、[`test_v8_locked_timing.py`](../video-maker/tools/tests/test_v8_locked_timing.py) | 慢放源区间、帧数、历史保留与前47镜时长锁验证 |
| [`test_v9_locked_timing.py`](../video-maker/tools/tests/test_v9_locked_timing.py) | 拒绝任一镜头时长变化及其余46镜指令变动 |

这些能力为Python后处理worker，位于以Java为主的制作框架中；不将它们描述成Java渲染器已经内置的自动修复模型。

2026-11-18实读8001的OpenAPI还确认：FastH3的`negative_prompt`固定为空，`guidance_scale`固定1.0，`num_inference_steps`固定8，`task`固定`ref2va`，没有独立的像素级首帧锁定参数。正文写“不要某物”不是独立负向控制，也不能保证参考图里没有的物体不会生成。应使用清晰的正向构图与动作描述，再按真实结果验收；不虚构负向参数、不将语义提示称为强制锁帧。这个接口事实不证明某个具体幻觉一定由某个词造成。
