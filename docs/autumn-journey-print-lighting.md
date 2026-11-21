# 周边印花修复后的明度与场景光照

当前状态：本轮明度修订和完整成片复核已完成，[4K审片版](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v13-4k-20261121)的六个附件已实际完整回下载并核验SHA-256；用户审美待审。下面的未完成、拦截与排队描述均为当时的历史记录。

2026-11-21，用户指出修复后的部分周边面部过亮。该问题成立：恢复原始睁眼纹样、金色镜框和微笑后，部分修复区域没有充分继承现场的阴影、色温与印刷材质，局部清晰度也高于周围图案。此前的纹样审核不能代替光照融合审核。

本轮增加的明度复核尚未完成最终成片验收。旧源片、旧修复、失败试样、检查图片和已发布版本均保留。渲染队列继续工作；最终装配被 [`print-lighting-hold-v14.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-hold-v14.json) 拦截，不能把未解决的亮脸直接沿用到交付影片。历史通过结论不能自动关闭本轮问题。

本轮已完成 S42 杯子与 S43 露营立牌修订源片的助手逐帧复核并更新选片：每段完整 120 帧全景和 120 帧印花区域、原生全景与印花首末帧，以及分别 53／126 个检测候选均已实际查看。新版只校准局部印花的颜色与柔化，保留原来动作和时长；逐段依据见 [S42](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S42-print-lighting-source-review-v14-r1.json) 和 [S43](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S43-print-lighting-source-review-v14-r1.json)。这两段的源片结论不代表其余镜头或最终成片已通过明度审核。

后续完成 [S38 挂件](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S38-print-lighting-source-review-v14-r1.json) 与 [S03 徽章](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S03-print-lighting-source-review-v14-r1.json) 的同范围复核和替换；检测候选分别为 183／119 个。S38 保留从阴影转入暖光的原片变化，S03 保留旧版整块徽章的配准与摆动。四段均从原始视频重新编码，原版继续保留。其余修订候选仍待完整审阅，全片明度拦截继续有效。

第三批又完成 S06 电车窗贴纸、S09 水壶贴纸、S12 划船贴纸、S15 咖啡杯贴纸和 S45 行李箱挂件的同范围复核及选片，累计 9 段明度修订。每段实际查看完整 120 帧全景、120 帧印花细节、原生全景与印花首末帧及全部检测候选；候选数量依次为 35、141、4、1、83。全部印花外原片／新版帧对也重新比较，旧版分数未复用。逐段观察和哈希见各自 `production/SXX-print-lighting-source-review-v14-rN.json`，合并进度见 [`print-lighting-audit-v14-stage3.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage3.json)。这些是助手通过有序检查页形成的源片结论，不等于人工连续播放或最终成片验收；全片明度拦截仍开启。

S09 与 S15 的首轮明度候选还残留原始生成画面的嘴部竖线，因此被拒绝。第二版在原有配准和颜色增益基础上，将原始图案投影范围明确扩大至嘴与下巴，并限制遮罩下界和羽化；重新从未修改的原始视频合成，去除竖线并保留原始微笑。不能仅因眼睛已稳定、脸已变暗就认定整个面部合格，也不能把重做后的覆盖范围记成旧候选已全部审过。各轮候选和实际查看范围均独立保留。

