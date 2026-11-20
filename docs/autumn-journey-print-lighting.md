# 周边印花修复后的明度与场景光照

2026-11-21，用户指出修复后的部分周边面部过亮。该问题成立：恢复原始睁眼纹样、金色镜框和微笑后，部分修复区域没有充分继承现场的阴影、色温与印刷材质，局部清晰度也高于周围图案。此前的纹样审核不能代替光照融合审核。

本轮增加的明度复核尚未完成最终成片验收。旧源片、旧修复、失败试样、检查图片和已发布版本均保留。渲染队列继续工作；最终装配被 [`print-lighting-hold-v14.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-hold-v14.json) 拦截，不能把未解决的亮脸直接沿用到交付影片。历史通过结论不能自动关闭本轮问题。

本轮已完成 S42 杯子与 S43 露营立牌修订源片的助手逐帧复核并更新选片：每段完整 120 帧全景和 120 帧印花区域、原生全景与印花首末帧，以及分别 53／126 个检测候选均已实际查看。新版只校准局部印花的颜色与柔化，保留原来动作和时长；逐段依据见 [S42](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S42-print-lighting-source-review-v14-r1.json) 和 [S43](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S43-print-lighting-source-review-v14-r1.json)。这两段的源片结论不代表其余镜头或最终成片已通过明度审核。

后续完成 [S38 挂件](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S38-print-lighting-source-review-v14-r1.json) 与 [S03 徽章](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S03-print-lighting-source-review-v14-r1.json) 的同范围复核和替换；检测候选分别为 183／119 个。S38 保留从阴影转入暖光的原片变化，S03 保留旧版整块徽章的配准与摆动。四段均从原始视频重新编码，原版继续保留。其余修订候选仍待完整审阅，全片明度拦截继续有效。

第三批又完成 S06 电车窗贴纸、S09 水壶贴纸、S12 划船贴纸、S15 咖啡杯贴纸和 S45 行李箱挂件的同范围复核及选片，累计 9 段明度修订。每段实际查看完整 120 帧全景、120 帧印花细节、原生全景与印花首末帧及全部检测候选；候选数量依次为 35、141、4、1、83。全部印花外原片／新版帧对也重新比较，旧版分数未复用。逐段观察和哈希见各自 `production/SXX-print-lighting-source-review-v14-rN.json`，合并进度见 [`print-lighting-audit-v14-stage3.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage3.json)。这些是助手通过有序检查页形成的源片结论，不等于人工连续播放或最终成片验收；全片明度拦截仍开启。

S09 与 S15 的首轮明度候选还残留原始生成画面的嘴部竖线，因此被拒绝。第二版在原有配准和颜色增益基础上，将原始图案投影范围明确扩大至嘴与下巴，并限制遮罩下界和羽化；重新从未修改的原始视频合成，去除竖线并保留原始微笑。不能仅因眼睛已稳定、脸已变暗就认定整个面部合格，也不能把重做后的覆盖范围记成旧候选已全部审过。各轮候选和实际查看范围均独立保留。

## 实际处理方法

1. 对每个已选修复区域提取原片与修复版的首帧、中间帧、末帧，保存完整原生裁图和并排查看图。该步骤用于筛查光照问题，不冒充全片逐帧审核。
2. 在对应周边母版上选择可见的非眼部肤色像素，通过原有眼部或三点配准映射到实际原片。排除虹膜、睫毛和部分镜框，统计 RGB 通道比例，得到调色起点。它测量的是编码 RGB 数值，未做相机标定、线性光照反演或物理曝光测量，不能把比例直接说成感知明度或曝光档数。
3. 人工语义检查原始画面的实际灯光、阴影、反光与周边材质，再选择增益。配准与原片脸形有差异时，肤色采样仍可能混入头发或阴影，必须拒绝不合适的自动建议。不能因为数值匹配就判定自然，也不能把所有镜头统一压暗。
4. 对光照较稳定的镜头使用固定 RGB 增益。对 S38 这类后半段逐渐变暖的镜头，可测量三个时间点，使用平滑的 RGB 关键帧曲线，保留原片的暖光变化。曲线以完整源片的帧号绑定；不改变动作速度与镜头长度，不逐帧自动测光造成明度跳动。
5. 按图案投影到原生视频后的实际大小控制轻微软化。参考图上的固定模糊半径不能通用：同样两像素，对缩小到杯上的贴纸和接近一比一的亚克力印花影响不同。本轮试样以原生画面约半像素作为起点，参考空间半径另有限制；实际效果仍逐镜检查。S43 第一轮过糊的试样保留，不能采用。
6. 从未改动的原始 4K 源片重新合成局部印花，一次 CRF16 编码另存新候选。不要继续在已修复 MP4 上反复编码。完整惰性道具模板若需要光照曲线，只调整其中的原始面部投影贡献，不对整个道具、背景或人物调色。
7. 对新候选完整解码，查看全部源帧、全部印花细节页及检测器候选。另比较印花外区域的全部帧对，检查是否只有有损编码差异；PSNR 不能代替动作、解剖、人员数量和审美审核。更新选片后，必须按新视频 SHA-256 失效旧缓存，并重新审核最终装配。

