# 第一期制作稿源

当前正式版本是 v3，39 段，保持原数学内容，重写台词及人物反应，不在本期追加矩形棋盘或 Wilson 定理的完整证明。已经实际制成10分55秒的1080p30影片，见[制作记录](../docs/production-v3.md)及[实测导演稿](../docs/director-timed-v3.md)。

| 文件 | 用途 |
| --- | --- |
| `dialogue-v3.json` | 全部39段修订台词、动作、词触发及改稿依据。修改旁白时以此为源。 |
| `compose_production_v3.py` | 消费现有完整分析和数学验证，调用通用案例适配器，再应用v3修订。 |
| `production-plan-v3.json` | 已审核的可执行计划快照，包含真实数学状态和来源绑定。 |
| `write_dialogue_docs_v3.py` | 从v3稿源导出导演稿与逐段审查说明。 |
| `test_dialogue_v3.py` | 检查全量替换、动作短语和数学数据保留。 |
| `compose_production.py`、`production-plan-v2.json` | 历史v2，不作为新任务默认稿件。 |
| `director-template.json`、`bind_director.py` | 历史v1导演契约，`render`只导出文档。 |

在仓库根目录使用正式入口：

```powershell
.\scripts\produce-puzzle-video.ps1 -Build -VideoCodec h264_nvenc

# 先检查图形而不配音；其他参数见脚本param
.\scripts\produce-puzzle-video.ps1 -PreviewOnly -OutputDirectory D:/renders/puzzle-preview
```

没有NVIDIA编码器时省略 `-VideoCodec`，使用默认 `libx264`。默认声音为晓晓 `zh-CN-XiaoxiaoNeural`、语速 `+8%`；声音、语速、人物及输出目录可配置。人物仍是用户指定图片占位，可换预渲染形象视频，不直接驱动Live2D。

默认实际输出为仓库外 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/01-sliding-puzzle/production-v3/`；历史v2保持在 `puzzle-restyle/production-v2-cued/`。脚本先保存实际计划，冻结当前JAR/worker，使用独立TTS缓存，再校验人格、文案及实际外部素材的审核绑定。

创作前必须完整读取外部私有角色库的唯一人格，成稿后分别检查人格一致性与信息披露；执行[角色规约](../../../../../../docs/character-workflow.md)。改台词、动作或人物素材后重新审核。技术预览和数学数据验证不能替代语义审查。

已有分析输入在 `D:/workspace/vivhite-analysis-output/puzzle-restyle/`；完整 `analysis-report.json` 与 `math-verification.json` 参与稿源绑定。首次重建来源分析另用 `scripts/run-puzzle-case.ps1`，不把历史v1导出当作当前影片。默认生产要求见[长期约定](../../../../../../docs/video-production-defaults.md)。