第四批完成 S19 火车窗边布包、S24 沙地挂件、S26 车内布包、S28 集市咖啡杯和 S46 车窗放松手掌旁的贴纸，累计 14 段修订。每段实际查看完整 120 帧全景和 120 帧印花细节、原生全景与印花首末帧及全部检测候选；候选数量依次为 8、118、18、36、30。印花外的全部 120 对原生帧重新比较。S19、S26 使用的是 M08 布包母版，不能误记成明信片。S46 另查看完整 120 帧扩大手部区域的有序检查页，确认后保留原手部动作，没有做解剖修补。记录见 [`print-lighting-audit-v14-stage4.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage4.json)。

这批保留车厢、沙地和集市遮棚各自的光照，不统一套用曝光值。S46 完整 5 秒、S28 完整 5 秒及其他已锁定镜头时长均未改动。以上仍是通过有序检查页和原生细节形成的助手源片结论，不是人工连续播放、音频验收或整片通过；全片明度拦截继续开启。

第五批完成 S29 港口玩偶与徽章、S31 渡轮挂件、S35 溪边水壶贴纸和 S44 帐篷布包，累计选定 18 段明度修订。每段实际查看全部 120 帧全景；S29 两个印花区域共查看 240 帧，其余各 120 帧，另查看原生全景与各印花首末帧及全部检测候选。候选数量依次为 0、126、95、11；零候选不能代替场景中人员与面部的语义检查。印花外的全部 120 对原生帧均重新比较。记录见 [`print-lighting-audit-v14-stage5.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage5.json)。

S44 首轮遮罩覆盖头发过多，原生印花末帧有浅色外边缘，因此仅凭实际查看的首末细节拒绝该候选，其余未查看页不冒记为已审。第二版缩小到面部范围，再完成全部检查。开帐篷仍是一次向下拉开拉链、松开拉头、空手返回并向左掀开布帘；没有修改手部解剖或镜头长度。S47 摆正玩偶的原始 4K 源片因印绣五官偏离母版而拒绝，原图眼睛一直是睁开的；明度候选已准备，尚未采用。旧版、失败版和未审图片均进入素材留存，但图片入库不代表审核通过。所有锁定时长保持不变，全片明度拦截继续开启。

第六批完成 S47 摆正玩偶、S07 秋叶散步、S14 雨天候车亭、S17 温室立牌，以及另行重生成的新 S05 骑行镜头，累计选定 23 段明度修订。其中原始 4K 运行目录为 22 段，新 S05 在独立运行目录中另计 1 段；旧的无车座 S05 仍为拒绝状态，不能回填。每段实际查看全部 120 帧全景、120 帧印花区域、原生全景与印花首末帧和全部检测候选；检测候选数量依次为 58、365、66、12、67。S17 使用 M02 成年比例立牌母版，不能与其他 Q 版周边混记。S47 在第五批时仍待审，本批已完成并采用，新结论不改写历史记录。

新 S05 另实际查看原始视频全部 120 帧车座／臀部区域、全部 120 帧腿／曲柄区域和全部 64 个原始检测候选，核对车座、座轨、夹具、座管和持续踩踏。修订版全部 52 个切换候选、S07 全部 19 个切换候选，都保留在机器报告中；助手对照完整有序全景帧，将其判断为连续骑行／步行、跟拍与树叶运动，没有观察到硬切背景。不能直接删除检测标记，或把阈值未通过说成自动通过。新 S05 的原始印花只实际放大查看第 0—3 帧及原生首帧，已足以发现偏离母版的眼睛、眼镜和嘴形；该拒绝记录不冒称其余原始印花细节页已查看。修订后的印花则完整检查全部 120 帧。

以上五段印花外的全部 120 对原生帧也重新比较，独立区域首末 PNG 留存但未逐张查看，不能把数值比较写成人工看过所有裁图。全部锁定动作、片段时长与 205 秒／6150 帧装配要求保持。第六批记录见 [`print-lighting-audit-v14-stage6.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage6.json)，新骑行记录见 [`S05-new-native-print-lighting-source-review-v14-r1.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/S05-new-native-print-lighting-source-review-v14-r1.json)。其余 11 段明度候选尚待完整审阅，高山湖单次 10 秒源片尚在生成；全片明度拦截继续开启，不代表成片已验收。

