# S01左手反手拉窗帘返工 v10

用户拒收第一幕左臂上的手部朝向。本轮仅重做S01，保持00:00–00:04，原生源片仍为5秒／120帧／24fps、1344×768；其余47镜源片与全部48镜时长、起点、音乐、标题和原生14秒片尾均沿用v9。全片固定205秒／6150帧／30fps。v9及所有旧Release、首帧候选和视频中间产物保留，不提交2K／4K任务。

## 先前错误与首帧修订

此前源片复核说明只称手部动作自然，没有具体核对左臂与手掌左右侧的对应关系，漏掉了用户指出的问题。不能以旧的采用记录覆盖用户拒收，更不能用“只有一只手”证明它接对了。正式拒收记录见[原S01](rejected-v9-S01.json)。

本轮最初又把反手动作改成了掌心朝镜头的抓握，偏离用户要的左手反手拉帘；用户明确拒绝，这两版不采用。第三版恢复手背朝镜头，但拇指接触被布遮得太多，也没有送视频。第四版保留手背与指关节朝镜头、掌心朝窗帘与玻璃，拇指在下侧与弯曲食指相对，捏住同一小片布，腕部连续连接左前臂。四张图全部保留：[v1](../assets/generated/production-v10-firstframes-001/scenes/S01-left-hand-v1.png)、[v2](../assets/generated/production-v10-firstframes-001/scenes/S01-left-hand-v2.png)、[v3](../assets/generated/production-v10-firstframes-001/scenes/S01-left-hand-v3.png)、[实际输入v4](../assets/generated/production-v10-firstframes-001/scenes/S01-left-hand-v4.png)。

图片均由内置imagegen编辑并复制入项目，未用CLI替代。每次的完整实际提示词、编辑目标、指纹及采用状态见[图像记录](image-edits-v10.json)。第三、四版额外参考[britt gaiser的真实拉帘手势照片](https://unsplash.com/photos/person-holding-window-curtain-during-daytime-92ZQFrntgwA)，仅作为手部姿势参考，不把该照片的布帘、首饰、链条、场景或身份带入本片；本地原输入及指纹在图像记录中保留。首帧被选作输入不等于生成视频已通过。

## 生成与检查

实际请求见[S01单镜计划](../production-plan-v10-S01-image-only-r1.json)，完整目标见[v10制作计划](../production-plan-v10-bf16-768p.json)和[48镜导演稿](../director-v10.md)。只上传第四版新首帧图，不上传旧缺陷视频。8001实读健康、模型列表确认BF16 FastH3 Omni、36层解码器、8步、1344×768；单窗口正常排队。

原上传、请求、任务响应、含音轨原始输出、规范化无声源片与检查记录保存在仓库同级 `vivhite-analysis-output/vivhite/autumn-journey/production-v10-motion-768p-001/`。具体进度见[快照](run-progress-v10-768p.json)，区分生成、源片采用、成片解码、编码后审阅和发布；提示词中的LEFT或图像文件名不是验收依据。

必须实际检查120个完整源帧，以及[原生局部检查工具](inspect-motion-details-v10.py)导出的全部手／腕局部与原生完整检查点：从左肘、左前臂跟到手腕和手背，再核对拇指侧与食指捏布接触，确认轻拉期间不翻掌、不换左右手、不扭腕、断腕或穿布。另核对无真人脸、下巴、人物倒影和新增人员；原女性化衣装、挂件睁眼轮廓、虹膜、细金圆镜和脸部比例须稳定。实际采用记录另存，检查图全部留项目入Git。

装配用[导入器](materialize-sources-v10.py)锁定全部48镜时长／起点及其余47镜完整指令和源片来源；[回归检查](../../../../../../video-maker/tools/tests/test_v10_locked_timing.py)拒绝任一镜头的时长、起点、源时长或非S01指令变化，也拒绝标题修改。动作错误须重生成，不能以人体遮罩、贴片或换帧冒充修正。相同205秒纯程序器乐及ASS沿用旧版，新的最终输入与真实影片分别进行人格／披露审核及全量编码检查。助手帧图审阅与人工连续观看、听音、用户审美验收分别记录。
