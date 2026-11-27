# video-maker：自动化数学科普视频制作器

Java 包前缀：`com.xenoamess.vivhite_video_framework.maker`。

本模块负责将数学选题制作成科普视频。已实现从已验证分析报告到导演稿，并增加 Java 数学动画、Edge TTS 配音、实测音频排程、字幕与完整 MP4 导出。新制作入口与动态音色/人物配置详见 [制作流程](docs/production.md)。

旅行等无对白影像新增[参考图视频入口](docs/reference-video-production.md)：调用 FastH3 Omni Ref2VA、保留可恢复任务与失败材料、裁剪 2–10 秒镜头并装配画面。当前装配产物是待声音合成与语义验收的中间文件；远端生成状态见具体制作记录。

无声动态海报使用 `tools/produce_live2d_short.py` 渲染 Live2D 参数动画或插画网格动画与 Canvas 图层，通过人物审核绑定后逐帧合成 MP4。运行时设置、依赖和复现命令见[《余像》初版](../series/vivhite/art-shorts/episodes/01-afterimage/README.md)与[修订 v2](../series/vivhite/art-shorts/episodes/01-afterimage/revision-2/README.md)。

长版动态海报使用 `tools/produce_music_visualizer.py` 分析音轨频带，以 WebGL 逐帧绘制，并用本机 Chromium 的 WebCodecs 按章编码。原 AAC 音轨直接封装，最后一帧的显示时长使两轨精确到同一采样终点。[《余像·潮汐》制作记录](../series/vivhite/art-shorts/episodes/01-afterimage/tide/README.md)

已完成的单一海报可用 `tools/produce_music_loop.py` 循环配乐。制作器核对原视频和音乐，并验证成片所有画面包都按同一个周期排列。[《余像·原构图循环版》制作记录](../series/vivhite/art-shorts/episodes/01-afterimage/tide-loop/README.md)

同一文档另列 BF16 原生1344×768与逐镜3840×2160重生成入口，以及印花细节检查和另存修订工具；当前[768P／4K规约](../docs/local-video-768p-4k.md)替代历史2K路线，4K仍沿用服务端历史模型ID并单任务执行。印花跟踪的 `--max-scale` 可显式适配已观察到的镜头推近，默认上限2.5倍；技术成功仍须实际逐帧检查，不能自动作为成片内容通过的结论。

`durable_video_controller.py`也支持原始768P图像参考批次：检查实际1344×768源片，将每镜新首帧指纹绑定到独立源片目录，下载、全解码并保存技术检查点。`generationOnly`只完成源片和检查点，不自动通过语义审核或发布影片。DeepSeek衍生片的独立部署、冻结执行器及使用边界见[实际制作记录](../series/deepseek/autumn-journey/episodes/01-autumn-journey/production/production-v1-768p.md)。

局部纹理稳定、场景原图回贴、慢放插帧、完整源帧复核、标题和固定时长装配，另见[后处理方法与代码索引](../docs/autumn-journey-video-postprocessing.md)。

具体创作材料按[系列、课题和期号](../series/README.md)管理，本模块保存可复用的制作能力。任何新文案或改稿先读取外部私有角色仓库的完整人格，再按[角色与文案审核规约](../docs/character-workflow.md)检查人格一致性及信息披露；审核状态必须对应当前文案和人格版本。

逆序数课题已制作三期完整视频：第一期 [v3 制作记录](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/production-v3.md)（10:55）、第二期 [矩形棋盘证明](../series/math-education/inversion-count/episodes/02-rectangle-proof/docs/production-v1.md)（18:29.3）、第三期 [Wilson 定理证明](../series/math-education/inversion-count/episodes/03-wilson-theorem/docs/production-v1.md)（32:24）。配音为晓晓，人物为可替换的图片占位。`produce` 生成成片，`preview` 生成技术预览；历史 `render` 命令仍仅导出导演稿文档。未来制作沿用[默认约定](../docs/video-production-defaults.md)。

## 当前命令与案例

[v1 导演草稿：滑块拼图的奇偶不变量](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director.md)，20 镜，计划 12 分 20 秒。对应原创稿源文件为 [director-template.json](../series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/director-template.json)，包含全片制作设定；内容来自第一部视频，表达规则来自第二部。

v1 风格复核结论为需要结构重写，详见 [复分析与改稿依据](../series/math-education/inversion-count/episodes/01-sliding-puzzle/analysis/style-reanalysis-v2.md) 和 [90 秒方向样稿](../series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/opening-direction-v2.json)。本次由案例适配器消费这些创作要求，完成独立的 v2 全文与制作计划。当前 `render` 的结构校验、规则 ID 及实际成片技术检查均不代表风格相似度通过；现有 API `DirectorPlanner` 仍未自动读取独立的复分析文件。