第七批完成其余 S11、S13、S16、S21、S22、S30、S32、S36、S37、S40、S41，累计 34／34 段明度修订：原始运行目录 33 段，独立新 S05 另计 1 段。每段实际查看全部 120 帧有序全景；S41 的玩偶、徽章分别查看 120 帧印花区域，共 240 帧，其余每段各 120 帧，另查看原生全景与各印花首末帧和全部检测候选。上述 11 段的候选数依次为 254、50、314、15、0、146、27、82、176、4、349。全部印花外 120 对原生帧重新比较；另存的独立区域首末 PNG 未逐张查看，留存不等于审核。三档试样的第 0／60／119 帧已实际比较，不代表所有未采用试样的视频均完整审过。

S11、S13、S16 的较小遮罩试样残留生成嘴形，依据实际比较的三个静帧拒绝后，采用明确覆盖嘴与下巴的新候选，再完成完整源片检查。S16 的 11 个切换候选全部保留并对照有序全景逐一解决，未观察到硬切；这段实际是林间台阶旁的小幅身体、镜头和布包晃动，脚部多数在画外，不能误记为完整走路检查。S21 实际为缆车车厢中的旅行包与玩偶。S37 是缓慢向镜头靠近，不能夸称全程均匀快速迈步；S41 分别匹配玩偶布料与徽章在蓝灰暮光下的响应。各段仍使用原来已经睁开的眼睛纹样、金色镜框与微笑，没有闭眼变睁眼的修订。

第七批绑定与覆盖见 [`print-lighting-audit-v14-stage7.json`](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-audit-v14-stage7.json)。34／34 仅表示本轮已完成的明度修订源片，不是完整影片交付进度。最终采用素材目前为 47／48；新的 S20 高山湖单次 10 秒视频仍在生成，必须另做整段连续性、印花、人员及源片绑定检查，不回填旧分窗视频。全片明度拦截保持开启，尚未完成最终装配、跨镜头与音画审核。全部镜长、S46 完整 5 秒、S48 完整 14 秒以及全片 205 秒／6150 帧均保持不变。

另将上述 34 段当前采用源片的第 0 帧场景，与各印花区域第 0／119 帧并排，形成 6 张跨镜头检查页（S29、S41 各含两个区域，共 36 个印花区域），助手已全部实际查看。此范围内未观察到新的孤立亮脸块或遮罩光边；S38 仍保留阴影转暖光，S41 两种材质分别匹配暮光，S43 匹配画内露营灯。部分外层生成服装、头发与印花细节仍较软，不声称所有细节都是真实恢复。这个首末帧横向比较不取代完整源片或成片审阅，见[跨镜头补充记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/print-lighting-cross-shot-review-v14.json)。

为减少最后一段出片后的等待，另从当前实际采用源片准备了 47 段独立 30fps 缓存，并将全部 5850 个缓存帧与同一源片的相同帧率转换结果做原生 3840×2160 YUV 比较。原运行目录 46 段最低逐帧 PSNR 为 42.59dB，新 S05 的 150 帧最低为 43.99dB；这些有损编码比较不代表像素相同或语义通过。旧缓存保留，后续只按当前源片指纹、镜长及配方匹配复用，禁止混入修订前亮脸或旧 S05／S20。新的 S20 所占 300 个最终帧仍未就绪，47 段没有拼成连续影片；正式绑定与成片审核仍待完成。实际版本和指纹见[装配准备检查点](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/native4k-v13-assembly-preparation-20261121.json)。

还对 S01、S04、S08、S27 四段未做印花恢复的原生源片做了场景与首末印花的并排补查，S08 含徽章和玩偶两个区域，共五行。已实际查看这张有界检查页；该范围内没有发现需要新增修订的孤立亮脸块。S01 末帧印花裁图仅覆盖上半头部与眼睛，不冒称完整下半脸可见；原生挂件的细虹膜仍较软，也不宣称已恢复成精确母版。此次不改源片、不重新授予完整动作通过。新保存的 S01／S04 整组查看副本只用于留存，不记为本次重新看过全部帧。见[未修复源片的光照补查](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/original-print-lighting-context-review-v14.json)。

