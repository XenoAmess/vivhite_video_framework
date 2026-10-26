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

第一期的内容源是 `BV1AV411V7SJ`，表达方法参考 `BV1i4aS6SEBR`；后两期沿用已经提炼的工具构造与操作演示方法，重新创作论证和画面，不搬用参考作者的声音、角色或素材。后两期现阶段交付导演稿，尚未生成配音、动画与成片；第一期现有渲染器不能直接覆盖一般图证明所需的全部图形。

第一期另有[完整 v3 台词稿](episodes/01-sliding-puzzle/docs/director-v3.md)和[逐段修订对照](episodes/01-sliding-puzzle/docs/dialogue-review-v3.md)，用于去掉模板化表达并重新调整人物反应；保持原39段数学内容，不追加后两期证明，也未覆盖已交付视频。v3 尚未重新制作。

每期的角色信息仅记录 `cast: ["vivhite"]`。创作时读取外部私有仓库中的唯一完整人格文档，成稿后追加人格一致性与信息披露两项审核，具体执行[角色与文案规约](../../../docs/character-workflow.md)。修改文案或人格版本后，旧审核失效，需重新审查。

仓库外的既有运行目录 `D:/workspace/vivhite-analysis-output/puzzle-restyle/` 保持原位，保存第一期的完整源证据与成片。仓库内路径已直接迁移，不设置旧路径跳转或兼容文件。