```powershell
$analysisFile = 'D:/workspace/vivhite-analysis-output/puzzle-restyle/analysis-report.json'
$directorOut = 'D:/workspace/vivhite-analysis-output/puzzle-restyle/director'
$makerJar = 'video-maker/target/video-maker-0.1.0-SNAPSHOT.jar'

# 离线输出任务说明和 Responses API 请求 JSON
java -jar $makerJar prepare $analysisFile $directorOut

# 配置 OPENAI_API_KEY、OPENAI_MODEL 后可请求模型写完整导演稿
java -jar $makerJar generate $analysisFile $directorOut

# 导入既有原创导演 JSON 并校验、输出 Markdown
java -jar $makerJar render $analysisFile "$directorOut/director-plan.json" $directorOut
```

`prepare` 输出 `director-prompt.md`、`director-request.json`；`generate` 输出模型原始返回和导演计划，验证后才产出 `director.json`、`director.md`、`director-validation.json`。API 使用与分析器相同的环境变量（此命令单次请求、5 分钟超时，不自动重试）；本例实际使用助手创作稿，未执行付费 API 请求。独立 API 路径尚未联网验证。

校验要求：分析文件 SHA-256 完全一致；所有镜头从 0 连续计时到片尾；所有知识点均被引用；每镜都有旁白、构图、动作、音频说明、风格规则与内容源语音段；拒绝未知引用。旁白字母/数字字符计数不得超过 6.5/秒，作为过载防线；这不是实际 TTS 时长测量。画面与数学是否正确仍需专门验证，不能从 JSON 合法推断。

本例一键重建见根目录 `scripts/run-puzzle-case.ps1`；案例辅助脚本只绑定同一对视频指纹，不对其他主题套用模板。

第一期[台词复审](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)已逐段改写全部 39 段，完整稿见 [director-v3.md](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director-v3.md)，实际配音时码见 [director-timed-v3.md](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director-timed-v3.md)。v3 使用独立稿源与适配器，不覆盖历史 v2；制作脚本默认选择 v3。第二、三期使用新增的[通用证明动画场景](docs/proof-scene.md)，执行真实图上滑动、代数置换和分阶段表格/矩阵，而非把证明稿直接铺成静态幻灯片。配音与渲染前须检查对应实际计划、完整人格及外部素材的审核绑定。

## 输入与输出

- 输入：数学主题、目标受众、目标时长、语言、画面规格，以及可选的视频分析报告或风格配置。
- 输出：成片，以及可追溯的文案、分镜、素材引用、字幕、渲染配置和制作记录。

本地生成式视频使用 `tools/local_video_pipeline.py`，默认连接 `http://192.168.1.11:8080/v1`。参考图生成和原生4K再生成共用网关、素材上传与任务队列。参数、历史任务恢复与校验见[本地视频制作规约](../docs/local-video-768p-4k.md)。

## 制作流程

1. 从系列、课题和本期清单确定角色，读取每个角色的唯一完整人格文档；明确主题、受众、学习目标和需要解释的数学概念，核验公式、推导与示例。
2. 结合完整人格规划叙事结构，生成文案和逐镜头分镜，为每段讲解分配时长。
3. 对成稿分别进行人格一致性与信息披露语义审核；将详细依据保存在私有角色仓库，将必要版本引用和结果保存在本期。文案或人格变化后重新审核。
4. 审核通过后，根据风格配置生成或选择图形、公式、动画、配音、字幕和音效，并按时间轴合成、渲染视频。
5. 检查数学表达、音画同步、字幕、时长和导出规格；根据质量检查及分析器反馈调整制作参数，记录可复现的制作过程。

## 与分析器协作

- 将分析器报告中的配色、版式、镜头节奏、公式呈现、叙事策略等转为制作参数。
- 参考分镜和表达方法，结合新的数学主题重新创作文案与画面。
- 消费有版本标识的结构化报告，不直接依赖分析器的内部实现，也不调用其 GPT 接口。
- 对缺失证据、低置信度结论和不适用于当前选题的建议保留可配置的处理方式。

## 构建

在仓库根目录执行：

```powershell
.\mvnw.cmd -pl video-maker -am verify
```

macOS / Linux 使用 `./mvnw -pl video-maker -am verify`。入口为 `DirectorMain`；通用命令及本例完整制作方法见 [production.md](docs/production.md)。