2026-11-21 14:18 更新：S20 新的单次 10 秒原生 4K 已生成并下载，全部 48 段的生成工作完成；最终可采用素材仍为 47／48。助手实际查看新 S20 全部 240 帧有序全景、原生全景首末帧、全部 212 个原生检测裁图，以及玩偶和徽章各自的原生印花首末帧。湖景、旧路径、背包与运镜连续，未观察到新增人员、真人脸或硬切；原始输出的玩偶眼睛形状、头部和徽章印花漂移，因此拒绝原始输出，不能直接拼入成片。

五轮静帧试样全部保留。前几轮分别发现旧嘴重影、带入领口、下巴边界或三点配准使眼睛纵向拉长；这些拒绝仅按实际查看的静帧范围记录，不冒称全部候选视频看过。第五轮回到保留虹膜与镜框比例的双眼配准，扩大面部遮罩、保留较长下缘羽化，并使用较暗的独立材质增益；三个时间点的全部三档、两个印花区域均实际比较，另核对所选档的原生首末细节。此时只选定整段输出候选，尚未完成修订视频全部 240 帧复审。旧的分窗 S20 不回填。当前阶段百分比和预计节点见[进度快照](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/native4k-progress-20261121-1418.json)，最终影片尚未装配或通过审核。

2026-11-21 14:57 更新：新的 S20 修订版已完成全部 240 帧全景、玩偶及徽章各 240 帧细节、原生全景及两种印花首末帧、全部 141 个原生检测裁图的实际审阅并采用。五官保持原设定睁眼，未观察到自主点头、重影或可见滑移；两种材质分别降低明度。全部 240 对印花外原生帧另做有损编码比较，独立区域首末裁图只留存、不冒称逐张看过。新增修订来自同一未改动原片的一次编码，完整惰性道具模板包含轮廓和邻近羽化，不能称为只改眼部。此前 34 段加本次 S20，累计 35 段明度修订；最终采用素材达到 48／48。

已按精确源片、全部动作审阅及指纹绑定解除源片装配拦截，独立成片发布检查仍未通过，不能将此写成成片验收。48 段共 6150 个画面帧准备完毕并全量解码，S20 新的 300 个 30fps 缓存帧也与同一采用源片做原生 YUV 比较，最低逐帧 PSNR 42.37dB；另外 5850 帧沿用此前已比较且逐一核验的当前缓存。实际最终制作计划与 53 个绑定输入已完成两项独立语义审核，公开库只导出版本及结论。当前正在编码完整 4K 成片，之后还要检查全部输出、字幕、音轨并验证 Release 下载。全片保持 205 秒／6150 帧，S20 为 10 秒，S46 为完整 5 秒，S48 为 14 秒，蝴蝶原速度与旧版本全部保留。见[源片完成检查点](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/native4k-source-completion-20261121.json)。

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

2026-11-21 最终输出更新：35段／38个印花区域的采用源片与完整4K编码后画面复核已完成，全部6150帧有序图册、18张原生重点、13张字幕检查代理和20张最终候选图册实际查看；另完整查看7张印花首末对照页，共76组原生区域。此范围未观察到新发光脸块或眼睛形变。源片拦截和最终发布检查已分别解决，具体指纹及检查边界见[完整4K制作记录](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/production-v13-native-4k.md)及其审核JSON。前述各阶段状态均为历史快照；此处仍不代表人工连续播放、听音或用户审美验收。

完整4K已通过上传、服务端摘要核对和六个附件的实际完整回下载验证，见[v13审片Release](https://github.com/XenoAmess/vivhite_video_framework/releases/tag/autumn-journey-v13-4k-20261121)及[发布凭据](../series/vivhite/autumn-journey/episodes/01-autumn-journey/production/release-v13-native-4k.json)。历史阶段的拦截描述保留作过程记录，当前以独立最终检查和发布凭据为准。
