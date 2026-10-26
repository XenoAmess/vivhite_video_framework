# 数学教育系列 · 逆序数课题

课题 ID：`inversion-count`；机器可读目录见 [topic.json](topic.json)。三期分别承担不同深度的结论，第一期维持已交付内容，不追加后两期的证明。

| 期数 | 主题与边界 | 稿件与材料 |
| --- | --- | --- |
| 1 | 通过滑块拼图构造奇偶判别器；展示有限棋盘的枚举与合法路径，不把小棋盘验证当作任意大棋盘的证明 | [第一期](episodes/01-sliding-puzzle/README.md) |
| 2 | 对所有有限、完整、至少两行两列的矩形棋盘，完整证明奇偶条件既必要又充分；不借用 Wilson 定理作为黑箱 | [第二期](episodes/02-rectangle-proof/README.md) |
| 3 | 从头证明 Wilson 一般图定理，讲清图的前提、置换群结构、环及特殊图的例外 | [第三期](episodes/03-wilson-theorem/README.md) |

```text
inversion-count/
  topic.json
  episodes/
    01-sliding-puzzle/
      episode.json
      case.json                   两个来源视频及本地分析配置
      analysis/                   内容、风格、覆盖与数学验证记录
      analysis-authoring/         人工辅助分析及复算工具
      authoring/                  原创文案模板与制作计划适配器
      docs/                       导演稿及已完成制作记录
    02-rectangle-proof/
    03-wilson-theorem/
```

第一期的内容源是 `BV1AV411V7SJ`，表达方法参考 `BV1i4aS6SEBR`；后两期沿用已经提炼的工具构造与操作演示方法，重新创作论证和画面，不搬用参考作者的声音、角色或素材。三期均已用 `video-maker` 制作完整1080p30影片，第二、三期使用新增的图滑动、置换、加耳及分阶段证明后端。

| 当前成片 | 实测片长 | 制作记录 |
| --- | --- | --- |
| 第一期 v3 | 10:55 | [制作记录及实测导演稿](episodes/01-sliding-puzzle/docs/production-v3.md) |
| 第二期 v1 | 18:29.3 | [制作记录及实测导演稿](episodes/02-rectangle-proof/docs/production-v1.md) |
| 第三期 v1 | 32:24 | [制作记录及实测导演稿](episodes/03-wilson-theorem/docs/production-v1.md) |

第一期[完整 v3 台词稿](episodes/01-sliding-puzzle/docs/director-v3.md)和[逐段修订对照](episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)用于去掉模板化表达并重新调整人物反应；保持原39段数学内容，不追加后两期证明，已在独立目录重新制作。两部证明片保留原始预算稿，实际时码以各期 `docs/director-timed-*.md` 为准；第三期没有把49:30预算当作静帧补时目标。

每期的角色信息仅记录 `cast: ["vivhite"]`。创作时读取外部私有仓库中的唯一完整人格文档，成稿后追加人格一致性与信息披露两项审核，具体执行[角色与文案规约](../../../docs/character-workflow.md)。修改文案或人格版本后，旧审核失效，需重新审查。

三期当前成片在仓库外 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/` 下按期隔离，附字幕、音轨、时间轴、运行快照及实际编码证据。既有 `D:/workspace/vivhite-analysis-output/puzzle-restyle/` 保持原位，保存来源证据与第一期历史版本。仓库内路径已直接迁移，不设置旧路径跳转或兼容文件。后续制作沿用[默认规约](../../../docs/video-production-defaults.md)，接手见[交接文档](../../../docs/video-production-handoff.md)。
