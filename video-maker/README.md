# video-maker：自动化数学科普视频制作器

Java 包前缀：`com.xenoamess.vivhite_video_framework.maker`。

本模块负责将数学选题制作成科普视频。已实现从已验证分析报告到导演稿，并增加 Java 数学动画、Edge TTS 配音、实测音频排程、字幕与完整 MP4 导出。新制作入口与动态音色/人物配置详见 [制作流程](docs/production.md)。

具体创作材料按[系列、课题和期号](../series/README.md)管理，本模块保存可复用的制作能力。任何新文案或改稿先读取外部私有角色仓库的完整人格，再按[角色与文案审核规约](../docs/character-workflow.md)检查人格一致性及信息披露；审核状态必须对应当前文案和人格版本。

当前案例使用 [v2 制作计划](../series/math-education/inversion-count/episodes/01-sliding-puzzle/authoring/production-plan-v2.json)，包含39段原创旁白和可执行数学状态；配音为晓晓，人物为可替换的图片占位。`produce` 生成成片，`preview` 生成预览；历史 `render` 命令仍仅导出导演稿文档。

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

第一期后续[台词复审](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)已逐段改写实际成片的全部 39 段，完整新稿见 [director-v3.md](../series/math-education/inversion-count/episodes/01-sliding-puzzle/docs/director-v3.md)。v3 使用独立稿源与适配器，不覆盖历史 v2；制作脚本默认选择 v3，新稿尚未配音或渲染。配音与渲染前须检查对应实际计划、完整人格及外部素材的审核绑定。

## 输入与输出

- 输入：数学主题、目标受众、目标时长、语言、画面规格，以及可选的视频分析报告或风格配置。
- 输出：成片，以及可追溯的文案、分镜、素材引用、字幕、渲染配置和制作记录。

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
