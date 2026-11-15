# 第一期：秋日旅程

- [导演案 v2](director.md)：无对白的多地点自由旅行蒙太奇；48 个连续镜头，每镜 2–10 秒，排练总长 3 分 22 秒。
- [周边图像生成说明 v2](image-briefs.md)：角色原图绑定、贴纸／玩偶／周边／意象设计，以及真实感人物不露脸的场景任务卡。
- [素材清单](reference-assets.json)：用户 ZIP 中 11 张图的指纹与使用范围。
- [期清单](episode.json)：稳定 ID、角色与导演稿入口。

本期要求：白绮全程不说话，不设旁白、内心独白或对白字幕；用音乐与环境声连接世界各处的旅行片段。每个连续镜头均为 2–10 秒，真实感人物只拍不露脸的局部，反射和背景也不能带出真人面孔。周边印刷角色图与二维贴纸可以显示白绮的绘制面孔。

所有出场人物为女性，真人局部的女性化服装贴近白绮设定图；已生成的普通旅行衣着版本保留归档，但不作为制作输入。

本次为前期文字交付，时码尚未按配乐锁定，调整仍须满足单镜 2–10 秒。角色 ZIP 已查看，尚未生成周边图片、人物动作、配乐或视频。原图解压副本留在仓库外，公开工程不保存原 ZIP 或原图。

导演案与图像说明是两个独立审核对象，`reviews/` 保存脚本导出的绑定收据，详细依据只在私有角色库维护。当前版本以这两个文件的实际 SHA-256 选取收据；历史 v1 收据只属于旧稿，不能覆盖 v2。审核方式为 `assistant-semantic-review`，不代表人工看过影片或最终美术验收。

本地保留原压缩包和私有角色库时，可以复查当前文字版本：

```powershell
$episode = 'series/vivhite/autumn-journey/episodes/01-autumn-journey/episode.json'
$referenceZip = '<本地 character.zip 路径>'
video-maker/.venv/Scripts/python.exe scripts/character_review.py check --episode $episode --asset $referenceZip
video-maker/.venv/Scripts/python.exe scripts/character_review.py check --episode $episode --document series/vivhite/autumn-journey/episodes/01-autumn-journey/image-briefs.md --asset $referenceZip
```

此处 `--asset` 绑定的是已查看的参考压缩包，不能用于放行正式渲染。后续实际母版、场景、人物、音频及最终制作计划须重新审阅，并传入本次正式制作采用的全部实际外部素材。
