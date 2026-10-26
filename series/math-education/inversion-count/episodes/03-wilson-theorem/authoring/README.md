# 第三期可执行稿源

`compose_production.py` 将完整导演稿编为 `vivhite-production-1`，消费 Java 制作器的通用 `proof` 后端。43 个制作段覆盖原来的全部 38 场；开场三种图分别匹配自己的牌数，三次特殊耳改路分别从独立原图开始，四二二的完整共轭单独测时。49:30 仅是最初的排练预算，不作为每场最短时长；实际按完整配音、真实路径操作所需时间和短观察段排程。不会删证明、强行加速或留下几十秒没有事件的静帧来凑片长。

默认使用 Edge TTS 晓晓 `zh-CN-XiaoxiaoNeural`、`+8%`，1920×1080、30fps。音色和语速是参数，可替换人物图片为事先渲染的形象视频。口播把希腊字母转为可读的“派、柔、陶”，画面仍保留数学记号；字幕来自实际单词时间，不使用预估语速切字幕。

```powershell
& series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/produce.ps1
video-maker/.venv/Scripts/python.exe series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/compose_production.py
video-maker/.venv/Scripts/python.exe series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/verify_production.py
java -jar video-maker/target/video-maker-0.1.0-SNAPSHOT.jar validate-production series/math-education/inversion-count/episodes/03-wilson-theorem/authoring/production-plan-v1.json
```

`produce.ps1` 支持 `-Voice`、`-Rate`（含负语速）、`-VideoCodec`、`-Presenter`、`-OutputDirectory` 和 `-PreviewOnly`。先用 Maven Wrapper 构建制作器；入口会验证全部数学动作，按内容哈希冻结 JAR 和 worker，设置本期独立 TTS 缓存，并在正式配音前执行 `character_review.py check`。修改音色、计划或素材后，需要审核对应实际版本。已有影片的输出目录拒绝换用不同计划或素材，应另设版本目录。

如需复用已交付的运行环境，传 `-MakerJar '<原输出>/engine.jar' -WorkerPath '<原输出>/production_worker.py'`，保留原始冻结快照；新运行快照放在 `runtime/` 下。技术预览不会自动生成语义审核结论。

制作前完整读取角色人格，对实际计划和外部人物素材做两项语义审核，并执行 [审核检查](../../../../../../docs/character-workflow.md)。不能把本适配器的数学自检当作人格审核，也不能把技术预览当成已完整观看成片。

正式输出放仓库外 `D:/workspace/vivhite-analysis-output/math-education/inversion-count/03-wilson-theorem/production-v1/`。每期独立缓存配音、片段和时间轴；`engine.jar`、`production_worker.py` 与 `production-plan.json` 保存运行快照，避免并发修改构建产物影响已有生产。既有片段按内容哈希复用，失败后修复实际问题再续跑，不删除原始结果。

`verify_production.py` 独立模拟全部图上边交换和代数卡，检查特殊 theta 种子卡、完整共轭及七点图基本卡的精确位置映射。它覆盖这份制作计划的全部动作，任意大小图的证明仍由 [数学底稿](../proof.md) 的符号恒等式、三角接力与耳扩张承担。