所有参考人物眼睛原本就是睁开的。本轮不以“闭眼变睁眼”解释印花漂移或眩亮，也不把周边图案的脸误当成允许出现的真人脸。

S03 的历史修复采用整块徽章矩形配准及圆形遮罩，与一般的面部投影不同。因此单独保留其原始母版矩形、目标矩形、原生分辨率圆形遮罩及边缘光流跟踪，只在该徽章印面内校准颜色与柔化。三档样张保存原片、旧亮版与新候选的首／中／末帧；不能为了复用眼部工具而静默改变徽章形状。新徽章候选仍须完整解码和实际逐帧审阅，不由测光函数自动采用。

## 代码与数据入口

| 环节 | 文件 |
| --- | --- |
| 原片与历史修复的三点对照 | [`prepare-print-lighting-audit-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-print-lighting-audit-v14.py) |
| 非眼部肤色采样与增益建议 | [`print_lighting_calibration.py`](../video-maker/tools/print_lighting_calibration.py) |
| 固定增益、光照曲线与局部柔化 | [`restore_printed_regions_lighting.py`](../video-maker/tools/restore_printed_regions_lighting.py) |
| 历史整块徽章配准的光照修订 | [`restore_printed_badge_lighting.py`](../video-maker/tools/restore_printed_badge_lighting.py) |
| 徽章原片／旧亮版／三档候选样张 | [`prepare-badge-lighting-trials-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-badge-lighting-trials-v14.py) |
| 三档候选样张及可选光照曲线 | [`prepare-print-lighting-trials-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-print-lighting-trials-v14.py) |
| 冻结实际代码、配置与输入后渲染 | [`render-print-lighting-candidates-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/render-print-lighting-candidates-v14.py) |
| 全量解码、印花页、检测候选与区域比较 | [`prepare-print-lighting-evidence-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/prepare-print-lighting-evidence-v14.py) |
| 沿用已核对区域坐标、重算新版全部帧对 | [`compare-print-lighting-outside-v14.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/compare-print-lighting-outside-v14.py) |
| 未解决明度问题时阻止正式装配 | [`materialize-native4k-sources-v13.py`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/materialize-native4k-sources-v13.py) |

图像与样张保存在本期 `assets/generated/production-v11-native-4k-001/review/lighting-v14-*`。新的本地视频候选保存在仓库外运行目录 `production-v11-native-4k-001/corrections/*-print-lighting-v14-*.mp4`；配置、检查记录与图片入 Git，大型视频沿用发布资产交付。正式选片前，候选一律标记为待审核。

相关测试覆盖偏暗暖光的测量、错误肤色样本拒绝、大型母版的 OpenCV 采样限制、RGB 通道顺序、原输入不变、三点配准、过度柔化拒绝、曲线端点与连续性、惰性模板外围不被曲线改色，以及未解决光照问题时禁止装配。测试通过只证明这些软件行为。

原有印花稳定、原图回贴、人员与动作错误处理方法见 [`autumn-journey-video-postprocessing.md`](autumn-journey-video-postprocessing.md)。
