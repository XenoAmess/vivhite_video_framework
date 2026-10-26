# 第三期：从头证明 Wilson 图上滑块定理

本期独立完成有限简单 2 连通图的可达性分类，包含环、七顶点 `θ₀`、交错群生成引理、theta 起点、任意耳扩张和分量计数。第二期的矩形结论保持单独成片，第一期不追加内容。

- [完整导演稿](director.md)：38 场，逐场完整旁白、连续对象、操作、公式、留白任务与预算。49 分 30 秒是未配音的制作预算，实际时长需由公式读法与动作排练重排。
- [逐式证明](proof.md)：全部关键引理和边界；补齐 `θ₀` 加任意耳的八类端点参数表。
- [校验程序](verify_proof.py) 与 [有限证书](verification.json)：只需 Python 标准库。有限计算不冒充无限图族证明。
- [期配置](episode.json)：角色 ID `vivhite`，完整人格在项目规约指定的私有角色库读取。

制作状态是导演稿，未配音、未渲染。现有制作器的有限棋盘视图不足以直接渲染本期，后续需要图路径、合法滑动队列、三轮换支点、耳增生、模 5 分式变换等画面组件；不能把 Markdown 当成已经能直接 `produce` 的计划。

本期公式统一按**动作队列的执行顺序**从左到右写。第二期常规函数复合的右到左写法不直接沿用；导演稿第 3 场用一个三位置例子明确切换。图上实际滑动及程序的循环方向与本期约定一致。

```powershell
py -3.12 series/math-education/inversion-count/episodes/03-wilson-theorem/verify_proof.py `
  --output series/math-education/inversion-count/episodes/03-wilson-theorem/verification.json
```

角色完整稿源引用和双项审核按项目 [角色创作与审核规约](../../../../../docs/character-workflow.md) 执行。公开文件只保存版本绑定和结果；审核结论不代表数学动画或最终成片已经验收。
