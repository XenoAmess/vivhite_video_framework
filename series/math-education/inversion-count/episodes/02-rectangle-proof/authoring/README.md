# 第二期可执行制作源

`compose_production.py` 逐镜读取完整导演稿、原节奏预算和数学验证数据，生成 [production-plan-v1.json](production-plan-v1.json)。28 镜旁白保留一般证明的所有环节；第 01 镜改成同一主图顺次对照，第 23 镜增加真实十六步操作解说，Wilson 的配音读作“威尔逊”。没有把充分性证明缩成总结或附录。

计划包含 136 个分阶段证明动作，以及 82 次沿真实边交换空格的移动。三轮换、共轭、双交换和一旧两新接口通过位置作用操作展示；字幕依赖实际词边界。非合法滑动的代数层有独立标记。有限数据核验只检查画面实例，任意尺寸的依据仍是正片中完整讲述的构造与归纳。

```powershell
video-maker/.venv/Scripts/python.exe series/math-education/inversion-count/episodes/02-rectangle-proof/authoring/compose_production.py
& 'series/math-education/inversion-count/episodes/02-rectangle-proof/authoring/produce.ps1' -PreviewOnly
& 'series/math-education/inversion-count/episodes/02-rectangle-proof/authoring/produce.ps1'
```

先由通用 `video-maker` 实现并验证 `proof` 后端，再运行本期制作入口。入口先生成实际计划、验证数据与结构，并核对最终计划及外部人物素材的双项语义审核绑定，再正式联网配音、渲染。缺少匹配审核会在配音前停止；技术预览不代表审核通过。完整人格与逐镜依据仅保存在独立私有角色库。

默认 1920×1080、30fps，Edge TTS 晓晓 `zh-CN-XiaoxiaoNeural`、语速 `+8%`，人物图片使用用户给定 JPEG 占位。`-Voice`、`-Rate`、`-Presenter`、`-VideoCodec` 与 `-OutputDirectory` 均可替换，计划和素材变化须复审。后续可将人物换成预渲染的 Live2D/其他视频形象；本期不声称已实现 Live2D 模型驱动或口型。

默认大型产物在仓库外 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/02-rectangle-proof/production-v1/`。每次运行按 SHA-256 冻结 JAR 与配音 worker，独立保存本期 TTS、分段缓存和运行记录，不和其他期并发写同一个缓存。保留失败材料后可按完全匹配的输入重试。三期争用资源时，第一期优先。
